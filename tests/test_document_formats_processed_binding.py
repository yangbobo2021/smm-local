"""Transfer nonces and immutable V/P tuples cannot be rebound to new data."""
from copy import deepcopy
from uuid import uuid4

import pytest

from document_helpers import observe
from document_formats_processed_transport import TransportReceiver, large_material
from smm_local.document_results import validate
from test_document_formats_received_validation import sha
from test_document_formats_retry import keep
from test_document_formats_processed_manifest import state
from test_hub_documents_contracts import w


@pytest.mark.parametrize('mode', ['first', 'replacement'])
def test_processed_begin_nonce_keeps_its_exact_capture_binding(w, tmp_path, monkeypatch, mode):
    receiver = TransportReceiver(w, tmp_path, mode)
    receiver.guard(monkeypatch)
    for item in receiver.next:
        original = receiver.begin(item)
        changed = deepcopy(item['meta']);changed['capture_id'] = uuid4().hex
        assert changed['capture_id'] != item['meta']['capture_id']
        before = state(w)
        w.reject_remote('POST', '/documents/processed/begin',
            {**receiver.binding, 'submission_id': item['submission'], 'document': changed})
        assert receiver.begin(item) == original and state(w) == before
        receiver.unpublished('nonce-capture-binding-' + item['label'])
        receiver.stage(item)
    receiver.finish()


@pytest.mark.parametrize('mode', ['first', 'replacement'])
@pytest.mark.parametrize('variant', ['raw-result', 'profile', 'result-only'])
def test_same_document_version_and_processing_version_reject_other_canonical_payload(w, tmp_path, monkeypatch, mode, variant):
    receiver = TransportReceiver(w, tmp_path, mode)
    conflicts = []
    for item in receiver.next:
        if variant == 'raw-result':
            raw, result = large_material(item['label'] + 'Conflict', item['meta']['version'])
        else:
            raw = item['raw'];result = deepcopy(item['result'])
            if variant == 'profile': result['profile']['fixture'] += '-alternate'
            else:
                # Schema-valid changed result metadata is intentional hostile
                # input, not a claim that the raw Word has these revisions.
                # Raw/profile/text are unchanged: result identity still matters.
                result['coverage']['revisions_present'] = not result['coverage']['revisions_present']
        validate(result)
        bad = receiver.packet(raw, result, item['label'], previous=item)
        for key in ('document_id', 'version', 'processing_version', 'capture_sequence', 'path'):
            bad['meta'][key] = item['meta'][key]
        assert bad['meta']['result_sha256'] != item['meta']['result_sha256']
        if variant == 'result-only':
            assert all(bad['meta'][key] == item['meta'][key]
                       for key in ('sha256', 'text_sha256', 'profile_sha256', 'format'))
        keep('processed-binding/conflicts/raw/' + sha(bad['raw']) + '.docx', bad['raw'])
        keep('processed-binding/conflicts/results/' + sha(bad['results']) + '.json', bad['results'])
        conflicts.append(bad)
    receiver.guard(monkeypatch)  # All creator parsing/hostile data preparation precedes this guard.
    for item, bad in zip(receiver.next, conflicts):
        receiver.stage(item)
        before = state(w)
        receiver.stage(bad, reject=True)
        assert state(w) == before
        receiver.unpublished('same-VP-' + variant + '-' + item['label'])
        correct = deepcopy(item);correct['submission'] = uuid4().hex
        receiver.stage(correct)  # Same guard, correct tuple and body succeed.
    receiver.finish()
    observe('processed-immutable-VP', {'mode': mode, 'variant': variant,
        'targets': 2, 'exact_original_stage_rows_preserved': True,
        'receiver_processing_attempts': receiver.processing,
        'business_source_opens': receiver.source_reads[receiver.known_source_controls:]})
