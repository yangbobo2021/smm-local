"""The task-owned preparation gate advances only on authenticated progress."""
from types import SimpleNamespace
import pytest
import document_formats_health_hook as hook


def test_preparation_progress_renews_only_after_a_new_complete_check(tmp_path, monkeypatch):
    clock=SimpleNamespace(value=100.0)
    monkeypatch.setattr(hook,'time',SimpleNamespace(monotonic=lambda:clock.value))
    token='a'*32;nonce='b'*32
    assert hook.preparation_progress(tmp_path,token,nonce,-1,120,30)==(-1,120)
    marker=tmp_path/('preparing-'+token+'.json')
    hook.write(marker,{'token':token,'nonce':nonce,'step':0})
    assert hook.preparation_progress(tmp_path,token,nonce,-1,120,30)==(0,130)
    clock.value=110
    assert hook.preparation_progress(tmp_path,token,nonce,0,130,30)==(0,130)
    hook.write(marker,{'token':token,'nonce':nonce,'step':1})
    assert hook.preparation_progress(tmp_path,token,nonce,0,130,30)==(1,140)


@pytest.mark.parametrize('change',[{'token':'c'*32},{'nonce':'d'*32},{'step':True},{'step':0}])
def test_preparation_progress_rejects_another_task_or_nonprogress(tmp_path, change):
    token='a'*32;nonce='b'*32
    value={'token':token,'nonce':nonce,'step':2};value.update(change)
    hook.write(tmp_path/('preparing-'+token+'.json'),value)
    with pytest.raises(AssertionError):hook.preparation_progress(tmp_path,token,nonce,1,123,30)
