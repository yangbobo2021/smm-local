"""Authenticated receive-only rejection must preserve the complete publication."""
from copy import deepcopy
import hashlib
import json
from uuid import uuid4

import pytest

from document_helpers import observe
from document_formats_sync_observer import install as receiver_observer
from test_hub_documents_contracts import w
from test_document_formats_update_replay import material
from smm_local.document_formats.word import parse
from smm_local.document_results import encode


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class Receiver:
    def __init__(self, world):
        self.w = world
        self.binding = world.protocol()
        world.control(self.binding)
        self.items = []
        for label in ('alpha', 'beta'):
            raw, truth = material('receive', label, 1)
            result = parse(raw, sha(raw), {'fixture': 'native-word-v1'})
            assert result['text'] == truth['text']
            assert [c['text'] for c in result['tables'][0]['cells']] == truth['cells']
            self.items.append(self.packet(raw, result, label))
        for item in self.items:
            self.stage(item)
        self.w.publish(self.manifest(self.items))
        self.saved = [self.read(item) for item in self.items]
        self.next = []
        for old in self.items:
            raw, truth = material('receive', old['label'], 2)
            result = parse(raw, sha(raw), {'fixture': 'native-word-v1'})
            assert result['text'] == truth['text']
            assert [c['text'] for c in result['tables'][0]['cells']] == truth['cells']
            self.next.append(self.packet(raw, result, old['label'], previous=old))

    def packet(self, raw, result, label, *, previous=None):
        payload = encode(result)
        metadata = {
            'document_id': previous['meta']['document_id'] if previous else uuid4().hex,
            'version': 2 if previous else 1, 'processing_version': 2 if previous else 1,
            'sha256': sha(raw), 'raw_bytes': len(raw), 'format': 'docx',
            'text_sha256': result['text_sha256'], 'result_sha256': sha(payload),
            'result_bytes': len(payload), 'profile_sha256': sha(encode(result['profile'])),
            'capture_id': uuid4().hex, 'schema': 'processed_documents_v1',
            'capture_sequence': 2 if previous else 1, 'captured_by_source_id': 'b' * 32,
            'path': '/synthetic-sender/' + label + '.docx', 'display_name': label + '.docx',
            'captured_at': '2026-11-28T00:00:00Z',
        }
        return {'meta': metadata, 'raw': raw, 'results': payload, 'result': result,
                'label': label, 'submission': uuid4().hex}

    def begin(self, item):
        body = {**self.binding, 'submission_id': item['submission'], 'document': item['meta']}
        return self.w.remote('POST', '/documents/processed/begin', body)

    def part(self, ident, kind, offset, raw, *, expected_sha=None, reject=False):
        path = '/v1/documents/processed/' + ident + '/' + kind + '/' + str(offset)
        response = self.w.hub.put(path, content=raw,
            headers={'X-Content-SHA256': expected_sha or sha(raw)})
        observe('received-part', {'path': path, 'bytes': len(raw), 'sha256': sha(raw),
                                 'status': response.status_code, 'response': response.json()})
        assert (400 <= response.status_code < 500) if reject else response.status_code == 200
        return response.json()

    def stage(self, item, *, reject=False, unexpected=None):
        started = self.begin(item)
        for kind in ('raw', 'results'):
            raw = item[kind]
            for start in range(0, len(raw), started['block_bytes']):
                self.part(started['transfer_id'], kind, start, raw[start:start + started['block_bytes']])
        request = {'transfer_id': started['transfer_id']}
        if reject:
            try:
                self.w.reject_remote('POST', '/documents/processed/commit', request)
            except Exception as error:
                if unexpected is None: raise
                import traceback
                detail={'type':type(error).__name__,'error':str(error),'traceback':traceback.format_exc()}
                unexpected.append(detail);observe('unexpected-receive-rejection',detail)
        else:
            assert self.w.remote('POST', '/documents/processed/commit', request)['staged'] is True
        return started

    def manifest(self, items, sequence=1):
        packet = self.w.manifest(self.binding, [item['meta'] for item in items], sequence=sequence)
        packet['files'] = [{**item['meta'], 'relative_path': item['meta']['display_name'],
                            'qualification': 1} for item in items]
        return packet

    def read(self, item, *, reference=None):
        result = item['result']; meta = item['meta']
        hits = self.w.search_hub(result['text'].split()[0], limit=50)['results']
        own = [h for h in hits if h['origin'] == {'device_id': self.w.device,
            'archive_id': self.w.archive, 'document_id': meta['document_id']}]
        assert len(own) == 1
        hit = own[0]; reference = reference or hit['reference']
        assert all(hit[key] == meta[key] for key in ('version', 'processing_version', 'sha256', 'result_sha256'))
        text = self.w.read_hub({'reference': reference}, start=0, end=len(result['text']))
        for key in ('text', 'locations', 'coverage', 'profile'):
            assert text[key] == result[key]
        assert text['tables'] == [{k: v for k, v in t.items() if k != 'cells'} for t in result['tables']]
        tables = []
        for expected in result['tables']:
            table = self.w.read_hub({'reference': reference}, view='table', table_id=expected['table_id'],
                row_start=1, row_end=expected['rows'] + 1, column_start=1, column_end=expected['columns'] + 1)
            assert all(table[k] == v for k, v in expected.items())
            tables.append(table)
        original = self.w.hub.post('/v1/documents/original',
            json={**self.w.context(), 'reference': reference})
        assert original.status_code == 200 and original.content == item['raw']
        return {'reference': reference, 'hit': hit, 'text': text, 'tables': tables,
                'raw_sha256': sha(original.content), 'raw_bytes': len(original.content)}

    def unchanged(self, before):
        assert self.w.snapshot() == before
        for item, saved in zip(self.items, self.saved):
            assert self.read(item, reference=saved['reference']) == saved


def malformed(value, variant):
    """Keep canonical encoding and matching transport SHA for structural faults."""
    table = value['tables'][0]
    if variant == 'schema': value['schema'] = 'processed_documents_future'
    elif variant == 'location-range': value['locations'][0]['end'] = value['text_length'] + 1
    elif variant == 'location-type': value['locations'][0] = []
    elif variant == 'location-bbox': value['locations'][0]['bbox'] = [0, 0, 2, 1]
    elif variant == 'missing-table-location': del table['location']
    elif variant == 'missing-table-cells': del table['cells']
    elif variant == 'table-cells-type': table['cells'] = None
    elif variant == 'cell-type': table['cells'][0] = None
    elif variant == 'missing-cell-location': del table['cells'][0]['location']
    elif variant == 'duplicate-cell': table['cells'].append(deepcopy(table['cells'][0]))
    elif variant == 'cell-range': table['cells'][0]['row'] = table['rows'] + 1
    elif variant == 'span-range': table['cells'][0]['column_span'] = table['columns'] + 1
    elif variant == 'duplicate-table': value['tables'].append(deepcopy(table))
    elif variant == 'text-digest': value['text_sha256'] = 'f' * 64
    elif variant == 'raw-binding': value['raw_sha256'] = 'f' * 64
    elif variant == 'format-binding': value['format'] = 'xlsx'
    elif variant == 'profile-binding': value['profile']['fixture'] = 'other-profile'
    else: raise AssertionError(variant)


@pytest.mark.parametrize('variant', ['schema', 'location-range', 'location-type', 'location-bbox',
    'missing-table-location', 'missing-table-cells', 'table-cells-type', 'cell-type',
    'missing-cell-location', 'duplicate-cell', 'cell-range', 'span-range', 'duplicate-table',
    'text-digest', 'raw-binding', 'format-binding', 'profile-binding'])
def test_processed_result_rejection_preserves_both_complete_publications(w, monkeypatch, variant):
    # @case-id: TC-008-processed-bundle-validation
    receiver = Receiver(w)
    attempts = receiver_observer(monkeypatch)
    unexpected = []
    for old, candidate in zip(receiver.items, receiver.next):
        raw = candidate['raw']
        # Structurally corrupt a real creator-produced V2 result, then update
        # canonical result SHA/length so transport validation cannot mask it.
        result = deepcopy(candidate['result'])
        original_profile = sha(encode(result['profile']))
        malformed(result, variant)
        item = receiver.packet(raw, result, old['label'], previous=old)
        if variant == 'profile-binding': item['meta']['profile_sha256'] = original_profile
        if variant == 'format-binding': item['meta']['format'] = 'docx'
        before = w.snapshot()
        receiver.stage(item, reject=True, unexpected=unexpected)
        receiver.unchanged(before)
    # Positive commits run under the very same receive-only observer. A blanket
    # commit rejection cannot satisfy the negative cases above. Staging itself
    # still must not replace either published document.
    for candidate in receiver.next:
        receiver.stage(candidate)
    for old, saved in zip(receiver.items, receiver.saved):
        assert receiver.read(old, reference=saved['reference']) == saved
    assert attempts == []
    assert unexpected == [], unexpected
    observe('received-structure-rejection', {'variant': variant, 'targets': 2,
        'both_published_bundles_preserved': True, 'receiver_processing_attempts': attempts})
