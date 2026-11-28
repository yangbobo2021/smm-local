"""Readiness denial controls use real owned files and the caller's original budget."""
from pathlib import Path
import json
import time
import pytest
from document_formats_fixture_io import read_fixture_json
from document_helpers import observe


@pytest.mark.parametrize('error',[PermissionError,FileNotFoundError])
def test_temporary_metadata_denial_returns_only_complete_json(tmp_path,monkeypatch,error):
    path=tmp_path/'owned.json';expected={'nonce':'fixture-ready','metadata':{'sequence':123,'revision':456}}
    path.write_text(json.dumps(expected),encoding='utf-8');original=Path.read_text;calls=[]
    def read(self,*a,**kw):
        if self==path:
            calls.append(str(self))
            if len(calls)==1:raise error('controlled metadata not yet observable')
        return original(self,*a,**kw)
    with monkeypatch.context() as patch:
        patch.setattr(Path,'read_text',read)
        assert read_fixture_json(path,deadline=time.monotonic()+1)==expected
    assert len(calls)==2
    observe('fixture-readiness-one-denial',{'exception':error.__name__,'calls':len(calls),'full_value':expected})


def test_persistent_metadata_denial_keeps_original_deadline_and_exception(tmp_path,monkeypatch):
    path=tmp_path/'owned.json';path.write_text('{}',encoding='utf-8');original=Path.read_text;calls=[]
    def read(self,*a,**kw):
        if self==path:calls.append(str(self));raise PermissionError('persistent owned fixture denial')
        return original(self,*a,**kw)
    deadline=time.monotonic()+.03
    with monkeypatch.context() as patch:
        patch.setattr(Path,'read_text',read)
        with pytest.raises(PermissionError,match='persistent owned fixture denial'):
            read_fixture_json(path,deadline=deadline)
    assert calls and time.monotonic()>=deadline
    observe('fixture-readiness-persistent-denial',{'calls':len(calls),'original_error_preserved':True,'original_deadline_reached':True})


def test_bad_json_is_not_a_readiness_retry(tmp_path,monkeypatch):
    path=tmp_path/'owned.json';path.write_text('{',encoding='utf-8');original=Path.read_text;calls=[]
    def read(self,*a,**kw):
        if self==path:calls.append(str(self))
        return original(self,*a,**kw)
    with monkeypatch.context() as patch:
        patch.setattr(Path,'read_text',read)
        with pytest.raises(json.JSONDecodeError):read_fixture_json(path,deadline=time.monotonic()+1)
    assert len(calls)==1
