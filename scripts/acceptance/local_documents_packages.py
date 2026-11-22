"""Opt-in installed Local/Hub wheel check for 006, with only fresh synthetic state."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--uv',required=True);p.add_argument('--output',type=Path)
    a=p.parse_args();out=a.output or Path(os.environ['ACCEPTANCE_EVIDENCE_DIR']);out.mkdir(parents=True,exist_ok=True)
    commands=[]
    def save(name,value): (out/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def run(args,code=0):
        actual=subprocess.run(list(map(str,args)),capture_output=True,text=True,encoding='utf-8',cwd=ROOT,timeout=180)
        commands.append({'argv':list(map(str,args)),'exit_code':actual.returncode,'stdout':actual.stdout,'stderr':actual.stderr});save('commands',commands)
        assert actual.returncode==code,actual.stderr
        return actual.stdout
    with tempfile.TemporaryDirectory(prefix='smm-006-packages-') as tmp:
        t=Path(tmp);wheels=t/'wheels'
        run([sys.executable,ROOT/'scripts/build_packages.py','--uv',a.uv,'--out-dir',wheels])
        installed={};wheel_meta={}
        for kind in ['local','hub']:
            wheel=next(wheels.glob('smm_'+kind+'-*.whl'));env=t/kind
            run([a.uv,'venv','--python',sys.executable,env]);python=env/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
            run([a.uv,'pip','install','--offline','--link-mode','copy','--python',python,wheel])
            with zipfile.ZipFile(wheel) as z:
                expected={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('smm_'+kind+'/') and n.endswith(('.py','.html'))}
                assert not any(n.endswith(('.sqlite3','.jsonl','.pem','.key')) for n in z.namelist())
            source={str(p.relative_to(ROOT/'src')).replace(os.sep,'/'):hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (ROOT/'src'/('smm_'+kind)).rglob('*') if p.suffix in ['.py','.html'] and '__pycache__' not in p.parts}
            if kind=='hub':
                shim=source.pop('smm_hub/_archive.py')
                source['smm_hub/_archive/__init__.py']=hashlib.sha256((ROOT/'src/smm_hub/_archive.py').read_text(encoding='utf-8').replace('from smm_local.','from .').encode()).hexdigest()
                for p in [*(ROOT/'src/smm_local'/name for name in ['core.py','support.py','archive_protocol.py','references.py']),*(ROOT/'src/smm_local/importers').rglob('*.py')]:
                    source['smm_hub/_archive/'+p.relative_to(ROOT/'src/smm_local').as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
            assert expected==source,{'source':source,'wheel':expected}
            save(kind+'-source-wheel',{'source':source,'wheel':expected})
            inspect="import importlib.util,pathlib,hashlib,json,sys;r=pathlib.Path(importlib.util.find_spec('smm_'+sys.argv[1]).origin).parent.parent;print(json.dumps({n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in json.loads(sys.argv[2])}))"
            actual=json.loads(run([python,'-I','-B','-c',inspect,kind,json.dumps(list(expected))]));assert actual==expected
            installed[kind]={'python':str(python),'modules':actual};wheel_meta[kind]={'wheel':wheel.name,'sha256':hashlib.sha256(wheel.read_bytes()).hexdigest()}
        local=installed['local']['python'];db=t/'local.sqlite3';path=t/'输入 文档.txt';path.write_bytes('needle package 中文😀\r\n'.encode())
        def cli(*args):return json.loads(run([local,'-I','-B','-m','smm_local.cli','--db',db,*args]))
        # On the pre-implementation baseline this completes with an actual missing CLI command.
        help_text=run([local,'-I','-B','-m','smm_local.cli','documents','--help']);assert 'refresh' in help_text
        project=cli('project','create','package project');source=cli('documents','add',path,'--project-id',project['id'])
        assert source['status']=='pending';cli('documents','refresh','--source-id',source['id'])
        hit=cli('documents','search','needle')['results'][0];read=cli('documents','read','--reference',hit['reference'])
        assert read['text']=='needle package 中文😀\n'
        hub=installed['hub']['python'];check="import importlib.util,json,sys;assert importlib.util.find_spec('smm_local') is None;from smm_hub._archive import Archive;d=Archive(sys.argv[1]);a=d.create_project('standalone-A');b=d.create_project('standalone-B');d.merge_projects(a['id'],b['id']);assert [p['name'] for p in d.projects()]==['standalone-B'];print(json.dumps({'independent':True,'projects':d.projects()}))"
        hub_result=json.loads(run([hub,'-I','-B','-c',check,t/'hub.sqlite3']))
        run([hub,'-I','-B','-m','smm_hub.cli','serve-hub','--help'])
        assert 'smm_local/documents.py' in installed['local']['modules']
        assert not any('/documents.py' in n for n in installed['hub']['modules'])
        save('package-result',{'status':'passed','wheels':wheel_meta,'installed':installed,'local_read':read,'hub':hub_result,'scope':'actual build and separate installations; fresh state only; no service or user archive'})
        print(json.dumps({'status':'passed','local_modules':len(installed['local']['modules']),'hub_modules':len(installed['hub']['modules'])}))


if __name__=='__main__':main()
