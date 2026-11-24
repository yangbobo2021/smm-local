"""Public CLI CAS/persistence tests; component interface stub is not OCR proof."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from smm_local.core import Archive
from smm_local.documents import Documents
from document_helpers import Fixture,deny_source_reads,observe
from document_formats_fixtures import docx_fixture


def invoke(side,root,args,monkeypatch,capsys):
    if side=='local':
        from smm_local.cli import main
        argv=['smm','--db',str(root/'archive.sqlite3'),'documents',*args]
    else:
        from smm_hub.cli import main
        argv=['smm-hub','hub','--state-dir',str(root),'documents',*args]
    with monkeypatch.context() as patch:
        patch.setattr(sys,'argv',argv)
        try:main();code=0
        except SystemExit as exc:code=exc.code or 0
    captured=capsys.readouterr()
    payload=json.loads(captured.out) if code==0 else None
    observe('processing-cli-'+side,{'argv':argv,'exit_code':code,'stdout':captured.out,'stderr':captured.err})
    return code,payload,captured.err


def stored(db):
    with db.connect() as con:
        row=con.execute('SELECT revision,payload FROM document_processing_config WHERE singleton=1').fetchone()
        return tuple(row)


@pytest.mark.parametrize('side',['local','hub'])
def test_processing_cli_configuration_cas_and_persistence(tmp_path,monkeypatch,capsys,side):
    # TC-008-processing-config. CLI runs in-process to stub only component calls;
    # real executable/identity/platform paths are independently required by E/H.
    root=tmp_path/side;root.mkdir();db=Archive(root/('archive.sqlite3' if side=='local' else 'smm-hub.sqlite3'))
    docs=Documents(db)
    sources=[root/'source-one.docx',root/'source-two.pdf']
    sources[0].write_bytes(docx_fixture('configready')[0]);sources[1].write_bytes(b'pending synthetic PDF must not be read')
    if side=='hub':
        from smm_hub.documents import HubDocuments
        hub=HubDocuments(db);context=hub.context()
        ready=hub.native('add',{**context,'path':str(sources[0]),'project_ids':[]})
        hub.native('refresh',context,ready['id'])
        hub.native('add',{**context,'path':str(sources[1]),'project_ids':[]})
    else:
        ready=docs.add(str(sources[0]));docs.refresh(ready['id']);docs.add(str(sources[1]))
    with db.connect() as c:
        assert {row[0] for row in c.execute('SELECT status FROM document_sources')}=={'ready','pending'}
    def source_state():
        with db.connect() as c:
            return {table:[dict(row) for row in c.execute('SELECT * FROM '+table+' ORDER BY 1,2')] for table in ['document_sources','document_source_projects','documents','document_memberships','document_meta','document_captures','document_capture_authorizations','document_processing_attempts','document_snapshot_state']}
    source_before=source_state();reads=deny_source_reads(monkeypatch,*sources)
    runtime=root/'runtime';runtime.mkdir();languages=root/'languages';languages.mkdir()
    extension='.exe' if os.name=='nt' else ''
    engine=runtime/('tesseract-fixture'+extension);alternate=runtime/('tesseract-other'+extension)
    for path in (engine,alternate):path.write_bytes(b'component-interface-test-double');path.chmod(0o700)
    (languages/'eng.traineddata').write_bytes(b'synthetic-eng')
    (languages/'chi_sim.traineddata').write_bytes(b'synthetic-chi-sim')
    calls=[];real_run=subprocess.run
    def component_run(command,*args,**kwargs):
        if Path(str(command[0])).resolve() not in {engine.resolve(),alternate.resolve()}:return real_run(command,*args,**kwargs)
        calls.append(list(map(str,command)))
        if '--version' in command:output='tesseract 5.5.4\n leptonica-1.87.0\n'
        elif '--list-langs' in command:output='List of available languages (2):\neng\nchi_sim\n'
        else:output=''
        return subprocess.CompletedProcess(command,0,output,'')
    monkeypatch.setattr(subprocess,'run',component_run)
    def success(*args):
        code,payload,error=invoke(side,root,list(args),monkeypatch,capsys)
        assert code==0,(args,code,error)
        return payload
    initial=success('processing-status')
    assert initial['config']['revision']==0
    assert Path(initial['archive'])==db.db_path.resolve()
    assert type(initial['identity']['pid']) is int and initial['identity']['pid']>0
    assert {'docx','xlsx','pdf'}.issubset(initial['formats'])
    assert initial['receive']['schema']=='processed_documents_v1'
    assert initial['ocr']['configured'] is False and initial['ocr']['ready'] is False
    assert calls==[]
    checked=success('processing-status','--check')
    assert checked['config']['revision']==0 and checked['ocr']['ready'] is False and calls==[]
    success('processing-configure','--expected-revision','0','--ocr-executable',str(engine),'--ocr-data-dir',str(languages),'--languages','eng+chi_sim')
    persisted=success('processing-status')
    assert persisted['config']['revision']==1
    assert persisted['config']['ocr_executable']==str(engine.resolve())
    assert persisted['config']['ocr_data_dir']==str(languages.resolve())
    assert persisted['config']['languages']=='eng+chi_sim'
    before=stored(db);count=len(calls)
    assert before[0]==1
    disk=json.loads(before[1])
    assert disk['ocr_executable']==str(engine.resolve()) and disk['ocr_data_dir']==str(languages.resolve()) and disk['languages']=='eng+chi_sim'
    again=success('processing-status')
    assert again['config']==persisted['config'] and len(calls)==count
    code,_,_=invoke(side,root,['processing-configure','--expected-revision','0','--ocr-executable',str(alternate),'--ocr-data-dir',str(languages),'--languages','eng+chi_sim'],monkeypatch,capsys)
    assert code!=0 and stored(db)==before
    actual_check=success('processing-status','--check')
    assert actual_check['ocr']['ready'] is True
    assert actual_check['ocr']['last_probe']['identity']['pid']==actual_check['identity']['pid']
    assert actual_check['config']==persisted['config']
    # Both language orders and both executable paths are independently valid.
    success('processing-configure','--expected-revision','1','--ocr-executable',str(alternate),'--ocr-data-dir',str(languages),'--languages','chi_sim+eng')
    persisted=success('processing-status');before=stored(db)
    assert persisted['config']['revision']==before[0]==2
    disk=json.loads(before[1])
    assert disk['ocr_executable']==persisted['config']['ocr_executable']==str(alternate.resolve())
    assert disk['ocr_data_dir']==persisted['config']['ocr_data_dir']==str(languages.resolve())
    assert disk['languages']==persisted['config']['languages']=='chi_sim+eng'
    valid=['processing-configure','--expected-revision','2','--ocr-executable',str(alternate),'--ocr-data-dir',str(languages),'--languages','chi_sim+eng']
    # Bad engine/data paths are tried while BOTH languages still exist.
    bad_inputs=[]
    for revision in ('1','3'):
        args=list(valid);args[2]=revision;bad_inputs.append(args)
    args=list(valid);args[4]=str(root/'missing-engine');bad_inputs.append(args)
    args=list(valid);args[6]=str(root/'missing-data');bad_inputs.append(args)
    for flag in ('--expected-revision','--ocr-executable','--ocr-data-dir','--languages'):
        args=list(valid);index=args.index(flag);del args[index:index+2];bad_inputs.append(args)
    for args in bad_inputs:
        code,_,_=invoke(side,root,args,monkeypatch,capsys)
        assert code!=0 and stored(db)==before
    with monkeypatch.context() as cwd_patch:
        cwd_patch.chdir(root)
        args=list(valid);args[4]=str(Path('runtime')/alternate.name)
        code,_,_=invoke(side,root,args,monkeypatch,capsys)
        assert code!=0 and stored(db)==before
        args=list(valid);args[6]='languages'
        code,_,_=invoke(side,root,args,monkeypatch,capsys)
        assert code!=0 and stored(db)==before
    (languages/'chi_sim.traineddata').unlink()
    missing=success('processing-status','--check')
    assert missing['ocr']['ready'] is False and 'chi_sim' in json.dumps(missing['ocr'],ensure_ascii=False)
    assert missing['config']==persisted['config'] and stored(db)==before
    code,_,_=invoke(side,root,valid,monkeypatch,capsys)
    assert code!=0 and stored(db)==before
    assert reads==[]
    assert source_state()==source_before, 'configuration/status must not recollect pending sources or reprocess published snapshots'
    observe('configuration-final-'+side,{'config':success('processing-status'),'component_calls':calls,'source_reads':reads})


def test_component_fixture_response_contract():
    # Verify the known stub language/version signals before using it as an oracle.
    version='tesseract 5.5.4\n leptonica-1.87.0\n';langs='List of available languages (2):\neng\nchi_sim\n'
    assert version.splitlines()[0]=='tesseract 5.5.4'
    assert set(langs.splitlines()[1:])=={'eng','chi_sim'}
