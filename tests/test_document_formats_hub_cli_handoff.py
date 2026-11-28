"""A Hub CLI collector hands saved-byte processing to its running Hub."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from document_helpers import ROOT, observe
from document_formats_handoff_observer import controls
from uuid import uuid4
from document_formats_platform import same_existing_path
from document_formats_platform import utf8_environment
from test_document_formats_management import native_input
from test_document_formats_upload_restart import Server
from test_document_formats_installed_minimum import assert_complete_source_text


def test_hub_cli_uses_running_same_archive_creator(tmp_path,monkeypatch):
    # TC-008-hub-cli-service-handoff
    controls(tmp_path/'observer-controls')
    service_workers_log=tmp_path/'service-workers.jsonl'
    nonce=uuid4().hex
    monkeypatch.setenv('SMM_008_HANDOFF_NONCE',nonce)
    monkeypatch.setenv('SMM_008_HANDOFF_AUDIT',str(service_workers_log))
    server = Server(tmp_path / 'hub', 'hub')
    (server.hooks/'sitecustomize.py').write_text('from document_formats_restart_server import install_audit\ninstall_audit()\nfrom document_formats_handoff_observer import install\ninstall()\n',encoding='utf-8')
    server.db = server.root / 'smm-hub.sqlite3'
    items = []
    for group in range(2):
        for format in ('docx', 'xlsx', 'pdf'):
            key = 'handoff' + str(group) + format
            raw, truth = native_input(format, key)
            path = tmp_path / (key + '.' + format)
            path.write_bytes(raw)
            items.append({'group': group, 'path': path, 'raw': raw, 'truth': truth})
    log = server.root / 'cli-processing.jsonl'
    env = utf8_environment(os.environ,
        PYTHONPATH=os.pathsep.join([str(server.hooks), str(ROOT / 'tests'), str(ROOT / 'src')]),
        SMM_008_RESTART_AUDIT=str(server.root/'cli-legacy-audit.jsonl'), SMM_008_RESTART_DENY='[]',SMM_008_HANDOFF_AUDIT=str(log))
    prefix = [sys.executable, '-B', '-m', 'smm_hub.cli', 'hub', '--state-dir', str(server.root)]

    def cli(*args, state=None):
        command = (prefix if state is None else [sys.executable, '-B', '-m', 'smm_hub.cli', 'hub', '--state-dir', str(state)]) + list(map(str, args))
        before=list(workers_installed(log))
        value = subprocess.run(command, cwd=server.root, env=env,
                               capture_output=True, timeout=60)
        observe('handoff-cli-command', {'argv': command, 'exit': value.returncode,
                'stdout': value.stdout.decode('utf-8'), 'stderr': value.stderr.decode('utf-8')})
        assert value.returncode == 0, value.stderr.decode('utf-8')
        installed=workers_installed(log)[len(before):]
        assert any(e['argv'][1:]==command[1:] and e['pid']!=serving_identity['pid'] for e in installed), 'CLI process did not install the observer'
        return json.loads(value.stdout)

    def workers_installed(path):
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()
                if json.loads(line).get('event')=='handoff-observer-installed'] if path.exists() else []

    def workers(path):
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()
                if json.loads(line).get('event') == 'subprocess.Popen'] if path.exists() else []

    def read(item):
        rows = server.call('GET', '/documents/files?source_id=' + item['source']['id']).json()
        assert len(rows) == 1
        entry = rows[0]
        assert entry['path'] == str(item['path']) and entry['version'] == entry['processing_version'] == 1
        assert entry['latest_attempt']['status'] == 'ready' and not entry['publication_pending']
        assert entry['published_snapshot']['sha256'] == hashlib.sha256(item['raw']).hexdigest()
        target = entry['retry_target']
        assert target['capture_id'] == entry['published_snapshot']['capture_id']
        query = item['truth']['words'][0].split()[0]
        hits = server.call('POST', '/documents/search', {**server.context, 'query': query, 'scope': 'project',
                           'project_id': item['project']['id'], 'limit': 50}).json()['results']
        assert [h['id'] for h in hits] == [entry['id']]
        reference = entry['original_reference']
        value = server.call('POST', '/documents/read', {**server.context, 'reference': reference, 'start': 0, 'end': entry['text_length']}).json()
        assert_complete_source_text(value['text'], item['truth'])
        actual = server.call('POST', '/documents/original', {**server.context, 'reference': reference}).content
        assert actual == item['raw']
        assert len(value['tables']) == len(item['truth']['tables'])
        tables = [server.call('POST', '/documents/read', {**server.context, 'reference': reference,
            'view': 'table', 'table_id': table['table_id'], 'row_start': 1, 'row_end': table['rows'] + 1,
            'column_start': 1, 'column_end': table['columns'] + 1}).json() for table in value['tables']]
        for truth in item['truth']['tables']:
            own = [t for t in tables if all(t['location'].get(k) == v for k, v in truth['location'].items())
                   and any(c['text'] == truth['cells'][0][2] for c in t['cells'])]
            assert len(own) == 1
            grid = own[0]
            assert (grid['rows'], grid['columns']) == (truth['rows'], truth['columns'])
            assert {(c['row'], c['column'], c['text'], c['row_span'], c['column_span']) for c in grid['cells']} == set(truth['cells'])
        return entry

    try:
        server.start(deny=[i['path'] for i in items])
        serving_identity=server.serving_stamp
        assert any(e['pid']==serving_identity['pid'] and e['created']==serving_identity['created']
                   for e in workers_installed(service_workers_log)), 'service process did not install the observer'
        projects = [cli('project', 'create', 'handoff ordinary'), cli('project', 'ensure-global')]
        for item in items:
            item['project'] = projects[item['group']]
            item['source'] = cli('documents', 'add', item['path'], '--project-id', item['project']['id'])
            refreshed = cli('documents', 'refresh', '--source-id', item['source']['id'])
            assert len(refreshed['sources']) == 1
            finished = refreshed['sources'][0]
            assert finished['id'] == item['source']['id'] and finished['status'] == 'ready'
            assert all(finished['counts'][k] == v for k, v in {'candidates': 1, 'ready': 1, 'failed': 0}.items())
            item['entry'] = read(item)
        first = workers(service_workers_log)
        observed_cli = workers(log)
        observe('handoff-initial-parent-identities', {'serving': server.serving_stamp,
                'service_workers': first, 'cli_workers': observed_cli})
        assert len(first) == len(items) and all(e['pid'] == server.serving_stamp['pid'] for e in first)
        assert {e['task_token'] for e in first}=={i['entry']['latest_attempt']['attempt_id'] for i in items}
        assert len({e['task_token'] for e in first})==len(first)
        assert all(e['created']==serving_identity['created'] and same_existing_path(e['exe'],serving_identity['exe'])
                   and e['parent_argv']==serving_identity['argv'] and e['nonce']==nonce for e in first)
        assert observed_cli == [], 'running Hub processing was executed in the interactive CLI'
        retried=[]
        for item in items:
            item['path'].unlink()
            target = item['entry']['retry_target']
            answer = cli('documents', 'reprocess', '--document-id', item['entry']['id'], '--capture-id', target['capture_id'],
                '--expected-attempt-id', target['expected_attempt_id'], '--expected-version', target['expected_version'],
                '--expected-processing-version', target['expected_processing_version'])
            result = read(item)
            assert answer['document_id'] == result['id']
            for field in ('processing_version', 'published_snapshot', 'latest_attempt', 'retry_target', 'publication_pending'):
                assert answer[field] == result[field]
            assert result['latest_attempt']['capture_id'] == target['capture_id']
            assert result['latest_attempt']['attempt_id'] != target['expected_attempt_id']
            retried.append(result['latest_attempt']['attempt_id'])
        assert len(workers(service_workers_log)) == 2 * len(items) and workers(log) == []
        after=workers(service_workers_log)
        assert len({e['task_token'] for e in after})==len(after)
        assert {e['task_token'] for e in after[len(first):]}==set(retried)
        assert all(e['pid']==serving_identity['pid'] and e['created']==serving_identity['created']
                   and same_existing_path(e['exe'],serving_identity['exe']) and e['nonce']==nonce for e in after)
        assert all(e.get('event') != 'open' for e in server.events())
        other = tmp_path / 'other-hub'
        other.mkdir()
        from smm_local.core import Archive
        Archive(other / 'smm-hub.sqlite3')
        project = cli('project', 'create', 'other archive', state=other)
        path = tmp_path / 'other.docx'
        raw, _ = native_input('docx', 'otherarchivehandoff')
        path.write_bytes(raw)
        source = cli('documents', 'add', path, '--project-id', project['id'], state=other)
        cli('documents', 'refresh', '--source-id', source['id'], state=other)
        assert len(workers(log)) == 1 and len(workers(service_workers_log)) == 2 * len(items)
        other_rows=cli('documents','files','--source-id',source['id'],state=other)
        assert len(other_rows)==1 and workers(log)[0]['task_token']==other_rows[0]['latest_attempt']['attempt_id']
        server.stop()
        path = tmp_path / 'foreground.docx'
        raw, truth = native_input('docx', 'foregroundhandoff')
        path.write_bytes(raw)
        source = cli('documents', 'add', path, '--project-id', projects[0]['id'])
        cli('documents', 'refresh', '--source-id', source['id'])
        assert len(workers(log)) == 2
        rows = cli('documents', 'files', '--source-id', source['id'])
        assert len(rows) == 1 and rows[0]['latest_attempt']['status'] == 'ready'
        assert workers(log)[-1]['task_token']==rows[0]['latest_attempt']['attempt_id']
        callers=workers_installed(log)
        for event in workers(log):
            assert any(e['pid']==event['pid'] and e['created']==event['created'] and same_existing_path(e['exe'],event['exe'])
                       and e['argv']==event['parent_argv'] and e['nonce']==nonce and e['probe_passed'] for e in callers)
        hits = cli('documents', 'search', truth['words'][0].split()[0], '--scope', 'project', '--project-id', projects[0]['id'], '--limit', 50)['results']
        assert [hit['id'] for hit in hits] == [rows[0]['id']]
        reference = rows[0]['original_reference']
        content = cli('documents', 'read', '--reference', reference, '--start', 0, '--end', rows[0]['text_length'])
        assert_complete_source_text(content['text'], truth)
        output = tmp_path / 'foreground-original.docx'
        metadata = cli('documents', 'read', '--reference', reference, '--original-output', output)
        assert output.read_bytes() == raw and metadata['sha256'] == hashlib.sha256(raw).hexdigest()
        tables = [cli('documents', 'read', '--reference', reference, '--view', 'table', '--table-id', t['table_id'],
            '--row-start', 1, '--row-end', t['rows'] + 1, '--column-start', 1, '--column-end', t['columns'] + 1) for t in content['tables']]
        assert len(tables) == len(truth['tables'])
        for expected in truth['tables']:
            own = [t for t in tables if all(t['location'].get(k) == v for k, v in expected['location'].items())
                   and any(c['text'] == expected['cells'][0][2] for c in t['cells'])]
            assert len(own) == 1
            assert {(c['row'], c['column'], c['text'], c['row_span'], c['column_span']) for c in own[0]['cells']} == set(expected['cells'])
    finally:
        server.stop()
