"""Physical current-candidate capacity, without changing the 256MiB budget."""
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest

from document_helpers import observe
from smm_local.archive_protocol import atomic_json
from document_formats_staging_observer import observe_capacity_writes
from test_document_formats_staging import test_before_accept_write_observer_has_real_positive_and_negative_controls as check_write_observer_controls
from test_document_formats_installed_minimum import assert_complete_source_text, test_complete_text_oracle_accepts_layouts_and_rejects_wrong_content as check_complete_text_controls
from document_formats_gc_fixture import image_with_unreferenced_stream, partial_without_ocr
from test_document_formats_management import Creator
from test_document_formats_retry import keep
from test_hub_documents_contracts import w

MIB = 1024 * 1024
LIMIT = 256 * MIB


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def input_bytes(label, raw):
    compressed = gzip.compress(raw, mtime=0)
    assert gzip.decompress(compressed) == raw
    keep('gc-inputs/' + sha(raw) + '.pdf.gz', compressed)
    observe('gc-input', {'label': label, 'bytes': len(raw), 'sha256': sha(raw),
                         'gzip_sha256': sha(compressed)})


def body_write_events(events, root):
    """Allow bounded transfer-state JSON, never body writes or worker launches."""
    root = Path(root).resolve()
    body = []
    for event in events:
        if event['kind'] == 'worker-launch':
            body.append(event)
            continue
        path = Path(event['path']).resolve()
        relative = path.relative_to(root)
        metadata = (len(relative.parts) == 3 and relative.parts[0] == 'transfers'
            and (relative.name == 'state.json' or relative.name.startswith('state.json.'))
            and event['bytes'] <= 128 * 1024)
        if not metadata:
            body.append(event)
    return body


def check_body_event_filter(root, monkeypatch):
    folder = root / 'transfers' / ('a' * 32)
    folder.mkdir(parents=True)
    raw = root / 'raw'
    raw.mkdir()
    with monkeypatch.context() as patch:
        events = observe_capacity_writes(patch, root)
        atomic_json(folder / 'state.json', {'binding': 'metadata-control', 'blobs': {}})
        assert len(events) == 2 and body_write_events(events, root) == []
        (raw / sha(b'body-control')).write_bytes(b'body-control')
        assert len(body_write_events(events, root)) == 1
        (folder / 'unknown-body.part').write_bytes(b'unexpected-body')
        assert len(body_write_events(events, root)) == 2
        size = len(events)
        assert json.loads((folder / 'state.json').read_text())['binding'] == 'metadata-control'
        assert len(events) == size
    observe('gc-body-event-filter-controls', {'events': events,
        'metadata_atomically_written_then_allowed': True, 'raw_and_unknown_transfer_body_detected': True,
        'reads_produce_no_write_events': True})



class GCClient(Creator):
    def __init__(self, world, owner):
        self.begins = {}
        super().__init__(world, owner)

    def request(self, method, path, body=None, **kwargs):
        response = super().request(method, path, body=body, **kwargs)
        if method == 'POST' and path == '/documents/uploads' and not kwargs.get('reject'):
            self.begins[response.json()['upload_id']] = deepcopy(body)
        return response

    def push(self, item, raw, *, update=False):
        input_bytes(item['name'], raw)
        comparison = self.comparison(self.entries()[item['id']]) if update else None
        uid, receipt, entry = self.upload(item, raw, comparison)
        item['id'] = entry['id']
        record = {'uid': uid, 'body': self.begins[uid], 'first': raw[:MIB],
                  'target': deepcopy(entry['retry_target']), 'entry': deepcopy(entry)}
        assert receipt['capture_id'] == entry['latest_attempt']['capture_id']
        assert receipt['attempt_id'] == entry['latest_attempt']['attempt_id']
        return record

    def failed(self, item, raw, *, update=False):
        record = self.push(item, raw, update=update)
        entry = record['entry']
        assert entry['latest_attempt']['status'] == 'failed'
        error = entry['latest_attempt']['error']
        assert isinstance(error, str) and 'ocr' in error.lower(), error
        assert not any(word in error for word in ('256MiB', '300秒', 'RSS', 'PermissionError'))
        target = entry['retry_target']
        assert target and target['sha256'] == sha(raw)
        assert target['capture_id'] == entry['latest_attempt']['capture_id']
        assert target['expected_attempt_id'] == entry['latest_attempt']['attempt_id']
        assert (entry['version'], entry['processing_version']) == ((0, 0) if item['before'] == 'none' else (1, 1))
        assert (entry['published_snapshot'] is None) == (item['before'] == 'none')
        item['current_raw'] = raw
        item['current'] = record
        return record

    def remove_item(self, item):
        entry = self.entries()[item['id']]
        self.request('DELETE', '/documents/library/' + item['id'],
                     {**self.project(item['project']), **self.comparison(entry)})
        assert item['id'] not in self.entries()

    def frozen(self):
        business = super().frozen()
        root = self.db.db_path.resolve().parent / '.document-snapshots'
        snapshot = {}
        for path in sorted(root.rglob('*')):
            if path.is_file() and not path.name.endswith('.lock'):
                raw = path.read_bytes()
                snapshot[path.relative_to(root).as_posix()] = {'bytes': len(raw), 'sha256': sha(raw)}
        return business, snapshot

    def reject_old(self, item, record):
        requests = [
            ('POST', '/documents/uploads', {'body': record['body']}),
            ('PUT', '/documents/uploads/' + record['uid'] + '/parts/0',
             {'raw': record['first'], 'headers': {'X-Chunk-SHA256': sha(record['first'])}}),
            ('POST', '/documents/uploads/' + record['uid'] + '/commit', {'body': self.context}),
        ]
        for method, path, arguments in requests:
            before = self.frozen()
            self.request(method, path, reject=True, **arguments)
            assert self.frozen() == before
            observe('gc-stale-request-unchanged', {'method': method, 'path': path,
                'document_id': item['id'], 'snapshot_and_transfer_bytes_unchanged': True})
        before = self.frozen()
        self.retry_removed(item, record['target'])
        assert self.frozen() == before
        observe('gc-stale-refused', {'document_id': item['id'], 'upload_id': record['uid'],
                                    'capture_id': record['target']['capture_id'],
                                    'all_business_and_snapshot_state_unchanged': True})


def storage(client, published):
    root = client.db.db_path.resolve().parent / '.document-snapshots'
    result = {}
    for kind in ('raw', 'results'):
        folder = root / kind
        for path in sorted(folder.iterdir()) if folder.exists() else []:
            raw = path.read_bytes()
            assert path.is_file() and not path.is_symlink() and sha(raw) == path.name
            if (kind, path.name) not in published:
                result[kind + '/' + path.name] = {'bytes': len(raw), 'sha256': sha(raw)}
    # This case finishes every real transfer; no pending reservations may hide.
    for path in (root / 'transfers').glob('*/state.json'):
        state = json.loads(path.read_text())
        assert state.get('committed') or (root / 'expired-transfers' / path.parent.name).exists()
    return result


def assert_storage(client, published, candidates, expected_total):
    expected = {'raw/' + sha(item['current_raw']): {'bytes': len(item['current_raw']),
                 'sha256': sha(item['current_raw'])} for item in candidates}
    actual = storage(client, published)
    assert actual == expected
    assert sum(row['bytes'] for row in actual.values()) == expected_total
    observe('gc-physical-capacity', {'bytes': expected_total, 'blobs': actual,
                                    'document_ids': sorted(item['id'] for item in candidates)})


def assert_protected(client, targets, text_controls, unrelated):
    entries = client.entries()
    for item in targets:
        current = entries[item['id']]
        previous = item['current']['entry']
        for field in ('latest_attempt', 'retry_target', 'published_snapshot', 'version', 'processing_version'):
            assert current[field] == previous[field]
        assert client.db.db_path.parent.joinpath('.document-snapshots', 'raw', sha(item['current_raw'])).read_bytes() == item['current_raw']
        if item['before'] != 'none':
            before = item['published']
            assert current['published_snapshot'] == before['entry']['published_snapshot']
            fresh = client.read(item)
            assert_complete_source_text(fresh['read']['text'],
                {**item['truth'], 'ordered_groups': [item['truth']['words']]})
            for field in ('read', 'tables', 'info', 'raw_sha256'):
                assert fresh[field] == before[field]
            reference = before['entry']['original_reference']
            result = client.request('POST', '/documents/read',
                {**client.context, 'reference': reference, 'start': 0,
                 'end': before['entry']['text_length']}).json()
            assert result == before['read']
            for table in before['tables']:
                view = client.request('POST', '/documents/read',
                    {**client.context, 'reference': reference, 'view': 'table', 'table_id': table['table_id'],
                     'row_start': 1, 'row_end': table['rows'] + 1,
                     'column_start': 1, 'column_end': table['columns'] + 1}).json()
                assert view == table
            response = client.request('POST', '/documents/original', {**client.context, 'reference': reference})
            assert response.content == item['raw']
            other = client.request('POST', '/documents/search', {**client.context,
                'query': item['truth']['words'][0], 'scope': 'project', 'project_id': unrelated['id'],
                'limit': 50, **({'local': True} if client.owner == 'local' else {})}).json()
            assert other['results'] == []
    for item in text_controls:
        client.assert_text(item)


@pytest.mark.parametrize('owner', ['local', 'hub'])
def test_replaced_and_removed_candidates_release_physical_capacity(w, tmp_path, owner, monkeypatch):
    # TC-008-canonical-candidate-capacity: first focused GC subcase, not whole GC.
    # Known real writes/no-writes and wrong complete-text inputs self-check the probes.
    check_write_observer_controls(tmp_path / 'write-control', monkeypatch)
    check_complete_text_controls()
    check_body_event_filter(tmp_path / 'body-filter-control', monkeypatch)
    client = GCClient(w, owner)
    unrelated = (w.local.request('POST', '/api/projects', {'name': 'GC unrelated'}) if owner == 'local'
                 else w.hub_project('GC unrelated'))
    text_controls = client.text_controls()
    sentinel = tmp_path / 'unrelated-control.bin'
    sentinel.write_bytes(b'never remove unrelated bytes')
    sentinel_stamp = sentinel.stat().st_mtime_ns
    targets = []
    published = set()
    for group, project in enumerate(client.projects):
        for before in ('none', 'ready', 'partial'):
            for index in range(2):
                key = owner + 'gc' + str(group) + before + str(index)
                if before == 'ready':
                    item = client.add('pdf', key, project)
                elif before == 'partial':
                    raw, truth = partial_without_ocr(key)
                    item = {'name': key + '.pdf', 'format': 'pdf', 'project': project,
                            'raw': raw, 'truth': truth, 'status': 'partial'}
                    result = client.push(item, raw)
                    assert result['entry']['latest_attempt']['status'] == 'partial'
                    client.items.append(item)
                else:
                    item = {'name': key + '.pdf', 'format': 'pdf', 'project': project,
                            'status': 'failed'}
                item.update(before=before, key=key)
                if before != 'none':
                    old = client.read(item)
                    assert_complete_source_text(old['read']['text'],
                        {**item['truth'], 'ordered_groups': [item['truth']['words']]})
                    item['published'] = old
                    if before == 'partial':
                        errors = old['read']['coverage']['errors']
                        assert any(e['page'] == 2 and e['method'] == 'ocr'
                            and any(word in e['reason'] for word in ('配置', '引擎', '组件')) for e in errors)
                    snapshot = old['entry']['published_snapshot']
                    published.update({('raw', snapshot['sha256']), ('results', snapshot['result_sha256'])})
                raw = image_with_unreferenced_stream(key + 'first', 18 * MIB)
                client.failed(item, raw, update=before != 'none')
                if before != 'none':
                    assert item['current']['target']['capture_id'] != item['published']['entry']['published_snapshot']['capture_id']
                    assert item['current']['target']['expected_attempt_id'] != item['published']['entry']['latest_attempt']['attempt_id']
                targets.append(item)
    assert len(targets) == len({item['id'] for item in targets}) == 12
    assert len({sha(item['current_raw']) for item in targets}) == 12
    assert len({item['current']['target']['capture_id'] for item in targets}) == 12
    assert len({item['current']['target']['expected_attempt_id'] for item in targets}) == 12
    filler = {'name': owner + 'filler.pdf', 'format': 'pdf', 'project': client.projects[0],
              'before': 'none', 'status': 'failed'}
    client.failed(filler, image_with_unreferenced_stream(owner + 'filler', 20 * MIB))
    assert_storage(client, published, [*targets, filler], 236 * MIB)
    assert_protected(client, targets, text_controls, unrelated)

    for index, item in enumerate(targets):
        old = item['current']
        raw = image_with_unreferenced_stream(item['key'] + 'replacement', 18 * MIB)
        client.failed(item, raw, update=True)  # 236 + 18 = 254MiB before obsolete GC.
        assert item['current']['target']['capture_id'] != old['target']['capture_id']
        assert item['current']['target']['expected_attempt_id'] != old['target']['expected_attempt_id']
        probe = {'name': owner + 'probe' + str(index) + '.pdf', 'format': 'pdf',
                 'project': item['project'], 'before': 'none', 'status': 'failed'}
        probe_raw = image_with_unreferenced_stream(owner + 'probe' + str(index), 20 * MIB)
        client.failed(probe, probe_raw)  # Requires reclaiming the obsolete18MiB.
        assert_storage(client, published, [*targets, filler, probe], LIMIT)
        assert_protected(client, targets, text_controls, unrelated)
        client.reject_old(item, old)
        before = client.frozen()
        small = image_with_unreferenced_stream(owner + 'over' + str(index), 2048)
        input_bytes('over-limit', small)
        with monkeypatch.context() as patch:
            events = observe_capacity_writes(patch, client.db.db_path.parent / '.document-snapshots')
            client.request('POST', '/documents/uploads', {**client.project(item['project']),
                'name': owner + 'over.pdf', 'submission_id': uuid4().hex,
                'sha256': sha(small), 'bytes': len(small)}, reject=True)
        body_events = body_write_events(events, client.db.db_path.parent / '.document-snapshots')
        observe('gc-full-admission-write-events', {'all_events': events, 'body_events': body_events, 'limit': LIMIT})
        assert body_events == [], body_events
        assert client.frozen() == before
        assert_storage(client, published, [*targets, filler, probe], LIMIT)
        client.remove_item(probe)
        client.reject_old(probe, probe['current'])
        # Admission in the next iteration must reclaim this removed probe too.
        assert sentinel.read_bytes() == b'never remove unrelated bytes'
        assert sentinel.stat().st_mtime_ns == sentinel_stamp
        observe('gc-target-complete', {'owner': owner, 'index': index, 'document_id': item['id'],
                                      'before': item['before'], 'probe_removed': probe['id']})
    # Trigger one final ordinary admission to collect the last removed probe.
    final = {'name': owner + 'final.pdf', 'format': 'pdf', 'project': client.projects[0],
             'before': 'none', 'status': 'failed'}
    client.failed(final, image_with_unreferenced_stream(owner + 'final', 20 * MIB))
    assert_storage(client, published, [*targets, filler, final], LIMIT)
    assert_protected(client, targets, text_controls, unrelated)
    assert sentinel.read_bytes() == b'never remove unrelated bytes'
    assert sentinel.stat().st_mtime_ns == sentinel_stamp
