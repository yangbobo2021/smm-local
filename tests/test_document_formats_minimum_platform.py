"""Three-platform Python3.11 installed-wheel acceptance; never source product subprocesses.

Fork of the original Mac-only fixture driver, preserving its source/table oracles.
Native identity is independently measured on the actual platform.
"""
import hashlib,json,os,re,sqlite3,subprocess,sys
from pathlib import Path
from zipfile import ZipFile
import pytest
from document_helpers import observe
from document_formats_fixtures import docx_fixture
from test_document_formats_management import native_input
from test_document_formats_retry import ENGINE,DATA,FONT,scan_pdf,keep

CONFIG=os.environ.get('SMM_008_MINIMUM_INSTALLED_CONFIG')
pytestmark=pytest.mark.skipif(not CONFIG or not all((ENGINE,DATA,FONT)),reason='requires explicit isolated installed Python3.11 wheels and local OCR assets')


IDENTITY_CODE="""import hashlib,importlib,importlib.util,json,os,platform,sys
from pathlib import Path
owner=sys.argv[1];root=Path(importlib.import_module('smm_'+owner).__file__).resolve().parent.parent
if 'site-packages' not in str(root) or 'src/smm_' in str(root):raise SystemExit('source package is not an installed origin')
expected=json.loads(Path(sys.argv[2]).read_text());actual={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in expected}
if actual!=expected:raise SystemExit('installed package bytes differ from wheel')
assert sys.version_info[:2]==(3,11)
assert 'site-packages' in str(root) and 'src/smm_' not in str(root)
assert platform.system()==sys.argv[3]
if os.name=='nt':
 import ctypes,csv,io,subprocess
 assert not ctypes.windll.shell32.IsUserAnAdmin()
 rows=list(csv.reader(io.StringIO(subprocess.check_output(['whoami.exe','/user','/fo','csv','/nh'],text=True,encoding='utf-8'))))
 sid=rows[-1][1];assert sid.startswith('S-1-5-21-')
 groups=subprocess.check_output(['whoami.exe','/groups','/fo','csv','/nh'],text=True,encoding='utf-8');assert 'S-1-5-32-544' not in groups
 actor={'sid':sid,'administrator_group':False}
else:
 assert os.getuid()!=0
 actor={'uid':os.getuid()}
if owner=='hub':assert importlib.util.find_spec('smm_local') is None
print(json.dumps({'python':sys.version,'executable':sys.executable,'prefix':sys.prefix,'actor':actor,'os':platform.platform(),'system':platform.system(),'package_root':str(root),'files':actual,'hub_cannot_import_local':owner=='hub','isolated':sys.flags.isolated}))
"""

def assert_complete_source_text(text,truth,ocr=False):
    if ocr:
        assert re.sub(r'\s+','',text)==re.sub(r'\s+','','\n'.join(truth['words']))
        return
    # Preserve actual source text units once. Their separators are not a new
    # format contract; only source orders explicitly defined by B2 are checked.
    remainder=text
    for unit in sorted(truth['words'],key=len,reverse=True):
        assert text.count(unit)==1,unit
        remainder=remainder.replace(unit,'',1)
    # Table/part layout may add punctuation or separators, not new words/numbers.
    assert not re.search(r'[^\W_]',remainder),remainder
    for group in truth.get('ordered_groups',[]):
        positions=[text.index(unit) for unit in group]
        assert positions==sorted(positions),group


def test_complete_text_oracle_accepts_layouts_and_rejects_wrong_content():
    truth={'words':['ALPHA','BETA','HEADER'],'ordered_groups':[['ALPHA','BETA']]}
    for correct in ('ALPHA\nBETA\nHEADER','HEADER\nALPHA\tBETA','ALPHA   BETA\r\nHEADER','| HEADER | ALPHA | BETA |'):
        assert_complete_source_text(correct,truth)
    # DOCX parts may move relative to one another; explicit body order stays.
    for wrong in ('BETA\nALPHA\nHEADER','ALPHA\nBETA\nBETA\nHEADER','ALPHA\nHEADER','ALPHA\nINJECTED\nBETA\nHEADER'):
        with pytest.raises(AssertionError):assert_complete_source_text(wrong,truth)
    # XLSX's flat text layout is not its grid; cell/sheet structure is separately
    # checked against every source table, so flat row/column separators may vary.
    unordered={'words':['ALPHA','BETA']}
    assert_complete_source_text('BETA\tALPHA',unordered)
    ocr={'words':['ALPHA','BETA']}
    assert_complete_source_text(' ALPHA \r\n  BETA ',ocr,True)
    for wrong in ('BETA\nALPHA','ALPHA\nBETA\nBETA','ALPHA','ALPHA\nINJECTED\nBETA'):
        with pytest.raises(AssertionError):assert_complete_source_text(wrong,ocr,True)
    observe('minimum-installed-fulltext-known-controls',{'legal_native_separator_variants':4,'independent_part_placement_allowed':True,'xlsx_flat_layout_not_grid_order':True,'ocr_only_whitespace_tolerated':True,'wrong_source_order_duplicate_missing_extra_rejected':8})


def source_tables_match(table,truth):
    cells=[(c['row'],c['column'],c['text'],c['row_span'],c['column_span']) for c in table['cells']]
    return (table['rows'],table['columns'])==(truth['rows'],truth['columns']) and len(cells)==len(truth['cells']) and set(cells)==set(truth['cells'])


def test_installed_wheel_manifest_and_driver_source_are_separate(tmp_path):
    # Fixture prerequisites; actual source/hash rejection controls run in each business case.
    root=Path(__file__).resolve().parents[1]
    assert (root/'src/smm_local').is_dir() and (root/'src/smm_hub').is_dir()
    config=json.loads(Path(CONFIG).read_text())
    for owner in ('local','hub'):
        wheel=Path(config[owner]['wheel'])
        assert hashlib.sha256(wheel.read_bytes()).hexdigest()==config[owner]['wheel_sha256']
        with ZipFile(wheel) as z:
            assert z.testzip() is None
            assert any(n.startswith('smm_'+owner+'/') for n in z.namelist())
            if owner=='hub':assert not any(n.startswith('smm_local/') for n in z.namelist())
    observe('minimum-installed-source-probe-control',{'source_driver_is_source':True,'distinct_wheel_packages':True,'hub_has_no_local_package':True})



def test_installed_source_table_oracle_rejects_wrong_members():
    from copy import deepcopy
    truth={'rows':1,'columns':2,'cells':[(1,1,'alpha',1,1),(1,2,'beta',1,1)]}
    good={'rows':1,'columns':2,'cells':[{'row':r,'column':c,'text':t,'row_span':rs,'column_span':cs} for r,c,t,rs,cs in truth['cells']]}
    assert source_tables_match(good,truth)
    bads=[]
    for key,value in [('row',2),('column',2),('text','other'),('row_span',2),('column_span',2)]:
        bad=deepcopy(good);bad['cells'][0][key]=value;assert not source_tables_match(bad,truth);bads.append(key)
    for change in ({'rows':2},{'columns':3},{'cells':good['cells'][:1]},{'cells':good['cells']*2}):assert not source_tables_match({**good,**change},truth)
    observe('minimum-installed-table-known-controls',{'correct_table':True,'wrong_cell_fields_rejected':bads,'wrong_dimensions_missing_duplicate_rejected':4})


@pytest.mark.parametrize('owner',['local','hub'])
def test_installed_minimum_python_can_capture_search_and_read_all_formats(tmp_path,owner):
    # TC-008-minimum-installed-mac
    config=json.loads(Path(CONFIG).read_text());entry=config[owner];python=Path(entry['python']);wheel=Path(entry['wheel'])
    root=tmp_path/owner;root.mkdir();run_cwd=root/'not-source-cwd';run_cwd.mkdir();state=root/'state';state.mkdir()
    env={k:v for k,v in os.environ.items() if not k.startswith('PYTHON') and not k.startswith('SMM_') and k!='VIRTUAL_ENV'}
    env['PYTHONUTF8']='1';env['PYTHONIOENCODING']='utf-8'
    expected={}
    with ZipFile(wheel) as z:
        assert z.testzip() is None
        expected={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if not n.endswith('/') and (n.startswith('smm_'+owner+'/') or n.endswith('.dist-info/METADATA'))}
    manifest=root/'expected-installed.json';manifest.write_text(json.dumps(expected))

    identity=subprocess.run([str(python),'-I','-c',IDENTITY_CODE,owner,str(manifest),config['expected_system']],cwd=run_cwd,env=env,capture_output=True,text=True,encoding='utf-8',timeout=20)
    observe('minimum-installed-identity',{'owner':owner,'exit':identity.returncode,'stdout':identity.stdout,'stderr':identity.stderr,'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest()})
    assert identity.returncode==0,identity.stderr
    package=json.loads(identity.stdout);assert Path(package['prefix']).resolve()==python.parent.parent.resolve()
    assert Path(package['package_root']).resolve().is_relative_to(python.parent.parent.resolve())
    bad_manifest=root/'wrong-installed.json';bad={**expected,next(iter(expected)):'0'*64};bad_manifest.write_text(json.dumps(bad))
    wrong_sha=subprocess.run([str(python),'-I','-c',IDENTITY_CODE,owner,str(bad_manifest),config['expected_system']],cwd=run_cwd,env=env,capture_output=True,text=True,encoding='utf-8',timeout=20)
    source_env={**env,'PYTHONPATH':str(Path(__file__).resolve().parents[1]/'src')}
    source_probe=subprocess.run([str(python),'-c',IDENTITY_CODE,owner,str(manifest),config['expected_system']],cwd=run_cwd,env=source_env,capture_output=True,text=True,encoding='utf-8',timeout=20)
    observe('minimum-installed-probe-rejection-controls',{'owner':owner,'wrong_sha_exit':wrong_sha.returncode,'wrong_sha_stderr':wrong_sha.stderr,'source_import_exit':source_probe.returncode,'source_import_stderr':source_probe.stderr})
    assert wrong_sha.returncode!=0 and 'installed package bytes differ from wheel' in wrong_sha.stderr
    assert source_probe.returncode!=0 and 'source package is not an installed origin' in source_probe.stderr
    assert package['isolated']==1 and package['system']==config['expected_system']
    if os.name=='nt':
        import csv,io
        own_sid=list(csv.reader(io.StringIO(subprocess.check_output(['whoami.exe','/user','/fo','csv','/nh'],text=True,encoding='utf-8'))))[-1][1]
        assert package['actor']=={'sid':own_sid,'administrator_group':False}
    else:assert package['actor']=={'uid':os.getuid()} and os.getuid()!=0
    # -I intentionally ignores PYTHONUTF8; carry the UTF-8 protocol setting as
    # an interpreter flag, like the shared installed-platform runner does.
    prefix=[str(python),'-I','-X','utf8','-m','smm_'+owner+'.cli']+(['--db',str(state/'local.sqlite3')] if owner=='local' else ['hub','--state-dir',str(state)])
    def command(*args):
        argv=prefix+list(map(str,args));result=subprocess.run(argv,cwd=run_cwd,env=env,capture_output=True,text=True,encoding='utf-8',timeout=70)
        observe('minimum-installed-cli',{'owner':owner,'argv':argv,'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
        assert result.returncode==0,result.stderr
        return json.loads(result.stdout)
    project=command('project','create','minimum ordinary');global_project=command('project','ensure-global');unrelated=command('project','create','unrelated')
    projects=[project,global_project];assert len({p['id'] for p in [*projects,unrelated]})==3
    kind_key='kind' if owner=='local' else 'project_kind'
    assert project[kind_key]=='ordinary' and global_project[kind_key]=='global' and unrelated[kind_key]=='ordinary'
    configured=command('documents','processing-configure','--expected-revision',0,'--ocr-executable',ENGINE,'--ocr-data-dir',DATA,'--languages','chi_sim+eng')
    checked=command('documents','processing-status','--check')
    assert checked['config']['revision']==configured['config']['revision']==1
    assert checked['ocr']['ready'] is True and checked['ocr']['errors']==[]
    assert all(checked['formats'][kind]['available'] for kind in ('docx','xlsx','pdf'))
    items=[];ids=set()
    for group,p in enumerate(projects):
        directory=root/('sources'+str(group));directory.mkdir()
        for kind in ('docx','xlsx','nativepdf','ocrpdf'):
            key=owner+('alpha' if group==0 else 'beta')+kind
            if kind=='ocrpdf':
                anchor=(owner+'SCAN'+('ALPHA' if group==0 else 'BETA')).upper();raw=scan_pdf(anchor);truth={'words':[anchor+' RETRY 73428','CAPTURED ORIGINAL 12345.67'],'excluded':[],'tables':[]};format='pdf'
            elif kind=='docx':
                format='docx';raw,source=docx_fixture(key)
                tables=[{'rows':max(c[0]+c[3]-1 for c in cells),'columns':max(c[1]+c[4]-1 for c in cells),'cells':cells,'location':{'part':'word/document.xml','path':path}} for cells,path in zip(source['tables'],source['table_paths'])]
                truth={'words':source['words'],'excluded':source['excluded'],'tables':tables,'ordered_groups':[source['body_order']]};anchor=truth['words'][0].split()[0]
            else:
                format='pdf' if kind=='nativepdf' else kind;raw,truth=native_input(format,key);anchor=truth['words'][0].split()[0]
                if kind=='nativepdf':truth['ordered_groups']=[truth['words']]
            name=key+'.'+format;path=directory/name;path.write_bytes(raw)
            keep('inputs/'+name,raw);keep('truth/'+name+'.json',json.dumps(truth,ensure_ascii=False).encode())
            items.append({'kind':kind,'format':format,'name':name,'path':path,'raw':raw,'truth':truth,'anchor':anchor,'project':p,'before':(path.stat().st_mtime_ns,hashlib.sha256(raw).hexdigest())})
        source=command('documents','add',directory,'--project-id',p['id']);command('documents','refresh','--source-id',source['id'])
        files=command('documents','files','--source-id',source['id']);own=[i for i in items if i['project']['id']==p['id']]
        assert len(files)==4 and len({f['id'] for f in files})==4
        assert {Path(f['path']).name for f in files}=={i['name'] for i in own}
        for item in own:
            f=next(f for f in files if Path(f['path']).name==item['name']);assert f['version']==f['processing_version']==1 and f['latest_attempt']['status']=='ready'
            assert f['id'] not in ids;ids.add(f['id']);item.update(id=f['id'],source_id=source['id'])
            assert (item['path'].stat().st_mtime_ns,hashlib.sha256(item['path'].read_bytes()).hexdigest())==item['before']
    assert len(ids)==8
    database=state/('local.sqlite3' if owner=='local' else 'smm-hub.sqlite3')
    with sqlite3.connect('file:'+str(database)+'?mode=ro',uri=True) as con:
        archive=json.loads(con.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
        device=archive if owner=='local' else json.loads(con.execute("SELECT value FROM settings WHERE key='hub_identity'").fetchone()[0])
    for item in items:item['origin']={'device_id':device,'archive_id':archive,'document_id':item['id']}
    def search(item,p):
        return command('documents','search',item['anchor'],'--scope','project','--project-id',p['id'],'--limit',50,*(['--local'] if owner=='local' else []))['results']
    def read_all(item,phase):
        hit=item['hit'];value=command('documents','read','--reference',hit['reference'],'--start',0,'--end',hit['text_length'])
        assert value['id']==item['id'] and value['version']==value['processing_version']==1 and value['format']==item['format']
        assert value['sha256']==hashlib.sha256(item['raw']).hexdigest()
        assert_complete_source_text(value['text'],item['truth'],item['kind']=='ocrpdf')
        assert all(w not in value['text'] for w in item['truth']['excluded'])
        assert value['origin']==item['origin'] and value['source_ids']==[item['source_id']]
        assert value['processing_status']=='ready'
        if item['kind']=='ocrpdf':assert any(l.get('method')=='ocr' for l in value['locations'])
        summaries=value['tables'];assert len(summaries)==len(item['truth']['tables']) and len({t['table_id'] for t in summaries})==len(summaries)
        tables=[command('documents','read','--reference',hit['reference'],'--view','table','--table-id',t['table_id'],'--row-start',1,'--row-end',t['rows']+1,'--column-start',1,'--column-end',t['columns']+1) for t in summaries]
        for table in tables:
            assert table['id']==item['id'] and table['origin']==item['origin'] and table['source_ids']==[item['source_id']]
            assert table['version']==table['processing_version']==1 and table['sha256']==hashlib.sha256(item['raw']).hexdigest()
        used=set()
        for truth in item['truth']['tables']:
            matches=[t for t in tables if source_tables_match(t,truth) and all(t['location'].get(k)==v for k,v in truth['location'].items())]
            assert len(matches)==1
            assert matches[0]['table_id'] not in used;used.add(matches[0]['table_id'])
        assert used=={t['table_id'] for t in tables}
        info=command('documents','read','--reference',hit['reference'],'--view','original-info');assert info['id']==item['id'] and info['available'] is True
        assert info['origin']==item['origin'] and info['source_ids']==[item['source_id']] and info['format']==item['format']
        assert info['version']==info['processing_version']==1 and info['sha256']==hashlib.sha256(item['raw']).hexdigest() and info['bytes']==len(item['raw'])
        output=root/(phase+'-'+item['name']);result=command('documents','read','--reference',hit['reference'],'--original-output',output)
        assert output.read_bytes()==item['raw'] and result['sha256']==info['sha256'];keep('downloads/'+phase+'-'+item['name'],output.read_bytes())
        observe('minimum-installed-read-complete',{'owner':owner,'phase':phase,'id':item['id'],'project_id':item['project']['id'],'kind':item['kind'],'source_id':item['source_id'],'sha256':info['sha256'],'table_ids':sorted(used),'text':value['text']})
        return {'text':value,'tables':tables,'info':info}
    for item in items:
        hits=search(item,item['project']);assert len(hits)==1 and hits[0]['id']==item['id'] and hits[0]['source_ids']==[item['source_id']]
        item['hit']=hits[0];assert hits[0]['origin']==item['origin']
        assert hits[0]['version']==hits[0]['processing_version']==1 and hits[0]['sha256']==hashlib.sha256(item['raw']).hexdigest()
        for p in [x for x in [*projects,unrelated] if x['id']!=item['project']['id']]:assert search(item,p)==[]
        item['snapshot']=read_all(item,'before-offline')
    for item in items:item['path'].unlink()
    for item in items:
        hits=search(item,item['project']);assert [h['id'] for h in hits]==[item['id']]
        assert read_all(item,'after-offline')==item['snapshot']
    observe('minimum-installed-complete',{'owner':owner,'document_ids':sorted(ids),'files':len(items),'project_ids':[p['id'] for p in projects],'python':package['python'],'actual_actor':package['actor'],'system':package['system'],'actual_cli_new_process_per_request':True,'source_files_unavailable':True})
