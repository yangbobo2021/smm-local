"""Rejected immutable bundles cannot indefinitely consume shared admission quota."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import time
from uuid import uuid4

import pytest

from document_helpers import observe
from document_formats_processed_transport import TransportReceiver
from smm_local.document_snapshots import Snapshots
from smm_local.document_results import validate
from test_document_formats_management import Creator
from test_document_formats_processed_manifest import state
from test_document_formats_received_validation import sha
from test_document_formats_retry import keep
from test_document_formats_transfer_expiry import CORPUS
from test_hub_documents_contracts import w

MIB = 1024 ** 2
LIMIT = 256 * MIB


@pytest.mark.parametrize('mode', ['first', 'replacement'])
def test_rejected_processed_metadata_releases_quota_without_evicting_valid_uses(w, tmp_path, monkeypatch, mode):
    actor = Creator(w, 'hub')
    raw = (CORPUS / 'globalbodydocx.docx').read_bytes()
    keep('processed-capacity/current-candidate.docx', raw)
    candidate = {'project': actor.projects[0], 'name': 'current-candidate.docx'}
    uid, receipt, entry = actor.upload(candidate, raw)
    assert entry['latest_attempt']['status'] == 'failed'
    assert entry['published_snapshot'] is None and entry['retry_target']
    snapshots = Snapshots(actor.db)
    receiver = TransportReceiver(w, tmp_path, mode)
    extra, = [r for r in w.remote('GET', '/documents/files') if r['id'] == entry['id']]
    receiver.expected_extra_files = {entry['id']: extra}
    conflicts = []
    for item in receiver.next:
        result = deepcopy(item['result']);result['profile']['fixture'] += '-capacity-alternate'
        validate(result)
        bad = receiver.packet(item['raw'], result, item['label'], previous=item)
        for key in ('document_id', 'version', 'processing_version', 'capture_sequence', 'path'):
            bad['meta'][key] = item['meta'][key]
        keep('processed-capacity/conflicts/' + sha(bad['results']) + '.json', bad['results'])
        conflicts.append(bad)
    alias = receiver.packet(conflicts[0]['raw'], conflicts[0]['result'], 'live-alias')
    alias_path = tmp_path / 'live-alias.docx';alias_path.write_bytes(alias['raw'])
    alias['meta']['path'] = str(alias_path);receiver.paths.append(alias_path)
    with actor.db.connect() as connection:
        candidate_path = connection.execute('SELECT path FROM documents WHERE id=?', (entry['id'],)).fetchone()[0]
    receiver.paths.append(Path(candidate_path))
    receiver.guard(monkeypatch)
    rejected = []
    for item, bad in zip(receiver.next, conflicts):
        receiver.stage(item)
        before = state(w);keep('processed-capacity/state-before-' + item['label'] + '.json', json.dumps(before, default=str).encode())
        transfer = receiver.stage(bad, reject=True);rejected.append(transfer['transfer_id'])
        after = state(w);keep('processed-capacity/state-after-' + item['label'] + '.json', json.dumps(after, default=str).encode())
        assert after == before
    # A distinct recent, unfinished transfer legitimately shares the rejected
    # first result. Its bytes must survive reclamation of the rejected owner.
    live = receiver.begin(alias)
    for kind, body in (('raw', alias['raw']), ('results', alias['results'])):
        for offset in range(live['received'][kind], len(body), live['block_bytes']):
            receiver.part(live['transfer_id'], kind, offset, body[offset:offset + live['block_bytes']])
    live = receiver.begin(alias)
    assert live['received'] == {'raw': len(alias['raw']), 'results': len(alias['results'])}
    receiver.unpublished('rejected-metadata-before-capacity')
    promises = []

    def physical():
        with actor.db.connect() as connection:
            published = {(r[0], r[1]) for r in connection.execute('SELECT kind,sha256 FROM document_published_blobs')}
        return sum(p.stat().st_size for kind in ('raw', 'results')
                   for p in (snapshots.root / kind).iterdir() if (kind, p.name) not in published)

    def accounted():
        total = physical() + sum(p['bytes'] for p in promises)
        assert snapshots._unpublished_bytes() == total
        return total

    def begin(size, label):
        prefix = label.encode() + b'\0'
        body = (prefix + b'\0' * size)[:size]
        keep('processed-capacity/promises/' + label + '.bin.gz', gzip.compress(body))
        request = {**actor.project(actor.projects[1]), 'name': label + '.docx',
                   'submission_id': uuid4().hex, 'bytes': size, 'sha256': sha(body)}
        response = actor.request('POST', '/documents/uploads', request, reject=size == 1)
        return request, response

    exclusive = conflicts[1]['meta']['result_sha256']
    def exclusive_present():
        return any((snapshots.root / 'results' / name).exists() for name in (exclusive, '.incoming-' + exclusive))

    # Resource declarations only: these byte promises are never parsed or
    # represented as successful documents. No 256MiB physical fixture is made.
    index = 0
    while accounted() < LIMIT:
        size = min(20 * MIB, LIMIT - accounted())
        assert size > 1
        request, response = begin(size, 'quota-fill-' + str(index))
        assert response.json()['received_parts'] == []
        promises.append(request);index += 1
        assert index < 20
    assert accounted() == LIMIT
    observe('processed-capacity-full-accounting', {'physical_bytes': physical(),
        'promises': promises, 'total': accounted(), 'limit': LIMIT,
        'files': {kind + '/' + p.name: {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
                  for kind in ('raw', 'results') for p in (snapshots.root / kind).iterdir()}})
    # At the actual shared ceiling an additional byte must be rejected.
    _, denied = begin(1, 'quota-over-before')
    assert '256MiB' in denied.text
    retained_before_age = exclusive_present()
    for transfer in [*rejected, uid]:
        path = snapshots.root / 'transfers' / transfer / 'state.json'
        if not path.exists():
            assert transfer != uid
            observe('processed-capacity-already-reclaimed', {'transfer_id': transfer})
            continue
        value = json.loads(path.read_bytes());original = value['created_at']
        value['created_at'] = time.time() - 25 * 3600
        path.write_text(json.dumps(value), encoding='utf-8')
        keep('processed-capacity/aged/' + transfer + '.json', path.read_bytes())
        observe('processed-capacity-owned-clock', {'transfer_id': transfer, 'before': original,
            'after': value['created_at'], 'purpose': 'only task-owned persisted timestamps; no OS clock change'})
    before = state(w)
    probe = {**actor.project(actor.projects[1]), 'name': 'quota-recovered.docx',
             'submission_id': uuid4().hex, 'bytes': 1, 'sha256': sha(b'Z')}
    # Eager reclamation is valid too. If the rejected exclusive body was
    # already reclaimed before filling, fresh legitimate promises own the cap.
    response = actor.request('POST', '/documents/uploads', probe, reject=not retained_before_age)
    if retained_before_age:
        assert response.json()['received_parts'] == []
        promises.append(probe)
        assert not exclusive_present()
        assert accounted() < LIMIT
    else:
        assert '256MiB' in response.text
    assert state(w) == before
    assert receiver.begin(alias) == live
    for kind, body in (('raw', alias['raw']), ('results', alias['results'])):
        target = snapshots.blob(kind, sha(body))
        actual = target if target.exists() else snapshots.root / kind / ('.incoming-' + sha(body))
        assert actual.read_bytes() == body
    assert snapshots.blob('raw', sha(raw)).read_bytes() == raw
    current, = [r for r in w.remote('GET', '/documents/library') if r['id'] == entry['id']]
    assert current == entry
    replay = actor.request('POST', '/documents/uploads/' + uid + '/commit', actor.context).json()
    assert replay == {**receipt, 'status': 'failed', 'version': 0, 'processing_version': 0}
    receiver.unpublished('rejected-metadata-after-capacity-reclamation')
    for bad, transfer in zip(conflicts, rejected):
        frozen = state(w)
        w.reject_remote('POST', '/documents/processed/begin',
            {**receiver.binding, 'submission_id': bad['submission'], 'document': bad['meta']})
        receiver.part(transfer, 'results', 0, bad['results'][:MIB], reject=True)
        w.reject_remote('POST', '/documents/processed/commit', {'transfer_id': transfer})
        assert state(w) == frozen
    for item in receiver.next: receiver.stage(item)  # Original valid stages remain usable.
    receiver.finish()
    observe('processed-capacity-complete', {'mode': mode, 'limit': LIMIT,
        'rejected_exclusive_retained_before_age': retained_before_age,
        'current_failed_capture_and_live_alias_preserved': True,
        'receiver_processing': receiver.processing, 'physical_bytes': physical(),
        'promised_bytes': sum(p['bytes'] for p in promises)})
