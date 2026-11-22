"""Audit recorded synthetic platform facts without querying or running SMM.

This checks package provenance, bodies, ranges, ranking and outbound payloads.
It is not a visual review or a complete A1-A12/E1-E5 delivery judgment.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile


def require(condition, label):
    if not condition: raise AssertionError(label)


def audit(directory, local_wheel, hub_wheel):
    root = Path(directory)
    def read(name): return json.loads((root / (name + '.json')).read_text(encoding='utf-8-sig'))
    manifest, result = read('manifest'), read('result')
    require(result['status'] == 'passed', 'business attempt did not complete')
    require(read('cleanup')['failures'] == [], 'task cleanup failed')
    for kind, wheel in [('local', local_wheel), ('hub', hub_wheel)]:
        wheel = Path(wheel)
        with zipfile.ZipFile(wheel) as archive:
            expected = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()
                        if name.startswith('smm_' + kind + '/') and not name.endswith('/')}
        require(manifest['candidate'][kind + '_wheel']['sha256'] == hashlib.sha256(wheel.read_bytes()).hexdigest(), 'wheel identity: ' + kind)
        require(manifest['candidate']['installed_' + kind] == expected, 'candidate module identity: ' + kind)
        require(manifest['installed'][kind]['files'] == expected, 'installed module identity: ' + kind)
        require(manifest['installed'][kind]['other_package'] is False, 'environments are not independent')
    require(read('new-connection-status')['state'] == 'needs_selection', 'new connection choice')
    stop = read('stopped-state')
    require(stop['state'] == 'confirmed' and stop['policy']['mode'] == 'none', 'confirmed stop')
    expected_sessions = {'local-A', 'local-A-new', 'remote-B', 'vibe-V'}
    expected_bodies = {'local-A': ['selective common local-A original', 'selective common local-A appended while stopped'],
                       'local-A-new': ['selective common local-A new while stopped'],
                       'remote-B': ['selective common remote-B original'],
                       'vibe-V': ['selective common VibeInsight original']}
    def sessions(data): return {h['source_session_id'] for h in data['results']}
    def check_query(data, expected, offline=False):
        require(sessions(data) == expected, 'query scope/session set')
        require(all(h.get('reference') for h in data['results']), 'missing per-hit reference')
        require(data['coverage']['hub'] == ('unavailable' if offline else 'complete'), 'actual Hub coverage')
    def check_originals(reads, expected):
        require({r['source_session_id'] for r in reads} == expected, 'original-read session set')
        for original in reads:
            name = original['source_session_id']
            require([m['text'] for m in original['messages']] == expected_bodies[name], 'exact original body/order: ' + name)
            require([m['role'] for m in original['messages']] ==
                    (['user', 'assistant'] if name == 'local-A' else ['user']), 'exact original role: ' + name)
            require(original['source'] == ('vibeinsight' if name == 'vibe-V' else 'codex'), 'wrong original source')
    for stage in ['combined-stopped', 'reconnected', 'local-restarted', 'offline']:
        expected = {'local-A', 'local-A-new'} if stage == 'offline' else expected_sessions
        cli, mcp = read(stage + '-cli-search'), read(stage + '-mcp-search')
        check_query(cli, expected, stage == 'offline'); check_query(mcp, expected, stage == 'offline')
        check_originals(read(stage + '-cli-reads'), expected); check_originals(read(stage + '-mcp-reads'), expected)
        if stage != 'offline':
            require({h['source_session_id']: h['rerank_score'] for h in cli['results']} ==
                    {h['source_session_id']: h['rerank_score'] for h in mcp['results']}, 'CLI/MCP score divergence')
        if (root / (stage + '-browser.json')).exists():
            browser = read(stage + '-browser')
            require(browser['page_errors'] == [], 'browser page error')
            check_query(browser['search'], expected, stage == 'offline')
            check_originals(browser['reads'], expected)
        elif manifest['mode'] != 'hub-service':
            raise AssertionError('missing actual browser attempt')
    scoped = read('combined-stopped-cli-search')
    require({p['name'] for p in scoped['effective_projects']} == {'A', 'B', 'synthetic.example/005/V'}, 'effective shared snapshot')
    by_session = {h['source_session_id']: h for h in scoped['results']}
    require(by_session['local-A']['id'] == by_session['vibe-V']['id'], 'numeric ID collision fixture not exercised')
    require(by_session['local-A']['reference'] != by_session['vibe-V']['reference'], 'archive references collapsed')
    # Independent math for these English, whitespace-separated synthetic bodies.
    # It deliberately does not import the product tokenizer/ranker.
    documents = []
    for hit in scoped['results']:
        words = [word.lower() for m in hit['matched_messages'] for word in m['text'].split()]
        require(all(re.fullmatch(r'[a-z0-9][a-z0-9_.-]*', word) for word in words), 'unsupported audit fixture token')
        documents.append((hit, Counter(words)))
    average = sum(sum(c.values()) for _, c in documents) / len(documents)
    df = sum(c['selective'] > 0 for _, c in documents)
    idf = math.log1p((len(documents) - df + .5) / (df + .5))
    for hit, counts in documents:
        tf = counts['selective']
        expected = idf * tf * 2.2 / (tf + 1.2 * (.25 + .75 * sum(counts.values()) / average))
        require(math.isclose(hit['rerank_score'], expected, rel_tol=1e-10, abs_tol=1e-12), 'full-body BM25 score')
    require(sessions(read('explicit-local')) == {'local-A', 'local-A-new', 'local-D'}, 'explicit local links')
    require({'local-G', 'local-U', 'plugin-history'} <= sessions(read('all-local')), 'local global/unknown/plugin coverage')
    for label in ['initial-stop-replay', 'after-hub-restart-replay']:
        if not (root / (label + '.json')).exists():
            require(label.startswith('after-') and manifest['mode'] not in ('hub-service', 'self-managed'), 'missing old-request replay')
            continue
        replay = read(label)
        require(replay['before'] == replay['after'], 'rejected body changed archive')
        require(len(replay['attempts']) == 2 and all(a['status'] in (403, 409) for a in replay['attempts']), 'old/versionless body was accepted')
    backfill = read('backfill')
    hub = {h['source_session_id']: h for h in backfill['hub']}
    expected_hub = {'local-A', 'local-A-new', 'local-D', 'local-G', 'remote-B', 'remote-C', 'vibe-V'}
    if (root / 'browser-configuration.json').exists(): expected_hub.add('local-U')
    require(set(hub) == expected_hub, 'backfill allowed/unknown/plugin session set')
    require(backfill['state']['state'] == 'confirmed'
            and backfill['state']['allowed_pending_messages'] == 0
            and backfill['state']['inflight_messages'] == 0
            and backfill['state']['transfer_state'] == 'complete', 'backfill still pending/unknown')
    require([m['text'] for m in hub['local-A']['matched_messages']] ==
            ['selective common local-A original', 'selective common local-A appended while stopped'], 'backfill A body/order incomplete')
    require([m['text'] for m in hub['local-A-new']['matched_messages']] == ['selective common local-A new while stopped'], 'backfill new conversation incomplete')
    require(not {'local-U2', 'plugin-history'} & hub.keys(), 'unknown/plugin body uploaded')
    for session in expected_hub - {'local-A', 'local-A-new', 'vibe-V'}:
        require([m['text'] for m in hub[session]['matched_messages']] == ['selective common ' + session + ' original'], 'backfill peer body: ' + session)
    require([m['text'] for m in backfill['old-reference-read']['messages']] == ['selective common local-A original'], 'old reference changed')
    require([m['text'] for m in read('retained-version-original')['messages']] == ['versionprobe original archived version'], 'old version reference changed')
    for query, expected in [('versionprobe', {'versionprobe original archived version', 'versionprobe changed local version'}),
                            ('longneedle', {'paddingword ' * 2000 + 'longneedle end original'})]:
        observation = read('version-and-long-originals')[query]
        for original in observation['reads']:
            require({m['text'] for m in original['messages']} == expected and len(original['messages']) == len(expected), 'exact edge original: ' + query)
    allowed_search = {'query', 'current_session_id', 'current_source', 'include_current', 'limit', 'preview_chars', 'device_id', 'project_id', 'scope_reference'}
    for request in read('payloads'):
        payload = request['payload'] or {}
        if request['route'] == '/v1/search': require(set(payload) <= allowed_search, 'local candidate/ranking payload sent to Hub')
        if request['route'] == '/v1/project-metadata':
            require(not payload.get('memberships'), 'premature conversation metadata')
            require(all(set(p) <= {'id', 'name', 'kind', 'project_kind'} for p in payload['projects']), 'project path/body metadata')
        if request['route'] == '/v1/known-upload-messages':
            for r in payload['records']:
                require(set(r) <= {'conversation_digest', 'source_key', 'version', 'project_id', 'position', 'source_order'}, 'body in fingerprint lookup')
                require(all(re.fullmatch('[a-f0-9]{64}', r[k]) for k in ('conversation_digest', 'source_key', 'version')), 'non-digest fingerprint')
    for request in read('stopped-payloads'):
        payload = request['payload'] or {}
        if request['route'] == '/v1/upload' and payload.get('device_id') == stop['device_id']:
            require(not payload.get('records'), 'local body started after confirmed stop')
    inventory = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir() if p.is_file()}
    return {'status': 'passed', 'scope': 'recorded synthetic core platform facts; not complete A/E or visual delivery judgment',
            'platform': manifest['platform'], 'mode': manifest['mode'], 'candidate': manifest['candidate']['revision'],
            'checks': ['wheel and installed bytes', 'default and stop', 'three actual query scopes where required',
                       'same numeric ID references', 'independent full-body BM25', 'old requests',
                       'complete A append/new bodies', 'old/edge originals', 'outbound payload shape'], 'original_files': inventory}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    parser.add_argument('--local-wheel', type=Path, required=True)
    parser.add_argument('--hub-wheel', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'use a new audit output')
    result = audit(args.evidence_dir, args.local_wheel, args.hub_wheel)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('passed: recorded core facts; independent visual and complete-matrix review still required')
