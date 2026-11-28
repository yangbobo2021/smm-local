"""Observer controls: an enrolled Windows redirector is not the parser PID."""
from copy import deepcopy
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/acceptance'))
from document_formats_windows_identity import validate_worker_enrollment


def test_redirector_enrollment_rejects_foreign_or_reused_processes(tmp_path):
    declared=tmp_path/'venv.exe';declared.write_bytes(b'controlled declared image')
    base=tmp_path/'base.exe';base.write_bytes(b'controlled interpreter image')
    aid='a'*32;module='smm_local.document_worker'
    root={'pid':100,'created':17.0,'creation_filetime':1234,'parent_pid':90,
        'sid':'actual-actor','session_id':2,'executable':str(declared),
        'argv':[str(declared),'-B','-m',module,'--task-token',aid]}
    worker={**root,'pid':101,'created':17.1,'creation_filetime':1235,
        'parent_pid':100,'executable':str(base)}
    controller={**root,'pid':90,'created':16.0,'creation_filetime':1000,'parent_pid':80}
    state={'controller':{'pid':90,'created':16.0},'token':aid,'worker':{'pid':100,'created':17.0},
        'children':[{'pid':100,'created':17.0},{'pid':101,'created':17.1}],
        'windows_job':{'atomic':True,'worker_ticks':1234,'controller_ticks':1000}}
    kwargs={'sid':'actual-actor','session':2,'attempt_id':aid,'module':module,
        'declared_python':declared,'base_python':base}
    validate_worker_enrollment(worker,root,controller,state,**kwargs)
    # The same-PID interpreter branch keeps its actual kernel creation proof.
    validate_worker_enrollment(root,root,controller,state,**kwargs)
    for target,field,bad in [('worker','parent_pid',99),('worker','sid','foreign'),
        ('root','session_id',0),('root','created',18.0),('root','creation_filetime',999),
        ('worker','executable',str(declared)),('root','executable',str(base))]:
        samples={'worker':deepcopy(worker),'root':deepcopy(root)};samples[target][field]=bad
        with pytest.raises(AssertionError):validate_worker_enrollment(samples['worker'],samples['root'],controller,state,**kwargs)
    for sample_name in ('worker','root'):
        samples={'worker':deepcopy(worker),'root':deepcopy(root)}
        samples[sample_name]['argv'][-1]='b'*32
        with pytest.raises(AssertionError):validate_worker_enrollment(samples['worker'],samples['root'],controller,state,**kwargs)
    for changed in ({**state,'token':'b'*32},{**state,'children':state['children'][:1]},
        {**state,'windows_job':{**state['windows_job'],'atomic':False}},
        {**state,'windows_job':{**state['windows_job'],'controller_ticks':999}},
        {**state,'windows_job':{**state['windows_job'],'worker_ticks':999}}):
        with pytest.raises(AssertionError):validate_worker_enrollment(worker,root,controller,changed,**kwargs)

    for field,wrong in [('sid','foreign'),('created',16.5),('pid',89),('session_id',0)]:
        with pytest.raises(AssertionError):
            validate_worker_enrollment(worker,root,{**controller,field:wrong},state,**kwargs)
