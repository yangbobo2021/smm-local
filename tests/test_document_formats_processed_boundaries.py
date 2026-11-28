"""Malformed chunks cannot advance or publish a creator-produced bundle."""
import pytest

from document_helpers import observe
from document_formats_processed_transport import TransportReceiver
from test_document_formats_received_validation import sha
from test_hub_documents_contracts import w


@pytest.mark.parametrize('mode', ['first', 'replacement'])
@pytest.mark.parametrize('variant', ['chunk-sha', 'gap-offset', 'short-block', 'duplicate-block'])
def test_invalid_chunks_preserve_the_bundle_until_a_complete_legal_publish(w, tmp_path, monkeypatch, mode, variant):
    # @case-id: TC-008-processed-bundle-validation
    receiver = TransportReceiver(w, tmp_path, mode)
    receiver.guard(monkeypatch)
    for item in receiver.next:
        started = receiver.begin(item)
        for kind in ('raw', 'results'):
            first = item[kind][:started['block_bytes']]
            if variant == 'duplicate-block':
                accepted = receiver.part(started['transfer_id'], kind, 0, first)
                assert accepted['received'][kind] == len(first)
                assert receiver.part(started['transfer_id'], kind, 0, first) == accepted
                raw = bytes([first[0] ^ 1]) + first[1:];offset = 0;header = sha(raw)
            elif variant == 'gap-offset':
                offset = started['block_bytes'];raw = item[kind][offset:offset + started['block_bytes']];header = sha(raw)
                assert offset > 0 and raw
            elif variant == 'short-block':
                offset = 0;raw = first[:-1];header = sha(raw)
                assert len(raw) < min(started['block_bytes'], len(item[kind]))
            else:
                offset = 0;raw = first;header = '0' * 64
                assert header != sha(raw)
            before = w.snapshot();status = receiver.begin(item)
            observe('processed-malformed-chunk-input', {'mode': mode, 'variant': variant,
                'document_id': item['meta']['document_id'], 'kind': kind, 'offset': offset,
                'bytes': len(raw), 'actual_sha256': sha(raw), 'header_sha256': header})
            receiver.part(started['transfer_id'], kind, offset, raw, expected_sha=header, reject=True)
            assert receiver.begin(item) == status
            assert w.snapshot() == before
            receiver.unpublished(variant + '-' + kind + '-' + item['label'])
        # This actual positive stage uses the very same receive-only and source
        # guards. A blanket rejection cannot satisfy the preceding negatives.
        receiver.stage(item)
    receiver.unpublished(variant + '-all-staged')
    receiver.finish()
