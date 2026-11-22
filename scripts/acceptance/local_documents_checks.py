"""Independent expectations for the opt-in installed-document platform probe."""
import hashlib
import math


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
    return {'status':'passed','rejected_wrong_text_coordinates_identity_and_sets':True}
