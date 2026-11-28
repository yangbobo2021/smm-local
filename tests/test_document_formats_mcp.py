"""Real stdio transport preserves archived document views without source access."""
import asyncio
import base64
import copy
import pytest
import hashlib
import json
import os
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from document_helpers import Fixture, observe, fingerprint
from document_formats_fixtures import docx_fixture
from document_formats_cli_observer import install
from test_document_formats_cli import (
    assert_read_identity, assert_original_info, assert_source_headers,
    saved_state, nonzero_reference_source, keep,
)


def assert_source_cells(view, truth, index, row_start=1, row_end=None, column_start=1, column_end=None):
    source = truth['tables'][index]
    row_end = row_end if row_end is not None else max(c[0] for c in source) + 1
    column_end = column_end if column_end is not None else max(c[1] for c in source) + 1
    wanted = [c for c in source if row_start <= c[0] < row_end and column_start <= c[1] < column_end]
    cells = view['cells']
    assert len(cells) == len({(c['row'], c['column']) for c in cells}) == len(wanted)
    assert {(c['row'], c['column'], c['text'], c['row_span'], c['column_span']) for c in cells} == set(wanted)


def assert_metadata_only(value, originals):
    forbidden = [base64.b64encode(raw).decode('ascii') for raw in originals]
    def strings(node):
        if isinstance(node, str):
            yield node
        elif isinstance(node, dict):
            for key, item in node.items():
                yield from strings(key)
                yield from strings(item)
        elif isinstance(node, list):
            for item in node:
                yield from strings(item)
    assert all(encoded not in text for text in strings(value) for encoded in forbidden)


def test_mcp_source_cell_and_metadata_oracles_reject_wrong_views():
    truth = {'tables': [[(1, 1, 'HEAD1', 1, 1), (1, 2, 'HEAD2', 1, 1), (2, 1, 'BODY1', 1, 1), (2, 2, 'BODY2', 1, 1), (3, 1, 'TAIL1', 1, 1), (3, 2, 'TAIL2', 1, 1)]]}
    good = {'cells': [{'row': r, 'column': c, 'text': t, 'row_span': rs, 'column_span': cs} for r, c, t, rs, cs in truth['tables'][0]]}
    assert_source_cells(good, truth, 0)
    wrong = copy.deepcopy(good)
    wrong['cells'].append(copy.deepcopy(wrong['cells'][1]))
    with pytest.raises(AssertionError):
        assert_source_cells(wrong, truth, 0)
    with pytest.raises(AssertionError):
        assert_source_cells(good, truth, 0, row_start=2)
    with pytest.raises(AssertionError):
        assert_source_cells(good, truth, 0, row_end=3)
    with pytest.raises(AssertionError):
        assert_source_cells(good, truth, 0, column_end=2)
    raw = b'actual original bytes'
    other = b'another frozen original bytes'
    originals = [raw, other]
    assert_metadata_only({'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}, originals)
    for leaked in originals:
        with pytest.raises(AssertionError):
            assert_metadata_only({'nested': [{'raw_base64': base64.b64encode(leaked).decode()}]}, originals)


def test_stdio_mcp_document_views_preserve_snapshot_and_source_locations(tmp_path):
    # TC-008-reference-local-mcp
    f = Fixture(tmp_path / 'archive')
    project = f.project('MCP views')
    items = {}
    for key in ('mcpalpha', 'mcpbeta'):
        raw, truth = docx_fixture(key)
        if key == 'mcpalpha':
            raw = nonzero_reference_source(raw)
        path = f.file(key + '.docx', raw=raw)
        items[path.name] = {'raw': raw, 'truth': truth, 'path': path, 'before': fingerprint(path)}
        keep('inputs/' + path.name, raw)
        keep('truth/' + key + '.json', json.dumps(truth, ensure_ascii=False, default=lambda v: sorted(v) if isinstance(v, set) else str(v)).encode())
    source = f.add(f.root / 'docs', [project])
    f.refresh(source)
    for name, item in items.items():
        hits = f.search(item['truth']['key'], scope='project', project_id=project, local=True, limit=50)['results']
        own = [hit for hit in hits if Path(hit['path']).name == name]
        assert len(own) == 1
        hit = own[0]
        canonical = f.read(hit, start=0, end=hit['text_length'])
        assert all(canonical['text'].count(word) == 1 for word in item['truth']['words'])
        assert len(canonical['tables']) == len({table['table_id'] for table in canonical['tables']}) == 3
        assert {table['location']['path'] for table in canonical['tables']} == set(item['truth']['table_paths'])
        views = {table['table_id']: f.read(hit, view='table', table_id=table['table_id']) for table in canonical['tables']}
        for table_id, view in views.items():
            index = item['truth']['table_paths'].index(view['location']['path'])
            assert_source_headers(view, item['truth'], index)
        item.update(hit=hit, read=canonical, views=views)
        assert fingerprint(item['path']) == item['before']
    for item in items.values():
        item['path'].unlink()
    with f.db.connect() as con:
        archive = json.loads(con.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
    env, log = install(tmp_path, [item['path'] for item in items.values()])
    before = saved_state(f)

    async def scenario():
        params = StdioServerParameters(command=sys.executable, args=['-B', '-m', 'smm_local.mcp_server', '--db', str(f.db.db_path)], env=env)
        stderr_path = tmp_path / 'stdio.stderr'
        with stderr_path.open('w', encoding='utf-8') as stderr:
            async with stdio_client(params, errlog=stderr) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    initialized = await session.initialize()
                    observe('stdio-initialized', initialized.model_dump(mode='json'))
                    listed = await session.list_tools()
                    observe('stdio-tools', listed.model_dump(mode='json'))
                    tools = {tool.name: tool for tool in listed.tools}
                    document_tools = {name for name in tools if 'document' in name}
                    assert document_tools == {'list_document_sources', 'search_documents', 'read_document'}
                    assert all(tools[name].annotations.readOnlyHint is True for name in document_tools)

                    async def call(name, body, rejected=False):
                        response = await session.call_tool(name, body)
                        observe('stdio-call', {'name': name, 'input': body, 'response': response.model_dump(mode='json')})
                        if rejected:
                            assert response.isError is True
                            return
                        assert not response.isError
                        assert len(response.content) == 1 and response.content[0].type == 'text'
                        return json.loads(response.content[0].text)

                    seen = set()
                    for name, item in items.items():
                        hits = (await call('search_documents', {'query': item['truth']['key'], 'scope': 'project', 'project_id': project, 'local': True, 'limit': 50}))['results']
                        own = [hit for hit in hits if Path(hit['path']).name == name]
                        assert len(own) == 1
                        hit = own[0]
                        seen.add(hit['id'])
                        assert hit['id'] == item['hit']['id'] and hit['version'] == hit['processing_version'] == 1
                        if item['truth']['key'] == 'mcpalpha':
                            assert 0 < hit['start'] < hit['end'] < hit['text_length']
                        origin = {'device_id': archive, 'archive_id': archive, 'document_id': hit['id']}
                        default = await call('read_document', {'reference': hit['reference']})
                        assert_read_identity(default, item['read'], origin, source['id'])
                        assert default['start'] == hit['start'] and default['end'] == hit['end']
                        assert default['text'] == item['read']['text'][hit['start']:hit['end']]
                        assert default['start_line'] == 1 + item['read']['text'].count('\n', 0, hit['start'])
                        assert default['end_line'] == 1 + item['read']['text'].count('\n', 0, hit['end'] - 1)
                        properties = tools['read_document'].inputSchema['properties']
                        assert {'view', 'table_id', 'row_start', 'row_end', 'column_start', 'column_end'} <= set(properties)
                        assert set(properties['view']['enum']) == {'text', 'table', 'original-info'}
                        assert 'original_output' not in properties
                        full = await call('read_document', {'reference': hit['reference'], 'view': 'text', 'start': 0, 'end': hit['text_length']})
                        assert full == item['read']
                        emoji = full['text'].index('😀')
                        narrow = await call('read_document', {'reference': hit['reference'], 'view': 'text', 'start': emoji, 'end': emoji + 2})
                        assert_read_identity(narrow, item['read'], origin, source['id'])
                        assert narrow['text'] == full['text'][emoji:emoji + 2]
                        assert (narrow['start'], narrow['end']) == (emoji, emoji + 2)
                        assert narrow['start_line'] == 1 + full['text'].count('\n', 0, emoji)
                        assert narrow['end_line'] == 1 + full['text'].count('\n', 0, emoji + 1)
                        for table in full['tables']:
                            table_id = table['table_id']
                            view = await call('read_document', {'reference': hit['reference'], 'view': 'table', 'table_id': table_id})
                            assert view == item['views'][table_id]
                            index = item['truth']['table_paths'].index(view['location']['path'])
                            assert_source_cells(view, item['truth'], index)
                            assert_source_headers(view, item['truth'], index)
                            row_windows = [(1, table['rows'] + 1)]
                            if table['rows'] > 1:
                                row_windows += [(2, table['rows'] + 1), (1, table['rows'])]
                            for row_start, row_end in row_windows:
                                for column_start, column_end in ((2, 3), (1, 2)):
                                    selected = await call('read_document', {'reference': hit['reference'], 'view': 'table', 'table_id': table_id, 'row_start': row_start, 'row_end': row_end, 'column_start': column_start, 'column_end': column_end})
                                    assert_read_identity(selected, item['read'], origin, source['id'])
                                    assert selected['table_id'] == table_id
                                    for field, expected in table.items():
                                        assert selected[field] == expected
                                    assert selected['window'] == {'row_start': row_start, 'row_end': row_end, 'column_start': column_start, 'column_end': column_end}
                                    assert_source_cells(selected, item['truth'], index, row_start, row_end, column_start, column_end)
                                    assert selected['cells'] == [c for c in item['views'][table_id]['cells'] if row_start <= c['row'] < row_end and column_start <= c['column'] < column_end]
                                    assert_source_headers(selected, item['truth'], index, column_start, column_end)
                        info = await call('read_document', {'reference': hit['reference'], 'view': 'original-info'})
                        assert_original_info(info, hit, origin, source['id'], item['raw'])
                        assert_metadata_only(info, [entry['raw'] for entry in items.values()])
                        other = next(other for other_name, other in items.items() if other_name != name)
                        await call('read_document', {'reference': hit['reference'], 'view': 'table', 'table_id': other['read']['tables'][0]['table_id']}, rejected=True)
                    assert len(seen) == 2

    try:
        asyncio.run(scenario())
    finally:
        stderr_path=tmp_path/'stdio.stderr'
        if stderr_path.exists():keep('stdio/stderr.txt',stderr_path.read_bytes())
    after = saved_state(f)
    assert before == after
    assert all(not item['path'].exists() for item in items.values())
    assert not log.exists() or log.read_text(encoding='utf-8') == ''
    observe('mcp-before-after', {'before': before, 'after': after, 'source_paths_absent': True, 'events': []})
