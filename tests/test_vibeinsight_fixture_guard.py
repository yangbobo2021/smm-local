"""The opt-in probe cannot seed an unmarked external database."""
import importlib.util
import json
from pathlib import Path

import pytest


def module():
    source=Path(__file__).resolve().parents[1]/'scripts/acceptance/vibeinsight_fixture.py'
    spec=importlib.util.spec_from_file_location('fixture_guard',source)
    result=importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def test_unmarked_destination_is_rejected_before_any_connection(tmp_path,monkeypatch):
    m=module(); calls=[]
    monkeypatch.setattr(m,'run',lambda *args,**kwargs:calls.append(args))
    manifest=tmp_path/'external.json';manifest.write_text(json.dumps({'host':'external.example','kind':'external'}))
    with pytest.raises(ValueError,match='not a generated isolated fixture'):
        m.Fixture(manifest,'psql')
    assert not calls


def test_instance_mismatch_cannot_reach_a_write(tmp_path,monkeypatch):
    m=module(); calls=[]
    def query(argv,**kwargs):
        calls.append(kwargs['data']);return 'other-instance\n'
    monkeypatch.setattr(m,'run',query)
    manifest=tmp_path/'fixture.json';manifest.write_text(json.dumps({'kind':m.MARKER,'instance':'expected-instance',
        'host':'external.example','port':5432,'database':'postgres','admin_password':'synthetic-only','psql':'psql'}))
    with pytest.raises(ValueError,match='refusing writes'):
        m.Fixture(manifest)
    assert calls==['SELECT marker FROM smm_fixture_instance']
