"""Swallowed .pth failures cannot turn actual-role access controls green."""
from copy import deepcopy
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/acceptance'))
from document_formats_scm_native_guard import validate_storage_access


def test_all_service_starts_require_exact_actual_access_receipt():
    values=[]
    checks=[{'check':'ancestor-list','desired_access':1,'denied':True,'winerror':5},
        {'check':'ancestor-security','desired_access':0x20000,'denied':True,'winerror':5},
        {'check':'state-list-and-security','desired_access':0x20081,'denied':False,'winerror':0}]
    kwargs={'service_name':'smm-hub-owned','state':'D:/owned/hub'}
    for pid,argv in [(10,['-c',kwargs['service_name'],kwargs['state']]),
        (20,['python','-m','smm_hub._archive.document_worker','--task-token','a'*32])]:
        actor={'sid':'S-1-5-19','session_id':0,'argv':argv,'executable':'real-python',
            'prefix':'protected-prefix','cwd':'owned-root'}
        values.append({'kind':'identity','pid':pid,'owner':'hub',**actor})
        values.append({'kind':'native-storage-ancestor-control','pid':pid,'owner':'hub',
            'identity':actor,'checks':deepcopy(checks)})
    assert len(validate_storage_access(values,**kwargs))==2
    for index in (1,3):
        with pytest.raises(AssertionError):validate_storage_access(values[:index]+values[index+1:],**kwargs)
        for check in range(3):
            wrong=deepcopy(values);wrong[index]['checks'][check]['denied']=not checks[check]['denied']
            with pytest.raises(AssertionError):validate_storage_access(wrong,**kwargs)
        wrong=deepcopy(values);wrong[index]['identity']['sid']='S-1-5-18'
        with pytest.raises(AssertionError):validate_storage_access(wrong,**kwargs)
        with pytest.raises(AssertionError):validate_storage_access(values+[deepcopy(values[index])],**kwargs)
    # A reused PID is another startup, never satisfied by its earlier receipt.
    with pytest.raises(AssertionError):validate_storage_access(values+[deepcopy(values[0])],**kwargs)
    for key in ('service_name','state'):
        with pytest.raises(AssertionError):validate_storage_access(values,**{**kwargs,key:'other'})
