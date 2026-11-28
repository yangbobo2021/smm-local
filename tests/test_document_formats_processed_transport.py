"""Real full-body integrity failure must not poison another legal transfer."""
from copy import deepcopy
from uuid import uuid4

import pytest

from document_helpers import observe
from document_formats_processed_transport import TransportReceiver
from test_document_formats_received_validation import sha
from test_document_formats_retry import keep
from test_hub_documents_contracts import w


@pytest.mark.parametrize('mode', ['first', 'replacement'])
@pytest.mark.parametrize('kind', ['raw', 'results'])
def test_wrong_complete_body_cannot_block_a_fresh_legal_submission(w, tmp_path, monkeypatch, mode, kind):
    # @case-id: TC-008-processed-bundle-validation
    receiver = TransportReceiver(w, tmp_path, mode)
    receiver.guard(monkeypatch)
    failures = []
    for item in receiver.next:
        started = receiver.begin(item)
        before = w.snapshot()
        for body_kind in ('raw', 'results'):
            raw = item[body_kind]
            if body_kind == kind:
                raw = raw[:-1] + bytes([raw[-1] ^ 1])
                assert len(raw) == item['meta']['raw_bytes' if kind == 'raw' else 'result_bytes']
                keep('processed-transport/rejected-bodies/' + sha(raw) + '.bin', raw)
            # Each chunk correctly declares its actual bytes. Only the final
            # whole-object SHA differs from the canonical metadata's truth.
            for start in range(0, len(raw), started['block_bytes']):
                receiver.part(started['transfer_id'], body_kind, start, raw[start:start + started['block_bytes']])
        w.reject_remote('POST', '/documents/processed/commit', {'transfer_id': started['transfer_id']})
        assert w.snapshot() == before
        receiver.unpublished('wrong-full-' + kind + '-' + item['label'])
        fresh = deepcopy(item);fresh['submission'] = uuid4().hex
        try: receiver.stage(fresh)
        except AssertionError as error:
            failures.append({'label': item['label'], 'error': str(error)})
            receiver.old_bundles()
    observe('processed-full-sha-recovery', {'mode': mode, 'kind': kind,
        'targets': 2, 'fresh_legal_submission_failures': failures,
        'processing_attempts': receiver.processing,
        'source_open_controls': receiver.source_reads[:receiver.known_source_controls],
        'business_source_opens': receiver.source_reads[receiver.known_source_controls:]})
    assert failures == [], failures
    receiver.unpublished('all-legal-stages-still-unpublished')
    receiver.finish()


@pytest.mark.parametrize('mode', ['first', 'replacement'])
@pytest.mark.parametrize('kind', ['raw', 'results'])
def test_incomplete_body_keeps_its_prefix_for_a_fresh_resuming_submission(w, tmp_path, monkeypatch, mode, kind):
    receiver = TransportReceiver(w, tmp_path, mode)
    receiver.guard(monkeypatch)
    for item in receiver.next:
        started = receiver.begin(item)
        for body_kind in ('raw', 'results'):
            raw = item[body_kind]
            stop = started['block_bytes'] if body_kind == kind else len(raw)
            for start in range(0, stop, started['block_bytes']):
                receiver.part(started['transfer_id'], body_kind, start, raw[start:start + started['block_bytes']])
        w.reject_remote('POST', '/documents/processed/commit', {'transfer_id': started['transfer_id']})
        receiver.unpublished('incomplete-' + kind + '-' + item['label'])
        fresh = deepcopy(item);fresh['submission'] = uuid4().hex
        resumed = receiver.begin(fresh)
        assert resumed['received'][kind] == started['block_bytes']
        other = 'results' if kind == 'raw' else 'raw'
        assert resumed['received'][other] == len(item[other])
        for body_kind in ('raw', 'results'):
            raw = item[body_kind]
            for start in range(resumed['received'][body_kind], len(raw), resumed['block_bytes']):
                receiver.part(resumed['transfer_id'], body_kind, start, raw[start:start + resumed['block_bytes']])
        assert w.remote('POST', '/documents/processed/commit', {'transfer_id': resumed['transfer_id']})['staged'] is True
    receiver.unpublished('resumed-stages-before-manifest')
    receiver.finish()


@pytest.mark.parametrize('kind', ['raw', 'results'])
def test_integrity_error_never_deletes_a_canonical_published_blob(tmp_path, kind):
    from document_helpers import Fixture
    from document_formats_fixtures import docx_fixture
    from smm_local.documents import Documents
    from smm_local.document_transfers import BlobTransfers
    f = Fixture(tmp_path)
    raw, truth = docx_fixture('canonicalguard')
    project = f.project('canonical guard')
    source = f.add(f.file('canonical.docx', raw=raw), [project]);f.refresh(source)
    hit, = f.search(truth['words'][0], local=True)['results']
    baseline = f.read(hit, start=0, end=hit['text_length'])
    snapshots = Documents(f.db).snapshots
    blobs = {'raw': {'sha256': hit['sha256'], 'bytes': len(raw)},
             'results': {'sha256': hit['result_sha256'],
                         'bytes': len(snapshots.blob('results', hit['result_sha256']).read_bytes())}}
    path = snapshots.blob(kind, blobs[kind]['sha256'])
    original = path.read_bytes();corrupt = original[:-1] + bytes([original[-1] ^ 1])
    binding = {key: uuid4().hex for key in ('hub_id', 'document_epoch', 'device_id', 'archive_id', 'project_key', 'submission_id')}
    binding['generation'] = 1
    try:
        path.write_bytes(corrupt)  # This test's own synthetic storage fault.
        with pytest.raises(ValueError, match='摘要错误'):
            BlobTransfers(snapshots).begin(binding, blobs)
        assert path.exists() and path.read_bytes() == corrupt, 'canonical evidence must never be removed as incoming scratch'
    finally:
        path.write_bytes(original)  # Restore the injected fault, not a transfer.
    assert f.read(hit, start=0, end=hit['text_length']) == baseline
    response = f.client.post('/api/documents/original', json={'reference': hit['reference']})
    assert response.status_code == 200 and response.content == raw
    observe('canonical-published-blob-preserved-' + kind,
            {'sha256': blobs[kind]['sha256'], 'bytes': len(original), 'injected_sha256': sha(corrupt),
             'canonical_preserved_during_failure': True, 'fault_restored_old_reference_exact': True})
