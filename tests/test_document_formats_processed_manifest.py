"""Full manifests and their CAS identities gate the complete processed bundle."""
from copy import deepcopy
from uuid import uuid4

import pytest

from document_helpers import observe
from document_formats_processed_transport import TransportReceiver
from test_hub_documents_contracts import w


def state(world):
    # The older generic snapshot intentionally matches %document% tables;
    # processed stages have another name and need their own complete proof.
    with world.pair.remote.connect() as connection:
        stages = [dict(row) for row in connection.execute('SELECT * FROM hub_processed_stages '
            'ORDER BY device_id,archive_id,document_id,version,processing_version')]
    return {'business': world.snapshot(), 'processed_stages': stages}


@pytest.mark.parametrize('mode', ['first', 'replacement'])
@pytest.mark.parametrize('variant', ['unstaged-member', 'metadata-mismatch', 'duplicate-document',
                                    'old-control', 'old-source', 'submission-payload'])
def test_complete_manifest_rejects_stale_or_inconsistent_publication(w, tmp_path, monkeypatch, mode, variant):
    # @case-id: TC-008-processed-bundle-validation
    receiver = TransportReceiver(w, tmp_path, mode)
    receiver.guard(monkeypatch)
    receiver.stage(receiver.next[0])
    frame = receiver.manifest(receiver.final_items, sequence=2)
    if variant == 'unstaged-member':
        before = state(w)
        w.reject_remote('POST', '/documents/publish', frame)
        assert state(w) == before
        receiver.unpublished('declared-but-unstaged-second-member')
    receiver.stage(receiver.next[1])
    receiver.unpublished('complete-stages-not-yet-published')
    if variant in {'metadata-mismatch', 'duplicate-document'}:
        for index in range(2):
            bad = deepcopy(frame);bad['submission_id'] = uuid4().hex
            if variant == 'metadata-mismatch':
                assert bad['files'][index]['result_sha256'] != 'f' * 64
                bad['files'][index]['result_sha256'] = 'f' * 64
            else: bad['files'].append(deepcopy(bad['files'][index]))
            before = state(w)
            w.reject_remote('POST', '/documents/publish', bad)
            assert state(w) == before
            receiver.unpublished(variant + '-target-' + str(index))
    elif variant == 'old-control':
        retained = [{'source_id': 'b' * 32, 'revision': 1,
                     'files': [{'document_id': item['meta']['document_id'], 'qualification': 1}
                               for item in receiver.items]}]
        actual = w.control(receiver.binding, sequence=2, retained=retained)
        assert actual['sequence'] == 2 and frame['control_sequence'] == 1
        before = state(w)
        w.reject_remote('POST', '/documents/publish', frame)
        assert state(w) == before
        receiver.unpublished('old-control-only')
    elif variant in {'old-source', 'submission-payload'}:
        first = w.publish(frame)
        before = state(w)
        assert w.publish(frame) == first
        assert state(w) == before
        bad = deepcopy(frame)
        if variant == 'old-source':
            bad['submission_id'] = uuid4().hex;bad['sequence'] = 1
            assert frame['sequence'] == 2
        else:
            # New sequence and the same current complete files are a valid
            # payload. Only reuse of the old submission makes this request bad.
            bad['sequence'] = 3
        w.reject_remote('POST', '/documents/publish', bad)
        assert state(w) == before
        if variant == 'submission-payload':
            bad['submission_id'] = uuid4().hex
            w.publish(bad)  # Exact changed payload succeeds with a fresh nonce.
        receiver.finish(publish=False)
        observe('processed-published-manifest-CAS', {'mode': mode, 'variant': variant,
            'old_positive_source_sequence': 1, 'published_sequence': 2,
            'fresh_changed_payload_sequence': 3 if variant == 'submission-payload' else None})
        return
    receiver.finish()
    observe('processed-manifest-qualified', {'mode': mode, 'variant': variant,
        'two_targets_and_retained_non_target_complete': True})
