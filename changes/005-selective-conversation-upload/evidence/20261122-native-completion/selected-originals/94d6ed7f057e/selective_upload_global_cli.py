"""E1 CLI global-project follow-up on a CLOSED synthetic platform archive."""
import argparse
import json
from pathlib import Path

from selective_upload_platform import Run, now


class GlobalCLI(Run):
    def run(self):
        self.installed()
        self.db = self.root / 'local' / 'archive.sqlite3'
        source = self.root / 'local' / 'sessions' / 'local-U.jsonl'
        assert self.db.is_file() and source.is_file(), 'requires this task synthetic archive'
        rows = [json.loads(line) for line in source.read_text(encoding='utf-8').splitlines()]
        assert rows[0]['payload']['id'] == 'local-U'
        assert rows[1]['payload']['content'][0]['text'] == 'selective common local-U original'
        first = self.cli(self.db, 'project', 'ensure-global')
        second = self.cli(self.db, 'project', 'ensure-global')
        assert first['id'] == second['id'] and first['stable_key'] == second['stable_key']
        assert sum(p['kind'] == 'global' for p in self.cli(self.db, 'projects')) == 1
        hits = self.cli(self.db, 'search', 'selective', '--local', '--limit', '50')['results']
        before = next(h for h in hits if h['source_session_id'] == 'local-U'); assert before['project_id'] is None
        unknown = next(h for h in hits if h['source_session_id'] == 'local-U2')
        assert unknown['project_id'] is None
        preview = self.cli(self.db, 'project', 'assign-conversation', str(before['id']), '--project-id', str(first['id']))
        assert preview['requires_confirmation'] and not preview['applied']
        applied = self.cli(self.db, 'project', 'assign-conversation', str(before['id']), '--project-id', str(first['id']), '--confirm', preview['confirmation'])
        assert applied['applied']
        # Change synthetic head metadata to force an actual replay from offset0.
        rows[0]['payload']['global_cli_replay'] = 'synthetic-005'
        source.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
        code = 'import sys,json;from smm_local.core import Archive;print(json.dumps(Archive(sys.argv[1]).sync_codex()))'
        replay = json.loads(self.command([self.t['local_python'], '-I', '-X', 'utf8', '-c', code, self.db]).stdout)
        after = self.cli(self.db, 'read', str(before['id']))
        still_unknown = self.cli(self.db, 'read', str(unknown['id']))
        assert after['project_id'] == first['id']
        assert [m['text'] for m in after['messages']] == ['selective common local-U original']
        assert still_unknown['project_id'] is None
        assert sum(p['kind'] == 'global' for p in self.cli(self.db, 'projects')) == 1
        self.save('global-cli', {'first': first, 'second': second, 'before': before, 'preview': preview,
            'applied': applied, 'actual_source_replay': replay, 'after': after, 'unknown_retained': still_unknown})
        self.save('cleanup', {'failures': [], 'scope': 'no service started; only closed task archive/source mutated'})
        self.save('result', {'status': 'passed', 'scope': 'E1 CLI unique global/explicit assignment/replay only',
            'started_at': self.started, 'finished_at': now()})


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--target-config', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); args = p.parse_args(); args.mode = 'client'; GlobalCLI(args).run()


if __name__ == '__main__': main()
