"""Build, independently install and exercise both 007 distributions.

No imports from a source checkout are used in either product subprocess.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[2]


def sha(raw):return hashlib.sha256(raw).hexdigest()


def verify(output,uv):
    output.mkdir(parents=True,exist_ok=False);records=[]
    env=dict(os.environ,PYTHONUTF8='1');env.pop('PYTHONPATH',None);env.pop('VIRTUAL_ENV',None)
    def run(label,argv,cwd=None):
        result=subprocess.run(list(map(str,argv)),cwd=cwd or output,env=env,capture_output=True,timeout=120)
        (output/(label+'.stdout')).write_bytes(result.stdout);(output/(label+'.stderr')).write_bytes(result.stderr)
        records.append({'label':label,'argv':list(map(str,argv)),'exit_code':result.returncode,'stdout_sha256':sha(result.stdout),'stderr_sha256':sha(result.stderr)})
        (output/'commands.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        assert result.returncode==0,(label,result.returncode,result.stderr.decode('utf-8',errors='replace'))
        return result.stdout
    wheels=output/'wheels';run('build',[sys.executable,ROOT/'scripts/build_packages.py','--uv',uv,'--out-dir',wheels])
    whls=list(wheels.glob('*.whl'));assert len(whls)==2
    expected={}
    for role in ['local','hub']:
        wheel=next(w for w in whls if w.name.startswith('smm_'+role+'-'));prefix='smm_'+role+'/'
        mapping={}
        for file in (ROOT/'src'/('smm_'+role)).rglob('*'):
            if not file.is_file() or file.suffix not in {'.py','.html'} or '__pycache__' in file.parts:continue
            if role=='hub' and file.name=='_archive.py':continue
            mapping[file.relative_to(ROOT/'src').as_posix()]=file.read_bytes()
        if role=='hub':
            shim=(ROOT/'src/smm_hub/_archive.py').read_text().replace('from smm_local.','from .').encode()
            mapping['smm_hub/_archive/__init__.py']=shim
            pure=['core.py','support.py','archive_protocol.py','references.py','documents.py','document_protocol.py','managed_documents.py']
            for name in pure:
                path=ROOT/'src/smm_local'/name
                assert path.is_file(),('missing shared product module',name)
                mapping['smm_hub/_archive/'+name]=path.read_bytes()
            for file in (ROOT/'src/smm_local/importers').rglob('*.py'):
                if '__pycache__' not in file.parts:mapping['smm_hub/_archive/importers/'+str(file.relative_to(ROOT/'src/smm_local/importers')).replace(os.sep,'/')]=file.read_bytes()
        with ZipFile(wheel) as z:
            members={name for name in z.namelist() if name.endswith(('.py','.html'))}
            assert members==set(mapping),('complete package module set',role,sorted(members-set(mapping)),sorted(set(mapping)-members))
            assert role!='hub' or 'smm_hub/static/index.html' in members,'Hub must package its actual browser entry'
            for name,content in mapping.items():assert z.read(name)==content,(role,name)
        expected[role]={name:sha(content) for name,content in mapping.items()}
        venv=output/(role+'-env');run(role+'-venv',[uv,'venv','--python',sys.executable,venv])
        python=venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        run(role+'-install',[uv,'pip','install','--python',python,wheel])
        manifest=output/(role+'-expected.json');manifest.write_text(json.dumps(expected[role],sort_keys=True)+'\n')
        code="""import hashlib,importlib.util,json,pathlib,sys
mapping=json.loads(pathlib.Path(sys.argv[1]).read_text());role=sys.argv[2]
module=importlib.util.find_spec('smm_'+role);root=pathlib.Path(module.origin).parent.parent
for name,expected in mapping.items():
 p=root/name;assert p.is_file(),name;assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,name
if role=='hub':assert importlib.util.find_spec('smm_local') is None,'Hub installation depends on Local'
print(json.dumps({'role':role,'python':sys.executable,'site_root':str(root),'module_sha256':mapping,'hub_has_no_local':role=='hub'},ensure_ascii=False))
"""
        run(role+'-installed-modules',[python,'-I','-c',code,manifest,role])
        state=output/(role+'-state');state.mkdir();source=state/'source 中文.txt';text='packageprobe '+role+'😀\nindependent '+role;source.write_text(text,encoding='utf-8')
        if role=='local':base=[python,'-I','-m','smm_local.cli','--db',state/'local.sqlite3'];project_args=['project','create','Package P'];docbase=['documents']
        else:base=[python,'-I','-m','smm_hub.cli'];project_args=['hub','--state-dir',state,'project','create','Package P'];docbase=['hub','--state-dir',state,'documents']
        project=json.loads(run(role+'-project-create',base+project_args))
        added=json.loads(run(role+'-document-add',base+docbase+['add',source,'--project-id',str(project['id'])]));assert added['status']=='pending'
        run(role+'-document-refresh',base+docbase+['refresh','--source-id',added['id']])
        searchargs=['search','packageprobe','--scope','project','--project-id',str(project['id'])]+(['--local'] if role=='local' else [])
        result=json.loads(run(role+'-document-search',base+docbase+searchargs));assert len(result['results'])==1,result
        hit=result['results'][0];read=json.loads(run(role+'-document-read',base+docbase+['read','--reference',hit['reference']]))
        assert read['text']==text and hit['version']==1,(role,read)
        if role=='local':
            code="""import asyncio,json,sys
from smm_local.core import Archive
from smm_local.mcp_server import create_mcp
names=[t.name for t in asyncio.run(create_mcp(Archive(sys.argv[1])).list_tools())]
assert set(n for n in names if 'document' in n)=={'list_document_sources','search_documents','read_document'}
print(json.dumps(names))
"""
            # Give the isolated MCP its own empty state, never default user archive.
            run('local-mcp-tools',[python,'-I','-c',code,state/'mcp.sqlite3'])
    result={'status':'passed','wheels':{w.name:sha(w.read_bytes()) for w in whls},'source_wheel_install_sha256':expected,'commands':records}
    (output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--uv',default='uv');args=p.parse_args()
    result=verify(args.output,args.uv);print(json.dumps({'status':result['status'],'commands':len(result['commands']),'output':str(args.output)},ensure_ascii=False))
