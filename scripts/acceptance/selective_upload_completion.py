"""Opt-in real installed-package checks for explicit 005 record gaps.

Each invocation creates fresh task archives and a loopback HTTPS Hub. No daily
archive, remote data source, registry installation, or administrator service.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import socket
import tempfile
import uuid

from selective_upload_platform import Run, now
from selective_upload_compatibility import Compatibility
from selective_upload_recovery import Recovery
from selective_upload_fixture import history


class Completion(Compatibility, Recovery):
    def old_identities(self):
        for kind, interpreter in [('local', self.old_local), ('hub', self.old_hub)]:
            code = "import importlib.util,pathlib,hashlib,json,sys;from importlib.metadata import version;r=pathlib.Path(importlib.util.find_spec('smm_'+sys.argv[1]).origin).parent.parent;print(json.dumps({'version':version('smm-'+sys.argv[1]),'files':{n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in json.loads(sys.argv[2])}}))"
            expected = self.t['old_candidate']['installed_'+kind]
            actual = json.loads(self.command([interpreter,'-I','-c',code,kind,json.dumps(list(expected))]).stdout)
            assert actual['version']=='0.4.0' and actual['files']==expected
            self.save('actual-old-'+kind,actual)

    def local_links(self, interpreter, database):
        code="import sys,json;from smm_local.core import Archive;d=Archive(sys.argv[1]);print(json.dumps({'projects':d.projects(),'cursor':dict(d.connect().execute(\"SELECT key,value FROM settings WHERE key LIKE 'hub_cursor:%'\"))}))"
        return json.loads(self.command([interpreter,'-I','-c',code,database]).stdout)

    def remote_links(self, interpreter, link=False):
        code="import sys,json;from smm_hub._archive import Archive;from smm_hub.projects import HubProjects;p=HubProjects(Archive(sys.argv[1]));ids={x['name']:x['id'] for x in p.list()};\nif sys.argv[2]=='link':p.link(ids['A'],ids['D'])\nprint(json.dumps({'projects':p.list(),'links':p.links()}))"
        return json.loads(self.command([interpreter,'-I','-c',code,self.state/'smm-hub.sqlite3','link' if link else 'read']).stdout)

    def legacy_links(self):
        self.installed(); self.old_identities()
        (self.root/'input-token').write_text(self.token)
        self.start_compat_hub(self.old_hub,self.root/'old-hub-state')
        db=self.new_archive('old-device',self.old_local)
        history(db.parent,'old-related','D',['selective compatibility related original'])
        code="import sys;from smm_local.core import Archive;d=Archive(sys.argv[1]);d.sync_codex();p={x['name']:x['id'] for x in d.projects()};d.link_projects(p['A'],p['D'])"
        self.command([self.old_local,'-I','-c',code,db])
        self.cli_at(self.old_local,db,'configure-hub',self.t['address'],'legacy-links','--token-file',self.root/'input-token')
        self.sync_at(self.old_local,db)
        local_before=self.local_links(self.old_local,db);remote_before=self.remote_links(self.old_hub,True)
        assert local_before['cursor'] and remote_before['links']
        hits=self.hub_hits();assert {h['source_session_id'] for h in hits}=={'old-device','old-related'}
        references=[{'hub_id':self.hub_id,'conversation_id':h['id'],'message_id':h['matched_messages'][0]['hub_message_id']} for h in hits]
        originals=[self.api(self.t['address'],'/v1/read',r) for r in references]
        self.save('before-upgrade',{'local':local_before,'hub':remote_before,'hits':hits,'references':references,'originals':originals})
        self.stop_hub();self.start_compat_hub(self.active_hub_python,self.root/'old-hub-state')
        upgraded=self.sync_at(self.t['local_python'],db);assert json.loads(upgraded['stdout'])['uploaded']==0
        local_after=self.local_links(self.t['local_python'],db);remote_after=self.remote_links(self.t['hub_python'])
        def local_projection(v):return {p['id']:{k:p[k] for k in ('name','linked_ids','paths')} for p in v['projects']}
        def hub_projection(v):return {p['id']:{k:p[k] for k in ('name','owner','source_key')} for p in v['projects']}
        assert local_projection(local_after)==local_projection(local_before)
        assert local_after['cursor']==local_before['cursor']
        assert hub_projection(remote_after)==hub_projection(remote_before) and remote_after['links']==remote_before['links']
        after=[self.api(self.t['address'],'/v1/read',r) for r in references]
        self.save('upgrade-read-observation',{'before':originals,'after':after,'references':references})
        expected={'old-device':[(1,'user','selective compatibility old-device original',None)],
                  'old-related':[(1,'user','selective compatibility related original',None)]}
        for reads in (originals,after):
            assert {v['source_session_id'] for v in reads}==set(expected)
            for value in reads:
                assert value['source']=='codex'
                assert [(m['position'],m['role'],m['text'],m['timestamp']) for m in value['messages']]==expected[value['source_session_id']]
        assert [v['id'] for v in after]==[v['id'] for v in originals]
        a=next(p['id'] for p in local_after['projects'] if p['name']=='A')
        query=self.cli(db,'search','selective','--scope','project','--project-id',str(a))
        assert {h['source_session_id'] for h in query['results']}=={'old-device','old-related'}
        status=self.cli(db,'upload','status');assert status['policy']['mode']=='all' and status['state']=='confirmed'
        before_repeat=self.hub_hits();self.sync_at(self.t['local_python'],db);assert self.hub_hits()==before_repeat
        self.save('after-upgrade',{'local':local_after,'hub':remote_after,'originals':after,'query':query,'status':status,'upgraded':upgraded})

    def legacy_mcp(self):
        self.installed();self.old_identities();self.setup()
        self.cli(self.db,'upload','set','--mode','none')
        hit=next(h for h in self.hub_hits() if h['source_session_id']=='vibe-V')
        remote={'conversation_id':hit['id'],'hub_id':self.hub_id,'hub_message_id':hit['matched_messages'][0]['hub_message_id']}
        local_hit=next(h for h in self.cli(self.db,'search','selective','--local')['results'] if h['source_session_id']=='local-A')
        local={'conversation_id':local_hit['id']}
        assert local['conversation_id']==remote['conversation_id'],'exercise actual same-integer collision'
        observed={};new_python=self.t['local_python']
        for version,interpreter in [('old',self.old_local),('new',new_python)]:
            self.t['local_python']=interpreter
            try:
                local_read=asyncio.run(self.mcp('read_conversation',local));remote_read=asyncio.run(self.mcp('read_conversation',remote))
            finally:self.t['local_python']=new_python
            assert [m['text'] for m in local_read['messages']]==['selective common local-A original']
            assert [m['text'] for m in remote_read['messages']]==['selective common VibeInsight original']
            assert local_read['source_session_id']=='local-A' and remote_read['source_session_id']=='vibe-V'
            observed[version]={'local':local_read,'hub':remote_read,'interpreter':interpreter}
        self.save('legacy-mcp-parameters',{'local_arguments':local,'hub_arguments':remote,'actual_stdio':observed})

    def confirmed_loss(self):
        self.initial()
        history(self.root/'local','confirmed-recent','A',['selective confirmed after backup'])
        self.cli(self.db,'maintenance','sync')
        recent=next(h for h in self.hub_hits() if h['source_session_id']=='confirmed-recent')
        original=self.api(self.t['address'],'/v1/read',{'hub_id':self.hub_id,'reference':recent['reference']})
        assert [m['text'] for m in original['messages']]==['selective confirmed after backup']
        before=self.cli(self.db,'upload','status');assert before['allowed_pending_messages']==0 and before['inflight_messages']==0
        self.stop_and_append()
        self.save('confirmed-after-backup',{'original':original,'confirmed_state':before,'stopped_state':self.cli(self.db,'upload','status')})
        prepared=self.admin('prepare-restore');assert prepared['body_stopped']
        guard=Path(str(self.state/'smm-hub.sqlite3')+'.upload-guard.json');guard_bytes=guard.read_bytes()
        self.stop_hub();self.sql_restore(self.hub_backup,self.state/'smm-hub.sqlite3');assert guard.read_bytes()==guard_bytes
        self.start_hub();self.cli(self.db,'maintenance','sync')
        conflict=self.cli(self.db,'upload','status');assert conflict['state']=='conflict'
        assert 'confirmed-recent' not in {h['source_session_id'] for h in self.hub_hits()}
        difference=self.cli(self.db,'upload','reconcile');assert difference['hub']['policy']['mode']=='none'
        adopted=self.cli(self.db,'upload','reconcile','--use','hub');assert adopted['policy']['mode']=='none'
        self.cli(self.db,'maintenance','sync');assert 'confirmed-recent' not in {h['source_session_id'] for h in self.hub_hits()}
        self.cli(self.db,'upload','set','--mode','only','--project-id',str(self.projects['A']));self.cli(self.db,'maintenance','sync')
        expected={'local-A':['selective common local-A original','selective common local-A appended while stopped'],
                  'local-A-new':['selective common local-A new while stopped'],'confirmed-recent':['selective confirmed after backup']}
        hits={h['source_session_id']:h for h in self.hub_hits()};reads={}
        for session,texts in expected.items():
            read=self.api(self.t['address'],'/v1/read',{'hub_id':self.hub_id,'reference':hits[session]['reference']})
            assert [m['text'] for m in read['messages']]==texts;reads[session]=read
        old=self.api(self.t['address'],'/v1/read',{'hub_id':self.hub_id,'reference':self.reference});assert [m['text'] for m in old['messages']]==['selective common local-A original']
        before_repeat=self.hub_hits();self.cli(self.db,'maintenance','sync');assert self.hub_hits()==before_repeat
        done=self.cli(self.db,'upload','status');assert done['allowed_pending_messages']==done['inflight_messages']==0
        self.save('confirmed-loss-recovery',{'prepare':prepared,'conflict':conflict,'difference':difference,'adopted':adopted,'reads':reads,'old_reference':old,'done':done,'expected':expected})

    def run_completion(self,probe):
        error=None
        try:getattr(self,probe.replace('-','_'))()
        except BaseException as exc:error=f'{type(exc).__name__}: {exc}';raise
        finally:
            try:self.cleanup()
            except BaseException as exc:
                if error is None:error=f'cleanup: {exc}';raise
            finally:self.save('result',{'status':'failed' if error else 'passed','failure':error,'probe':probe,'started_at':self.started,'finished_at':now(),'scope':'fresh actual installed package supplemental business; task loopback HTTPS only'})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target-config',type=Path,required=True);p.add_argument('--probe',choices=['legacy-links','legacy-mcp','confirmed-loss'],required=True);a=p.parse_args()
    base=json.loads(a.target_config.read_text());base['work']=str(Path(tempfile.gettempdir())/('smm-005-complete-'+a.probe+'-'+uuid.uuid4().hex))
    with socket.socket() as s:s.bind(('127.0.0.1',0));base['port']=s.getsockname()[1]
    base['address']='https://localhost:'+str(base['port'])
    output=Path(os.environ['ACCEPTANCE_EVIDENCE_DIR'])/'probe'
    with tempfile.TemporaryDirectory(prefix='smm-005-complete-config-') as d:
        config=Path(d)/'target.json';config.write_text(json.dumps(base));args=argparse.Namespace(target_config=config,output=output,mode='self-managed',case='R2')
        Completion(args).run_completion(a.probe)


if __name__=='__main__':main()
