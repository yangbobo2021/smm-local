"""Two cold creator bundles and a retained non-target for processed transport."""
from io import BytesIO
from copy import deepcopy
from datetime import datetime
import io
import json
import os
from pathlib import Path
import sqlite3
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_STORED

from document_formats_fixtures import W
from document_helpers import observe, deny_source_reads
from document_formats_sync_observer import install
from test_document_formats_received_validation import Receiver, sha
from test_document_formats_update_replay import material
from test_document_formats_retry import keep
from smm_local.document_formats.word import parse
from smm_local.document_results import encode
from smm_local.archive_protocol import digest, sign
from scripts.acceptance.document_formats_installed_lifecycle import unchanged_publication


def large_material(label, version):
    raw, truth = material('large', label, version)
    long_text = (label.upper() + ' transport block ') * 60000
    with ZipFile(BytesIO(raw)) as source:
        files = {n: source.read(n) for n in source.namelist()}
    tree = ET.fromstring(files['word/document.xml'])
    paragraph = ET.SubElement(tree.find('{' + W + '}body'), '{' + W + '}p')
    ET.SubElement(ET.SubElement(paragraph, '{' + W + '}r'), '{' + W + '}t').text = long_text
    files['word/document.xml'] = ET.tostring(tree, encoding='utf-8')
    output = BytesIO()
    with ZipFile(output, 'w', compression=ZIP_STORED) as target:
        for name, body in files.items(): target.writestr(name, body)
    raw = output.getvalue()
    with ZipFile(BytesIO(raw)) as source:
        tree = ET.fromstring(source.read('word/document.xml'))
        independent = '\n'.join(node.text or '' for node in tree.iter('{' + W + '}t'))
    assert independent == truth['text'] + '\n' + long_text
    result = parse(raw, sha(raw), {'fixture': 'native-word-v1'})
    assert result['text'] == independent
    assert [c['text'] for c in result['tables'][0]['cells']] == truth['cells']
    table, = result['tables']
    assert (table['rows'], table['columns']) == (1, 2)
    assert table['location'] == {'part': 'word/document.xml', 'path': 'body/table[1]'}
    for column, cell in enumerate(table['cells'], 1):
        assert (cell['row'], cell['column'], cell['row_span'], cell['column_span']) == (1, column, 1, 1)
        assert cell['location']['part'] == 'word/document.xml'
        assert cell['location']['path'] == 'body/table[1]/row[1]/cell[' + str(column) + ']'
    assert 1024**2 < len(raw) < 20 * 1024**2
    assert 1024**2 < len(encode(result)) < 16 * 1024**2
    return raw, result


class TransportReceiver(Receiver):
    def files_without_expected_extras(self):
        rows = self.w.remote('GET', '/documents/files')
        assert len(rows) == len({row['id'] for row in rows})
        expected = getattr(self, 'expected_extra_files', {})
        actual = {row['id']: row for row in rows if row['id'] in expected}
        assert actual == expected
        return [row for row in rows if row['id'] not in expected]

    def read(self, item, *, reference=None):
        value = super().read(item, reference=reference)
        response = self.w.hub.post('/v1/documents/original',
            json={**self.w.context(), 'reference': value['reference']})
        assert response.status_code == 200 and response.content == item['raw']
        keep('processed-transport/downloads/' + sha(response.content) + '.bin', response.content)
        return value

    def __init__(self, world, tmp_path, mode):
        self.w = world;self.binding = world.protocol();world.control(self.binding)
        self.mode = mode;self.items = [];self.paths = []
        directory = tmp_path / 'synthetic-sender';directory.mkdir()
        previous = {}
        for label in (['alpha', 'beta', 'gamma'] if mode == 'replacement' else ['gamma']):
            raw, truth = material('receive', label, 1)
            result = parse(raw, sha(raw), {'fixture': 'native-word-v1'})
            assert result['text'] == truth['text']
            item = self.packet(raw, result, label)
            path = directory / (label + '.docx');path.write_bytes(raw)
            self.paths.append(path);item['meta']['path'] = str(path)
            self.items.append(item);previous[label] = item
        for item in self.items: self.stage(item)
        self.w.publish(self.manifest(self.items))
        self.saved = [self.read(item) for item in self.items]
        self.baseline_library = self.w.remote('GET', '/documents/library')
        self.next = []
        for label in ('alpha', 'beta'):
            raw, result = large_material(label, 2 if mode == 'replacement' else 1)
            item = self.packet(raw, result, label, previous=previous.get(label))
            path = directory / (label + '.docx');path.write_bytes(raw)
            if path not in self.paths: self.paths.append(path)
            item['meta']['path'] = str(path);self.next.append(item)
        self.gamma = previous['gamma']
        self.final_items = [*self.next, self.gamma]
        for item in [*self.items, *self.next]:
            keep('processed-transport/inputs/' + sha(item['raw']) + '.docx', item['raw'])
            keep('processed-transport/results/' + sha(item['results']) + '.json', item['results'])
        self.future = self.future_references()

    def guard(self, monkeypatch):
        self.processing = install(monkeypatch)
        self.source_reads = deny_source_reads(monkeypatch, *self.paths)
        for path in self.paths:
            for opening in (path.read_bytes, lambda: io.open(path, 'rb'), lambda: os.open(path, os.O_RDONLY)):
                try: opening()
                except AssertionError as error:
                    assert 'source body unexpectedly opened' in str(error)
                else: raise AssertionError('source guard did not reject its actual source path')
        self.known_source_controls = len(self.source_reads)
        assert self.known_source_controls == 3 * len(self.paths)
        observe('processed-source-open-negative-controls', {'paths': self.source_reads[:],
            'business_window_starts_after': self.known_source_controls})

    def future_references(self):
        # Only this synthetic archive's existing signing material, read-only.
        with sqlite3.connect(self.w.pair.remote.db_path.as_uri() + '?mode=ro', uri=True) as c:
            archive = json.loads(c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
            key = c.execute('SELECT signing_key FROM archive_reference_material WHERE singleton=1').fetchone()[0]
        source = digest([self.w.device, self.w.archive, self.binding['project_key'], 'b' * 32])[:32]
        result = {}
        for item in self.next:
            m = item['meta'];ident = digest([self.w.device, self.w.archive, m['document_id']])[:32]
            inner = sign({'format': 1, 'kind': 'document', 'archive_id': archive,
                'document_id': ident, 'version': m['version'],
                'sources': [{'id': source, 'revision': 1, 'qualification': 1}],
                'start': 0, 'end': 2000, 'processing_version': m['processing_version'],
                'result_sha256': m['result_sha256'], 'raw_sha256': m['sha256']}, key)
            result[item['label']] = sign({'format': 1, 'kind': 'hub_document', 'archive_id': archive,
                **self.w.context(), 'origin': {'device_id': self.w.device, 'archive_id': self.w.archive,
                'document_id': m['document_id']}, 'reference': inner,
                **{k: m[k] for k in ('version', 'sha256', 'text_sha256', 'processing_version', 'result_sha256')},
                'text_length': item['result']['text_length']}, key)
        return result

    def old_bundles(self):
        for item, saved in zip(self.items, self.saved):
            unchanged_publication(self.read(item, reference=saved['reference']), saved)

    def unpublished(self, phase):
        expected = {item['meta']['document_id']: item['meta'] for item in self.items}
        rows = self.files_without_expected_extras()
        assert len(rows) == len(expected)
        for row in rows:
            origin = row['origin'];m = expected[origin['document_id']]
            assert origin == {'device_id': self.w.device, 'archive_id': self.w.archive, 'document_id': m['document_id']}
            for key in ('version', 'sha256', 'processing_version'): assert row[key] == m[key]
            assert row['published_snapshot']['result_sha256'] == m['result_sha256']
        assert self.w.remote('GET', '/documents/library') == self.baseline_library
        for item in self.next:
            assert self.w.search_hub(item['result']['text'].split()[0], limit=50)['results'] == []
            body = {**self.w.context(), 'reference': self.future[item['label']]}
            for fields in ({'view': 'text'}, {'view': 'original-info'},
                           {'view': 'table', 'table_id': item['result']['tables'][0]['table_id']}):
                self.w.reject_remote('POST', '/documents/read', {**body, **fields})
            self.w.reject_remote('POST', '/documents/original', body)
        self.old_bundles()
        observe('processed-future-unpublished-' + phase, {'mode': self.mode,
            'future_references': self.future, 'baseline_document_ids': sorted(expected),
            'future_queries_and_all_read_views_rejected': True})

    def finish(self, *, publish=True):
        if publish: self.w.publish(self.manifest(self.final_items, sequence=2))
        for item in self.next:
            m = item['meta'];expected = item['result'];reference = self.future[item['label']]
            hits = self.w.search_hub(expected['text'].split()[0], limit=50)['results']
            hit, = [h for h in hits if h['origin']['document_id'] == m['document_id']]
            assert all(hit[k] == m[k] for k in ('version', 'processing_version', 'sha256', 'result_sha256'))
            chunks = []
            for start in range(0, expected['text_length'], 16000):
                end = min(start + 16000, expected['text_length'])
                actual = self.w.read_hub({'reference': reference}, start=start, end=end)
                assert actual['text'] == expected['text'][start:end]
                for key in ('locations', 'coverage', 'profile'): assert actual[key] == expected[key]
                assert actual['tables'] == [{k: v for k, v in table.items() if k != 'cells'} for table in expected['tables']]
                assert actual['start'] == start and actual['end'] == end
                assert actual['start_line'] == 1 + expected['text'].count('\n', 0, start)
                assert actual['end_line'] == 1 + expected['text'].count('\n', 0, end - 1)
                chunks.append(actual['text'])
            assert ''.join(chunks) == expected['text']
            for table in expected['tables']:
                actual = self.w.read_hub({'reference': reference}, view='table', table_id=table['table_id'],
                    row_start=1, row_end=table['rows'] + 1, column_start=1, column_end=table['columns'] + 1)
                assert all(actual[k] == v for k, v in table.items())
            info = self.w.read_hub({'reference': reference}, view='original-info')
            assert info['available'] and info['bytes'] == len(item['raw']) and info['sha256'] == m['sha256']
            actual = self.w.hub.post('/v1/documents/original', json={**self.w.context(), 'reference': reference})
            assert actual.status_code == 200 and actual.content == item['raw']
            keep('processed-transport/downloads/' + sha(actual.content) + '.bin', actual.content)
        gamma_saved = self.saved[self.items.index(self.gamma)]
        gamma = self.read(self.gamma, reference=gamma_saved['reference'])
        normalized = deepcopy(gamma)
        pairs = [(normalized['hit'], gamma_saved['hit']), (normalized['text'], gamma_saved['text']),
                 *zip(normalized['tables'], gamma_saved['tables'])]
        timestamps = set()
        for actual, old in pairs:
            # The same-source complete manifest is a new receive event even
            # for an unchanged non-target (Hub publish updates received_at).
            # Content, origin, versions and the retained old reference remain
            # exact; only this explicitly validated observation time may move.
            stamp = datetime.fromisoformat(actual['received_at'])
            before = datetime.fromisoformat(old['received_at'])
            assert stamp.tzinfo is not None and before.tzinfo is not None and stamp >= before
            timestamps.add(actual['received_at']);actual['received_at'] = old['received_at']
        assert len(timestamps) == 1
        unchanged_publication(normalized, gamma_saved)
        observe('processed-retained-nontarget-receipt', {'before': gamma_saved, 'after': gamma,
            'scope': 'Same-source legal manifest changes only receive time and corpus BM25; old ref/content/table/raw/origin/V/P remain exact.'})
        if self.mode == 'replacement':
            for item, saved in zip(self.items, self.saved):
                if item is not self.gamma:
                    body = {**self.w.context(), 'reference': saved['reference']}
                    for fields in ({'view': 'text'}, {'view': 'original-info'},
                                   {'view': 'table', 'table_id': item['result']['tables'][0]['table_id']}):
                        self.w.reject_remote('POST', '/documents/read', {**body, **fields})
                    self.w.reject_remote('POST', '/documents/original', body)
        rows = self.files_without_expected_extras()
        actual_ids = [r['origin']['document_id'] for r in rows]
        assert len(actual_ids) == len(set(actual_ids)) == len(self.final_items)
        assert set(actual_ids) == {i['meta']['document_id'] for i in self.final_items}
        assert self.processing == [] and self.source_reads[self.known_source_controls:] == []
        observe('processed-complete-transport', {'mode': self.mode, 'document_ids': actual_ids,
            'same_future_refs_succeeded': self.future, 'source_reads': self.source_reads,
            'known_negative_source_controls': self.known_source_controls, 'processing_attempts': self.processing})
