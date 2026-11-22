"""Self-contained negative controls for the evidence auditor, not SMM evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

import pytest


@pytest.fixture
def audit_fixture(tmp_path):
    path = Path(__file__).resolve().parents[1] / 'scripts/acceptance/selective_upload_audit.py'
    spec = importlib.util.spec_from_file_location('selective_auditor', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    root = tmp_path / 'recorded-fixture'; root.mkdir()
    def save(name, value): (root / (name + '.json')).write_text(json.dumps(value))
    candidate, installed, wheels = {'revision': 'unit-test-fixture'}, {}, []
    for kind in ['local', 'hub']:
        wheel = tmp_path / (kind + '.whl'); filename = 'smm_' + kind + '/__init__.py'; raw = b'# auditor unit fixture only\n'
        with zipfile.ZipFile(wheel, 'w') as archive: archive.writestr(filename, raw)
        files = {filename: hashlib.sha256(raw).hexdigest()}
        candidate['installed_' + kind] = files
        candidate[kind + '_wheel'] = {'sha256': hashlib.sha256(wheel.read_bytes()).hexdigest()}
        installed[kind] = {'files': files, 'other_package': False}
        wheels.append(wheel)
    save('manifest', {'candidate': candidate, 'installed': installed, 'mode': 'client', 'platform': 'auditor-unit-fixture'})
    save('result', {'status': 'passed'}); save('cleanup', {'failures': []})
    save('new-connection-status', {'state': 'needs_selection'})
    save('stopped-state', {'state': 'confirmed', 'policy': {'mode': 'none'}, 'device_id': 'a' * 32})
    bodies = {'local-A': ['selective common local-A original', 'selective common local-A appended while stopped'],
              'local-A-new': ['selective common local-A new while stopped'],
              'remote-B': ['selective common remote-B original'], 'vibe-V': ['selective common VibeInsight original']}
    def messages(session):
        return [{'text': text, 'role': 'user' if i == 0 else 'assistant', 'position': i + 1}
                for i, text in enumerate(bodies[session])]
    def hit(session):
        # Fixed independent golden scores for 10/6/4/4 token documents, N=df=4.
        return {'source_session_id': session, 'source': 'vibeinsight' if session == 'vibe-V' else 'codex',
                'id': 1 if session in ['local-A', 'vibe-V'] else 2,
                'reference': 'unit-reference-' + session, 'matched_messages': messages(session),
                'rerank_score': .1053605156578263 if session == 'local-A-new' else .1219963865511673}
    def query(names, offline=False):
        return {'results': [hit(n) for n in names], 'coverage': {'hub': 'unavailable' if offline else 'complete'},
                'effective_projects': [{'name': n} for n in ['A', 'B', 'synthetic.example/005/V']]}
    def originals(names):
        return [{'source_session_id': n, 'source': 'vibeinsight' if n == 'vibe-V' else 'codex',
                 'messages': messages(n)} for n in names]
    for stage in ['combined-stopped', 'reconnected', 'local-restarted', 'offline']:
        names = ['local-A', 'local-A-new'] if stage == 'offline' else list(bodies)
        data = query(names, stage == 'offline'); reads = originals(names)
        for channel in ['cli', 'mcp']:
            save(stage + '-' + channel + '-search', data); save(stage + '-' + channel + '-reads', reads)
        save(stage + '-browser', {'search': data, 'reads': reads, 'page_errors': []})
    bodies['local-D'] = ['selective common local-D original']
    bodies['local-G'] = ['selective common local-G original']
    bodies['local-U'] = ['selective common local-U original']
    bodies['remote-C'] = ['selective common remote-C original']
    bodies['plugin-history'] = ['selective common plugin-only original']
    save('explicit-local', query(['local-A', 'local-A-new', 'local-D']))
    save('all-local', query(['local-A', 'local-A-new', 'local-D', 'local-G', 'local-U', 'plugin-history']))
    save('browser-configuration', {'fixture': 'configuration already observed externally'})
    save('initial-stop-replay', {'before': ['original'], 'after': ['original'],
                                'attempts': [{'status': 409}, {'status': 403}]})
    save('backfill', {'hub': [hit(n) for n in bodies if n != 'plugin-history'],
                     'state': {'state': 'confirmed', 'transfer_state': 'complete',
                               'allowed_pending_messages': 0, 'inflight_messages': 0},
                     'old-reference-read': {'messages': [{'text': bodies['local-A'][0]}]}})
    save('retained-version-original', {'messages': [{'text': 'versionprobe original archived version'}]})
    save('version-and-long-originals', {query: {'reads': [{'messages': [{'text': t} for t in texts]}] * 2}
        for query, texts in [('versionprobe', ['versionprobe original archived version', 'versionprobe changed local version']),
                             ('longneedle', ['paddingword ' * 2000 + 'longneedle end original'])]})
    save('payloads', [{'route': '/v1/search', 'payload': {'query': 'selective', 'limit': 20}}])
    save('stopped-payloads', [{'route': '/v1/upload', 'payload': {'device_id': 'a' * 32, 'records': []}}])
    return module, root, wheels, save


def test_auditor_accepts_complete_synthetic_unit_fixture(audit_fixture):
    module, root, wheels, _ = audit_fixture
    assert module.audit(root, *wheels)['status'] == 'passed'


@pytest.mark.parametrize('fault,reason', [('missing_append', 'backfill A body'), ('wrong_score', 'score divergence'),
                                        ('candidate_egress', 'ranking payload'), ('false_complete', 'still pending'),
                                        ('wrong_original', 'exact original body')])
def test_auditor_rejects_false_pass_even_when_result_status_is_passed(audit_fixture, fault, reason):
    module, root, wheels, save = audit_fixture
    stem = {'missing_append': 'backfill', 'wrong_score': 'combined-stopped-cli-search',
            'candidate_egress': 'payloads', 'false_complete': 'backfill',
            'wrong_original': 'combined-stopped-mcp-reads'}[fault]
    data = json.loads((root / (stem + '.json')).read_text())
    if fault == 'missing_append':
        next(h for h in data['hub'] if h['source_session_id'] == 'local-A')['matched_messages'].pop()
    elif fault == 'wrong_score': data['results'][0]['rerank_score'] += 1
    elif fault == 'candidate_egress': data[0]['payload']['local_candidates'] = ['private body']
    elif fault == 'false_complete': data['state']['allowed_pending_messages'] = 1
    else: data[0]['messages'][0]['text'] = 'wrong archive body'
    save(stem, data)
    assert json.loads((root / 'result.json').read_text())['status'] == 'passed'
    with pytest.raises(AssertionError, match=reason): module.audit(root, *wheels)
