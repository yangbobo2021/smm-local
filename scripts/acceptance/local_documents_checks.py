"""Independent expectations for the opt-in installed-document platform probe."""
import hashlib
import math
from pathlib import Path
import tempfile
import zipfile


def normalized(raw):
    return raw.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')


def text_range(value, body, *, start=None, end=None):
    """Check Python codepoints and LF ownership without product helpers."""
    a=value['start']; b=value['end']
    assert type(a) is int and type(b) is int and 0<=a<b<=len(body)
    if start is not None:assert a==start
    if end is not None:assert b==end
    assert value['text']==body[a:b]
    assert value['start_line']==1+body[:a].count('\n')
    assert value['end_line']==1+body[:b-1].count('\n')


def hit(value, raw, expected_path):
    body=normalized(raw)
    assert value['path']==str(expected_path) and value['captured_at']
    assert value['sha256']==hashlib.sha256(raw).hexdigest() and value['text_length']==len(body)
    assert value['version']>=1 and value['id'] and value['reference'] and value['source_ids']
    text_range(value,body)
    assert value['end']-value['start']<=2000 and math.isfinite(value['bm25_score'])


def paths(result, wanted):
    items=result['results']
    assert len(items)==len(wanted)==len({x['id'] for x in items})==len({x['path'] for x in items})
    assert {x['path'] for x in items}=={str(x) for x in wanted}


def identity(value, platform):
    assert value['platform']==platform
    if platform=='win32':assert value['is_admin'] is False and value['session_id']>0
    else:assert value['uid']>0


def read_matches(value,search_hit,raw,path,*,start=None,end=None,collector=None):
    body=normalized(raw)
    assert value['path']==str(path) and value['id']==search_hit['id'] and value['version']==search_hit['version']
    assert value['sha256']==hashlib.sha256(raw).hexdigest() and value['text_length']==len(body)
    assert value['captured_at'] and '采集' in value['snapshot_kind']
    assert value['captured_by_source_id']==(search_hit['captured_by_source_id'] if collector is None else collector)
    assert set(value['source_ids'])==set(search_hit['source_ids']) and value['source_ids']
    text_range(value,body,start=search_hit['start'] if start is None else start,end=search_hit['end'] if end is None else end)


def sources(value,expected):
    assert len(value)==len(expected)==len({x['id'] for x in value})
    actual={x['id']:x for x in value};assert set(actual)==set(expected)
    for sid,fields in expected.items():
        for key,wanted in fields.items():
            if key=='counts':
                for name,count in wanted.items():assert actual[sid]['counts'][name]==count
            else:assert actual[sid][key]==wanted


def rejection(actual,expected):
    assert type(actual) is type(expected) and actual==expected


def evidence_available(root,names):
    for name in names:
        path=Path(root)/name;assert path.is_file() and path.stat().st_size>0
        if path.suffix=='.png':assert path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        elif path.suffix=='.zip':assert zipfile.is_zipfile(path)


def self_check():
    raw='needle 😀 e\u0301\r\n末行\n'.encode();body=normalized(raw)
    good={'start':0,'end':len(body),'text':body,'start_line':1,'end_line':2}
    text_range(good,body)
    for change in [{'text':'wrong'},{'start':True},{'end':len(body)+1},{'end_line':3},{'start':1}]:
        try:text_range({**good,**change},body)
        except AssertionError:pass
        else:raise AssertionError('range checker accepted an incorrect witness')
    for bad in [{'platform':'win32','is_admin':True,'session_id':1},{'platform':'win32','is_admin':False,'session_id':0},{'platform':'linux','uid':0}]:
        try:identity(bad,bad['platform'])
        except AssertionError:pass
        else:raise AssertionError('identity checker accepted an incorrect witness')
    paths({'results':[{'id':'a','path':'one'},{'id':'b','path':'two'}]},['one','two'])
    for bad in [[{'id':'a','path':'one'}],[{'id':'a','path':'one'},{'id':'a','path':'two'}],[{'id':'a','path':'one'},{'id':'b','path':'one'}]]:
        try:paths({'results':bad},['one','two'])
        except AssertionError:pass
        else:raise AssertionError('set checker accepted incomplete or duplicate targets')
    meta={**good,'id':'doc-a','version':2,'path':'one','sha256':hashlib.sha256(raw).hexdigest(),'text_length':len(body),'captured_at':'2026-01-01T00:00:00Z','captured_by_source_id':'source-a','source_ids':['source-a'],'snapshot_kind':'采集版本'}
    read_matches(meta,meta,raw,'one')
    for change in [{'path':'two'},{'id':'other'},{'version':999},{'sha256':'wrong'},{'captured_at':''},{'source_ids':[]},{'source_ids':['other-source']},{'captured_by_source_id':'other-source'},{'snapshot_kind':'live'}]:
        try:read_matches({**meta,**change},meta,raw,'one')
        except AssertionError:pass
        else:raise AssertionError('read checker accepted wrong identity/version/source metadata')
    expected={'source-a':{'path':'one','project_ids':[1],'status':'ready','revision':1,'counts':{'ready':1,'failed':0}}}
    source={'id':'source-a',**expected['source-a']};sources([source],expected)
    for values in [[],[{**source,'status':'pending'}],[{**source,'project_ids':[2]}],[{**source,'counts':{'ready':0,'failed':0}}]]:
        try:sources(values,expected)
        except AssertionError:pass
        else:raise AssertionError('source checker accepted false complete/pending/scope')
    for actual,wanted in [(0,2),(False,True),(200,400)]:
        try:rejection(actual,wanted)
        except AssertionError:pass
        else:raise AssertionError('rejection checker accepted a successful old-reference read')
    with tempfile.TemporaryDirectory(prefix='smm-006-checker-') as tmp:
        try:evidence_available(tmp,['missing.png'])
        except AssertionError:pass
        else:raise AssertionError('missing screenshot was accepted')
    return {'status':'passed','rejected_wrong_text_coordinates_identity_sets_sources_coverage_old_ref_success_and_missing_picture':True}
