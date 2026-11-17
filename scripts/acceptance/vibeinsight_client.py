# SPDX-License-Identifier: Apache-2.0
"""Two-phase native CLI/stdio MCP probe; the Hub CLI configures links between phases."""
import asyncio
import json
import os
from pathlib import Path
import select
import socket
import socketserver
import ssl
import subprocess
import sys
import threading
import uuid
from urllib.parse import urlsplit

from vibeinsight_platform import Run


class Relay(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True


class Forward(socketserver.BaseRequestHandler):
    def handle(self):
        if self.server.offline: return
        try:
            with socket.create_connection(self.server.destination,timeout=5) as upstream:
                peers=(self.request,upstream)
                while True:
                    ready,_,_=select.select(peers,[],[],10)
                    if not ready: return
                    for source in ready:
                        data=source.recv(65536)
                        if not data:return
                        (upstream if source is self.request else self.request).sendall(data)
        except OSError:return


def make_history(directory, session, cwd, text):
    directory.mkdir(parents=True,exist_ok=True); cwd.mkdir(parents=True,exist_ok=True)
    lines=[{'type':'session_meta','payload':{'id':session,'cwd':str(cwd)}},
           {'type':'response_item','ordinal':1,'payload':{'type':'message','id':session+'-message',
              'role':'user','content':[{'type':'input_text','text':text}]}}]
    (directory/(session+'.jsonl')).write_text(''.join(json.dumps(row)+'\n' for row in lines),encoding='utf-8')


def client_main(args):
    target=json.loads(args.target_config.read_text(encoding='utf-8-sig'))
    os.environ['SSL_CERT_FILE']=target['cert']
    from smm_local.core import Archive
    from smm_local.federation import hub_config,push_pending
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client

    run=Run(args); t=run.target
    if os.name=='nt':
        import ctypes
        run.save('client-identity',{'kind':'Windows user process','elevated_admin':bool(ctypes.windll.shell32.IsUserAnAdmin())})
    else:
        run.save('client-identity',{'uid':os.getuid(),'elevated_root':os.geteuid()==0})
    main_root=run.root/t.get('client_data_name','client-data'); main_root.mkdir(exist_ok=True)
    db_path=main_root/'archive.sqlite3'
    name=t['client_name']; session='device-'+name
    saved_file=main_root/'prepared.json'
    expected_main='platform evidence '+session
    history=main_root/'sessions'
    working=main_root/'work'/'duplicate name'
    other=main_root/'work'/'other'
    related=main_root/'work'/'local-related'
    run.env['SSL_CERT_FILE']=str(t['cert'])
    result={}
    relay=None
    try:
        # Verify the Local package bytes too, independent of Hub installation.
        code="import importlib.util,hashlib,json,pathlib,sys; r=pathlib.Path(importlib.util.find_spec('smm_local').origin).parent.parent; print(json.dumps({n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in json.loads(sys.argv[1])}))"
        actual=json.loads(run.command([t['local_python'],'-c',code,json.dumps(list(t['candidate']['installed_local']))]).stdout)
        assert actual==t['candidate']['installed_local']
        run.save('installed-local',actual)
        if t.get('phase')=='prepare':
            assert not saved_file.exists() and (not db_path.exists() or t.get('resume_prepare'))
            for label,cwd in [(session,working),('other-'+name,other),('related-'+name,related)]:
                make_history(history,label,cwd,'platform evidence '+label)
            (history/'empty').mkdir(exist_ok=True)
            # Generate/upload with the real old source, then upgrade the same archive without a new message.
            legacy="""
import json,sys
from smm_local.core import Archive
from smm_local.federation import configure_hub,push_pending,search_archive
path,history,address,name,token=sys.argv[1:]
db=Archive(path); db.set_settings(codex_root=history,claude_root=history+'/empty',sync_paused=False)
db.sync_codex(); result=configure_hub(db,address,name,token); assert result['connected'],result
push_pending(db)
print(json.dumps(search_archive(db,'platform',scope='all',limit=50)))
"""
            env=dict(run.env,PYTHONPATH=t['baseline_src'])
            old=json.loads(run.command([t['local_python'],'-c',legacy,str(db_path),str(history),t['address'],
                                       name,t['hub_token_file']],env=env).stdout)
            run.save('C6-before-metadata',old)
            hit=next(h for h in old['results'] if h['source_session_id']==session)
            old_message=next(m for m in hit['matched_messages'] if m['text']==expected_main)
            old_ref={'conversation_id':hit['id'],'hub_id':old['hub_id'],'hub_message_id':old_message['hub_message_id']}
            db=Archive(db_path)
            count_before=sum(len(db.read(h['id'])['messages']) for h in db.search('platform',limit=50)['results'])
            push_pending(db)
            main_id=db.resolve_project(str(working))['id']; related_id=db.resolve_project(str(related))['id']
            db.link_projects(main_id,related_id)
            assert sum(len(db.read(h['id'])['messages']) for h in db.search('platform',limit=50)['results'])==count_before
            prepared={'main_id':main_id,'related_id':related_id,'device_id':hub_config(db)['device_id'],
                      'session':session,'old_reference':old_ref,'expected_main':expected_main,'message_count':count_before}
            saved_file.write_text(json.dumps(prepared,indent=2),encoding='utf-8')
            run.save('C6-prepared',prepared)
            run.finish('prepared')
            return
        prepared=json.loads(saved_file.read_text(encoding='utf-8')); db=Archive(db_path)
        expected_ids=set(t['expected_projects'])
        destination=urlsplit(t['address'])
        relay=Relay(('127.0.0.1',0),Forward); relay.offline=False
        relay.destination=(destination.hostname,destination.port or 443)
        thread=threading.Thread(target=relay.serve_forever,daemon=True);thread.start()
        profile=db_path.with_suffix(db_path.suffix+'.hub.json')
        original=profile.read_bytes(); cfg=json.loads(original)
        cfg['address']=f'https://127.0.0.1:{relay.server_address[1]}'
        profile.write_text(json.dumps(cfg),encoding='utf-8')

        def cli(*parts):
            return json.loads(run.command([t['local_python'],'-m','smm_local.cli','--db',str(db_path),*map(str,parts)]).stdout)

        def assert_project(data):
            assert data['archive_scope']=='hub' and data['scope']=='project'
            assert {p['id'] for p in data['effective_projects']}==expected_ids
            assert {p['id'] for h in data['results'] for p in h['projects']}==expected_ids
            for expected in t['expected_hits']:
                assert any(h['source']==expected['source'] and h['source_session_id']==expected['session']
                           and any(p['id']==expected['project_id'] for p in h['projects'])
                           and any(m.get('text') in expected['texts'] for m in h['matched_messages']) for h in data['results'])
            assert any(h['source_session_id']==session for h in data['results'])
            assert any(h['source']=='vibeinsight' for h in data['results'])

        def assert_offline(data):
            assert data['archive_scope']=='local' and data['scope']=='all' and data['fallback_reason']
            assert {h['source_session_id'] for h in data['results']}=={session,'other-'+name,'related-'+name}

        def assert_local(data):
            assert data['archive_scope']=='local'
            assert {h['source_session_id'] for h in data['results']}=={session,'related-'+name}

        async def verify():
            params=StdioServerParameters(command=t['local_python'],args=[str(Path(__file__).with_name('vibeinsight_mcp_process.py')),str(run.output/'mcp-process.json'),str(db_path)],env=run.env)
            async with stdio_client(params) as (reader,writer):
                async with ClientSession(reader,writer) as mcp:
                    await mcp.initialize()
                    tools=await mcp.list_tools()
                    schemas={item.name:item.inputSchema for item in tools.tools}
                    assert {'scope','project_id','local'} <= schemas['search_conversations']['properties'].keys()
                    assert {'hub_id','hub_message_id','conversation_id'} <= schemas['read_conversation']['properties'].keys()
                    run.save('C5-mcp-tool-schemas',schemas)
                    async def tool(label,toolname,arguments):
                        reply=await mcp.call_tool(toolname,arguments)
                        assert not reply.isError
                        data=json.loads(reply.content[0].text)
                        run.save(label,{'tool':toolname,'arguments':arguments,'response':data})
                        return data
                    resolved=await tool('C1-resolve','resolve_project',{'cwd':str(working)})
                    assert resolved['id']==prepared['main_id']
                    query={'query':'platform','scope':'project','project_id':prepared['main_id'],'limit':50}
                    old_scope=cli('search','platform','--scope','project','--project-id',prepared['main_id'],'--limit',50)
                    old_name=next(p['name'] for p in old_scope['effective_projects'] if p['id']==t['expected_projects'][0])
                    renamed='renamed-'+name+'-'+uuid.uuid4().hex[:8]
                    assert renamed!=old_name
                    for label in ('initial','recovered','renamed'):
                        if label=='recovered':relay.offline=False
                        if label=='renamed':
                            db.rename_project(prepared['main_id'],renamed); push_pending(db)
                        scoped=cli('search','platform','--scope','project','--project-id',prepared['main_id'],'--limit',50)
                        assert_project(scoped); run.save('C1-cli-'+label,scoped)
                        via=await tool('C1-mcp-'+label,'search_conversations',query)
                        assert_project(via)
                        if label=='renamed':
                            for data in (scoped,via):
                                current=next(p for p in data['effective_projects'] if p['id']==t['expected_projects'][0])
                                assert current['name']==renamed and current['name']!=old_name
                            run.save('C6-display-name-change',{'before':old_name,'after':renamed,'stable_local_id':prepared['main_id'],'stable_hub_id':t['expected_projects'][0]})
                        if label!='initial':continue
                        global_cli=cli('search','platform','--scope','all','--limit',50)
                        global_mcp=await tool('C2-global-mcp','search_conversations',{'query':'platform','scope':'all','limit':50})
                        run.save('C2-global-cli',global_cli)
                        for data in (global_cli,global_mcp):
                            assert {'codex','vibeinsight'} <= {h['source'] for h in data['results']}
                            assert all(h['projects'] and h['source_session_id'] and h['matched_messages'] for h in data['results'])
                        for entry,data in [('cli',global_cli),('mcp',global_mcp)]:
                            for source in ('codex','vibeinsight'):
                                hit=next(h for h in data['results'] if (h['source_session_id']==session if source=='codex' else h['source']=='vibeinsight' and h['source_session_id']=='turns'))
                                message=hit['matched_messages'][0]
                                ref={'conversation_id':hit['id'],'hub_id':data['hub_id'],'hub_message_id':message['hub_message_id']}
                                if entry=='cli':
                                    read=cli('read',hit['id'],'--hub-id',data['hub_id'],'--hub-message-id',message['hub_message_id'])
                                    run.save('C2-read-cli-'+source,read)
                                else:read=await tool('C2-read-mcp-'+source,'read_conversation',ref)
                                expected=expected_main if source=='codex' else f"platform evidence C turns {message['position']-1}"
                                assert len(read['messages'])==1
                                assert read['messages'][0]['text']==expected
                                assert read['messages'][0]['role']==('user' if source=='codex' or (message['position']-1)%2==0 else 'assistant')
                                assert read['source']==source and read['source_session_id']==(session if source=='codex' else 'turns')
                                assert read['messages'][0]['hub_message_id']==message['hub_message_id']
                                origins=read['messages'][0]['origins']
                                if source=='codex':
                                    assert any(o['device_id']==prepared['device_id'] and o['device_name']==name and o['source_position']==1 and o['project_id']==t['expected_projects'][0] for o in origins)
                                else:
                                    assert any(o['source']=='vibeinsight' and o['platform']=='codex' and o['source_position']==message['position'] and o['source_event_id']==f"E{message['position']-1:06d}" for o in origins)
                                    assert any(p['source_key']=='git.example:0/team/C' for p in read['projects'])
                        old=prepared['old_reference']
                        old_cli=cli('read',old['conversation_id'],'--hub-id',old['hub_id'],'--hub-message-id',old['hub_message_id'])
                        old_mcp=await tool('C2-old-reference-mcp','read_conversation',old)
                        assert old_cli['messages'][0]['text']==expected_main and old_mcp['messages'][0]['text']==expected_main
                        run.save('C2-old-reference-cli',old_cli)
                        local_cli=cli('search','platform','--local','--scope','project','--project-id',prepared['main_id'],'--limit',50)
                        assert_local(local_cli);run.save('C4-local-cli',local_cli)
                        assert_local(await tool('C4-local-mcp','search_conversations',{**query,'local':True}))
                        relay.offline=True
                        off=cli('search','platform','--scope','project','--project-id',prepared['main_id'],'--limit',50)
                        assert_offline(off);run.save('C3-offline-cli',off)
                        assert_offline(await tool('C3-offline-mcp','search_conversations',query))
        try:
            asyncio.run(verify())
            process=json.loads((run.output/'mcp-process.json').read_text(encoding='utf-8'))
            assert process['exit_code']==0
            run.save('C5-mcp-process',process)
            run.command([t['local_python'],'-m','smm_local.cli','search','--help'])
            run.command([t['local_python'],'-m','smm_local.mcp_server','--help'])
            assert len(db.search('platform',limit=50)['results'])==3
            run.finish('passed')
        finally:profile.write_bytes(original)
    except BaseException as exc:
        run.finish('failed',type(exc).__name__+': '+str(exc));raise
    finally:
        if relay:relay.shutdown();relay.server_close()
