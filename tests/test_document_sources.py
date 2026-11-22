import asyncio
import json
from pathlib import Path
import pytest
from document_helpers import Fixture, fingerprint, observe


def test_source_config(tmp_path, monkeypatch):
    f = Fixture(tmp_path); path = f.file('用户资料.md', '\ufeffneedle 中文😀\r\nsecond\n')
    original = fingerprint(path)
    from document_helpers import deny_source_reads
    deny_source_reads(monkeypatch, path)
    project = f.request('POST', '/api/projects', {'name': '  P  '})
    assert project['name'] == 'P' and project['kind'] == 'ordinary' and project['stable_key']
    other = f.request('POST', '/api/projects', {'name': 'P'})
    assert other['id'] != project['id'] and other['stable_key'] != project['stable_key']
    source = f.add(path, [project['id']])
    assert source['status'] == 'pending' and source['path'] == str(path.resolve())
    assert source['project_ids'] == [project['id']] and source['recursive'] is True and source['exclude'] == []
    assert f.files() == [] and f.search()['results'] == []
    changed = f.set(source, project_ids=[other['id']], exclude=['private/**'], recursive=False)
    assert changed['status'] == 'pending' and changed['revision'] > source['revision']
    assert changed['project_ids'] == [other['id']] and changed['exclude'] == ['private/**'] and changed['recursive'] is False
    assert f.sources() == [changed]
    reset = f.set(source)
    assert reset['project_ids'] == [] and reset['exclude'] == [] and reset['recursive'] is True
    assert f.sources() == [reset]
    directory = f.add(path.parent, [project['id']], recursive=False, exclude=['private/**'])
    directory_reset = f.set(directory)
    assert directory_reset['status'] == 'pending' and directory_reset['project_ids'] == []
    assert directory_reset['recursive'] is True and directory_reset['exclude'] == []
    assert f.files() == [] and f.search()['results'] == []
    baseline = f.sources()
    for payload in [dict(path='relative.md'), dict(path=str(tmp_path / 'absent.md')), dict(path=str(path), project_ids=[9999]),
                    dict(path=str(path), exclude=['/absolute']), dict(path=str(path), exclude=['../up']),
                    dict(path=str(path), exclude=['a\\b']), dict(path=str(path), exclude=[''])]:
        f.bad('POST', '/api/documents/sources', payload)
        assert f.sources() == baseline
    for payload in [dict(project_ids=[9999]), dict(exclude=['../escape']), dict(path=str(tmp_path))]:
        f.bad('PUT', '/api/documents/sources/' + source['id'], payload)
        assert f.sources() == baseline
    f.bad('POST', '/api/projects', {'name': '  '})
    from smm_local.core import Archive
    from smm_local.documents import Documents
    assert Documents(Archive(f.db.db_path)).sources() == baseline
    f.remove(source); f.remove(directory); assert f.sources() == []
    monkeypatch.undo()
    assert fingerprint(path) == original
    observe('source-config-expected', {'project': project, 'other': other, 'original': original, 'source': source, 'changed': changed})


def test_entrance_contract(tmp_path):
    f = Fixture(tmp_path); file = f.file('cli space 中文.txt', 'needle CLI 中文😀\nline 2\n')
    project = f.cli('project', 'create', 'CLI文档项目')
    assert project['name'] == 'CLI文档项目' and project['kind'] == 'ordinary'
    other = f.cli('project', 'create', 'Other')
    source = f.cli('documents', 'add', file, '--project-id', project['id'], '--project-id', other['id'], '--no-recursive', '--exclude', 'skip?.txt', '--exclude', '**/private/')
    stored = f.source(source)
    assert source == stored and stored['status'] == 'pending'
    assert set(stored['project_ids']) == {project['id'], other['id']} and stored['recursive'] is False
    assert stored['exclude'] == ['skip?.txt', '**/private/']
    changed = f.cli('documents', 'set', source['id'], '--project-id', project['id'], '--exclude', 'else/**')
    assert f.source(source) == changed and changed['project_ids'] == [project['id']]
    assert changed['recursive'] is True and changed['exclude'] == ['else/**'] and changed['status'] == 'pending'
    cleared=f.cli('documents','set',source['id'])
    assert f.source(source)==cleared and cleared['project_ids']==[] and cleared['exclude']==[] and cleared['recursive'] is True
    assert cleared['status']=='pending' and cleared['revision']>changed['revision']
    f.cli('documents','set',source['id'],'--project-id',project['id'])
    f.cli('documents', 'refresh', '--source-id', source['id'])
    assert f.source(source)['status'] == 'ready'
    result = f.cli('documents', 'search', 'needle', '--scope', 'project', '--project-id', project['id'])
    assert len(result['results']) == 1 and result['results'][0]['path'] == str(file.resolve())
    read = f.cli('documents', 'read', '--reference', result['results'][0]['reference'])
    assert read['text'] == 'needle CLI 中文😀\nline 2\n'
    invalid = f.cli('documents', 'add', 'relative.txt', code=2); assert invalid.stderr
    from smm_local.mcp_server import create_mcp
    tools = {x.name: x for x in asyncio.run(create_mcp(f.db).list_tools())}
    for name in ['list_document_sources', 'search_documents', 'read_document']:
        assert tools[name].annotations.readOnlyHint is True
    assert {'search_conversations','read_conversation','list_projects','manage_sync'} <= tools.keys()
    from document_helpers import ROOT
    import subprocess,sys
    helps = {}
    for args in [[], ['documents'], ['documents','add'], ['documents','set'], ['documents','search'], ['documents','read'], ['project','create']]:
        p = subprocess.run([sys.executable,'-m','smm_local.cli',*args,'--help'],capture_output=True,text=True,encoding='utf-8',cwd=ROOT)
        assert p.returncode == 0; helps[' '.join(args)] = p.stdout
    assert 'documents' in helps[''] and 'project-id' in helps['documents add'] and 'refresh' in helps['documents add']
    assert 'reference' in helps['documents read'] and 'Unicode' in helps['documents read']
    observe('new-help',helps)
