"""Pure remote originals traverse the real Local HTTP/CLI/stdio reference route."""
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from document_formats_remote_fixture import remote_world
from document_helpers import observe
from test_document_formats_mcp import assert_metadata_only
from test_document_formats_retry import keep
from test_document_formats_upload_restart import Server


def assert_remote_info(info, item, hit):
    assert info['available'] is True and info.get('reason') is None
    assert info['origin'] == hit['origin'] == item['origin']
    assert info['id'] == hit['id'] == item['hub_id']
    assert info['version'] == hit['version'] == 1
    assert info['processing_version'] == hit['processing_version'] == 1
    assert info['format'] == hit['format'] == item['format']
    assert info['sha256'] == item['sha256'] == hit['sha256']
    assert info['bytes'] == len(item['raw']) and info['archive_scope'] == 'hub'


def test_pure_hub_original_downloads_via_local_cli_http_and_stdio(tmp_path, monkeypatch):
    # TC-008-remote-original-routing
    with remote_world(tmp_path, monkeypatch) as w:
        assert len(w.items) == 24
        assert len({tuple(i['origin'].values()) for i in w.items}) == 24
        w.freeze_query_services()
        env, log, before = w.query_environment()
        seen = set()

        def download(item, hit, label):
            info = w.cli(w.reader, 'read', '--reference', hit['reference'], '--view', 'original-info', env=env)
            assert_remote_info(info, item, hit)
            output = w.root / ('download-' + label + '-' + item['key'] + '.' + item['format'])
            assert not output.exists()
            metadata = w.cli(w.reader, 'read', '--reference', hit['reference'], '--original-output', output, env=env)
            assert output.read_bytes() == item['raw']
            assert metadata['sha256'] == item['sha256'] and metadata['bytes'] == len(item['raw'])
            api_info = w.reader.call('POST', '/documents/read', {'reference': hit['reference'], 'view': 'original-info'}).json()
            assert_remote_info(api_info, item, hit)
            raw = w.reader.call('POST', '/documents/original', {'reference': hit['reference']}).content
            assert raw == item['raw']
            keep('remote/downloads/' + item['sha256'] + '.' + item['format'], raw)
            observe('remote-verified-download', {'entry': label, 'key': item['key'], 'origin': item['origin'], 'cli': metadata, 'http_sha256': hashlib.sha256(raw).hexdigest()})
            w.query_unchanged(log, before)

        for item in w.items:
            cli = w.cli(w.reader, 'search', item['query'], '--scope', 'all', '--limit', '50', env=env)
            http = w.reader.call('POST', '/documents/search', {'query': item['query'], 'scope': 'all', 'limit': 50}).json()
            for result in (cli, http):
                assert result['coverage']['hub'] == 'complete' and not result['candidate_failures']
                assert len(result['results']) == 1
                hit = result['results'][0]
                assert hit['origin'] == item['origin'] and hit['archive_scope'] == 'hub'
                download(item, hit, 'cli-search' if result is cli else 'http-search')
            item['reference'] = cli['results'][0]['reference']
            seen.add(cli['results'][0]['id'])
        assert len(seen) == 24

        async def stdio():
            params = StdioServerParameters(command=sys.executable, args=['-B', '-m', 'smm_local.mcp_server', '--db', str(w.reader.db)], env=env)
            stderr_path = w.root / 'stdio.stderr'
            try:
                with stderr_path.open('w', encoding='utf-8') as stderr:
                    async with stdio_client(params, errlog=stderr) as (reader, writer):
                        async with ClientSession(reader, writer) as session:
                            await session.initialize()
                            tools = {t.name: t for t in (await session.list_tools()).tools if 'document' in t.name}
                            assert set(tools) == {'list_document_sources', 'search_documents', 'read_document'}
                            assert all(t.annotations.readOnlyHint is True for t in tools.values())
                            assert 'original_output' not in tools['read_document'].inputSchema['properties']
                            async def call(name, body):
                                response = await session.call_tool(name, body)
                                observe('remote-stdio-call', {'tool': name, 'input': body, 'response': response.model_dump(mode='json')})
                                assert not response.isError and len(response.content) == 1 and response.content[0].type == 'text'
                                value = json.loads(response.content[0].text)
                                assert_metadata_only(value, [i['raw'] for i in w.items])
                                return value
                            mcp_seen = set()
                            for item in w.items:
                                result = await call('search_documents', {'query': item['query'], 'scope': 'all', 'limit': 50})
                                assert len(result['results']) == 1 and result['coverage']['hub'] == 'complete'
                                hit = result['results'][0]
                                info = await call('read_document', {'reference': hit['reference'], 'view': 'original-info'})
                                assert_remote_info(info, item, hit)
                                download(item, hit, 'stdio-reference')
                                mcp_seen.add(hit['id'])
                            assert mcp_seen == seen
            finally:
                if stderr_path.exists():keep('remote/stdio.stderr', stderr_path.read_bytes())
        asyncio.run(stdio())

        # A different actual Hub must not accept the old signed routing wrapper.
        wrong = Server(w.root / 'wrong-hub', 'hub')
        w.servers.append(wrong)
        wrong.start()
        assert wrong.context['hub_id'] != w.hub.context['hub_id']
        from smm_local import federation
        token = w.root / 'wrong-token';token.write_text(wrong.token, encoding='ascii')
        assert federation.configure_hub(w.reader_db, 'http://127.0.0.1:' + str(wrong.port), 'reader other hub', str(token))['connected']
        # Existing client guard allows only the original Hub. Use the new current
        # endpoint for these negative requests; no extra source/parse capability.
        wrong_env = {**env, 'SMM_008_QUERY_HUB_PORT': str(wrong.port)}
        for item in w.items:
            out = w.root / ('wrong-' + item['key'] + '.' + item['format'])
            response = w.cli(w.reader, 'read', '--reference', item['reference'], '--original-output', out, env=wrong_env, reject=True)
            assert not out.exists() and 'Hub' in response.stderr.decode('utf-8')
            response = w.reader.client.post('/api/documents/original', json={'reference': item['reference']})
            observe('remote-wrong-hub', {'key': item['key'], 'status': response.status_code, 'body': response.text})
            assert 400 <= response.status_code < 500 and 'Hub' in response.text
        w.query_unchanged(log, before)
