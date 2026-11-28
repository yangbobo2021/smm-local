"""A ready attempt is not yet a searchable, readable publication."""
from copy import deepcopy
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/acceptance'))
from document_formats_upload_transport import published_or_failed,wait


def entry(status):
    return {'id':'document','sha256':'a'*64,'version':1,'processing_version':1,
        'publication_pending':False,'original_available':True,
        'latest_attempt':{'status':status,'capture_id':'c'*32},
        'published_snapshot':{'status':status,'capture_id':'c'*32,'sha256':'a'*64,
            'result_sha256':'b'*64,'version':1,'processing_version':1}}


@pytest.mark.parametrize('status',['ready','partial','empty-success'])
def test_wait_requires_current_published_snapshot(status,monkeypatch):
    good=entry(status)
    early={**deepcopy(good),'publication_pending':True,'published_snapshot':None,
        'version':0,'processing_version':0,'original_available':False}
    assert not published_or_failed(early) and published_or_failed(good)
    for key,wrong in [('capture_id','old'),('sha256','wrong'),('version',2),
        ('processing_version',2),('status','other'),('result_sha256',None)]:
        changed=deepcopy(good);changed['published_snapshot'][key]=wrong
        assert not published_or_failed(changed)
    assert not published_or_failed({**good,'original_available':False})
    class Probe:
        calls=0
        def path(self,role,path):return path
        def request(self,role,path):
            self.calls+=1
            return [early if self.calls==1 else good]
    probe=Probe();monkeypatch.setattr('document_formats_upload_transport.time.sleep',lambda _:None)
    assert wait(probe,'hub','document')==good and probe.calls==2
    probe=Probe()
    with pytest.raises(AssertionError):wait(probe,'hub','document',timeout=0)


def test_failed_attempt_does_not_wait_for_publication():
    failed={'latest_attempt':{'status':'failed','capture_id':'c'*32},
        'version':0,'processing_version':0,'published_snapshot':None,
        'publication_pending':False,'original_available':False}
    assert published_or_failed(failed)
    for status in ('pending','processing'):
        assert not published_or_failed({**failed,'latest_attempt':{'status':status}})
