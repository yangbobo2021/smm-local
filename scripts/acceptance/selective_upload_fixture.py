"""Synthetic 005 input generator, run by the actual installed product interpreter.

Never opens a source server; all paths must be beneath the caller's task directory.
"""
import argparse
import json
from pathlib import Path


def history(root, session, project, bodies):
    directory = root / 'sessions'; directory.mkdir(parents=True, exist_ok=True)
    cwd = root / 'work' / project if project else None
    if cwd: cwd.mkdir(parents=True, exist_ok=True)
    rows = [{'type': 'session_meta', 'payload': {'id': session, **({'cwd': str(cwd)} if cwd else {})}}]
    rows += [{'type': 'response_item', 'ordinal': i, 'payload': {'type': 'message', 'id': session + f'-m{i}',
        'role': 'user' if i % 2 else 'assistant', 'content': [{'type': 'input_text', 'text': text}]}}
        for i, text in enumerate(bodies, 1)]
    (directory / (session + '.jsonl')).write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')


def prepare(root, device):
    from smm_local.core import Archive
    root.mkdir(parents=True, exist_ok=True)
    database = root / 'archive.sqlite3'
    assert not database.exists(), 'task archive already exists'
    labels = ['A', 'D', 'G', 'U'] if device == 'local' else ['B', 'C']
    for name in labels:
        history(root, device + '-' + name, name if name != 'U' else None, ['selective common ' + device + '-' + name + ' original'])
    empty = root / 'empty'; empty.mkdir()
    db = Archive(database)
    db.set_settings(codex_root=str(root / 'sessions'), claude_root=str(empty), sync_interval_seconds=10)
    db.sync_codex()
    if device == 'local':
        g = db.ensure_global_project()
        hit = next(h for h in db.search('selective', limit=50)['results'] if h['source_session_id'] == 'local-G')
        db.assign_conversation(hit['id'], g['id'])
        ids = {p['name']: p['id'] for p in db.projects()}
        db.link_projects(ids['A'], ids['D'])
        # One plugin record participates in local all queries; plugin bodies never upload.
        plugin = root / 'plugin'; plugin.mkdir()
        body = {'session_id': 'plugin-history', 'message_id': 'plugin-m1', 'position': 1,
                'role': 'user', 'text': 'selective common plugin-only original', 'origin': 'records.json'}
        extra = {**body, 'message_id': 'plugin-m2', 'position': 2, 'role': 'assistant', 'text': 'selective common plugin-only appended'}
        for name in ('before', 'after', 'live'):
            (plugin / name).mkdir(); (plugin / name / 'records.json').write_text(json.dumps([body] if name == 'before' else [body, extra]), encoding='utf-8')
        (plugin / 'adapter.py').write_text("import json,sys\nfrom pathlib import Path\nr=json.load(sys.stdin); rows=json.loads(Path(r['root']).read_text()); start=int(r['cursor'] or 0); end=min(len(rows),start+r['limit']); print(json.dumps({'messages':rows[start:end],'cursor':str(end),'more':end<len(rows)}))\n", encoding='utf-8')
        manifest = {'id': 'synthetic-005', 'name': '005 fixture', 'version': 1, 'root': str(plugin / 'live' / 'records.json'), 'script': 'adapter.py'}
        fixture = {'scope': {'kind': 'all'}, 'before': str(plugin / 'before' / 'records.json'), 'after': str(plugin / 'after' / 'records.json'), 'expected_before': [body], 'expected_added': [extra]}
        (plugin / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        (plugin / 'fixture.json').write_text(json.dumps(fixture), encoding='utf-8')
        from smm_local.importers.registry import configure
        configure(db, plugin / 'manifest.json', plugin / 'fixture.json', register=True)
        db.sync_all()
    return {'database': str(database), 'projects': db.projects(), 'search': db.search('selective', limit=50)}


def seed_vibe(root):
    from smm_hub._archive import Archive
    from smm_hub.vibeinsight import VibeInsightSync
    root.mkdir(parents=True, exist_ok=True)
    class Source:
        def validate(self): pass
        def projects(self, through=None): return ['synthetic.example/005/V']
        def upper(self): return ('2026-11-01T00:00:00', 'v-event-1')
        def page(self, project, after, through, limit):
            row = {'id': 'v-event-1', 'created_at': '2026-11-01T00:00:00', 'event_timestamp': '2026-11-01T00:00:00',
                   'user_id': 'synthetic-owner', 'platform_code': 'codex', 'session_id': 'vibe-V', 'trace_id': 'v-trace-1',
                   'event_type': 'trace.started', 'message': 'selective common VibeInsight original', 'project': project}
            return [row] if after is None or (row['created_at'], row['id']) > after else []
    db = Archive(root / 'smm-hub.sqlite3'); VibeInsightSync(db, 'synthetic-005-source').run(Source())
    return {'fixture': 'synthetic-only', 'messages': db.status()['messages']}


def main():
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['prepare', 'append', 'seed-vibe']); p.add_argument('--root', type=Path, required=True); p.add_argument('--device', default='local')
    args = p.parse_args(); root = args.root.resolve()
    if args.action == 'prepare': result = prepare(root, args.device)
    elif args.action == 'seed-vibe': result = seed_vibe(root)
    else:
        history(root, 'local-A', 'A', ['selective common local-A original', 'selective common local-A appended while stopped'])
        history(root, 'local-A-new', 'A', ['selective common local-A new while stopped'])
        result = {'appended': ['local-A-m2', 'local-A-new-m1']}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__': main()
