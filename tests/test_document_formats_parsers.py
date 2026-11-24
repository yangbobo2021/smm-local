"""008 Word acceptance: independent source paths, order, cells and raw bytes."""
import copy
import hashlib
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from xml.etree import ElementTree as ET
import pytest
from document_helpers import Fixture, fingerprint, observe
from document_formats_fixtures import docx_fixture


def assert_anchor(text, locations, anchor):
    matches = [loc for loc in locations if loc['part']==anchor['part'] and loc['path']==anchor['path']]
    assert len(matches)==1, (anchor,matches)
    loc = matches[0]
    assert text[loc['start']:loc['end']]==anchor['text'], (anchor,loc,text)
    assert loc['start']==text.index(anchor['text'])
    assert loc['end']==loc['start']+len(anchor['text'])
    assert 'page' not in loc


def assert_text_result(result, expected):
    for word in expected['words']:
        assert result['text'].count(word)==1, word
    assert all(word not in result['text'] for word in expected['excluded'])
    positions = [result['text'].index(word) for word in expected['body_order']]
    assert positions==sorted(positions), positions
    assert {(loc['part'],loc['path']) for loc in result['locations']} == {(a['part'],a['path']) for a in expected['anchors']}
    for anchor in expected['anchors']:
        assert_anchor(result['text'],result['locations'],anchor)


def assert_table_result(view, table_path, expected_cells):
    assert view['location']['part']=='word/document.xml'
    assert view['location']['path']==table_path
    cells=view['cells']; coordinates=[(c['row'],c['column']) for c in cells]
    assert len(coordinates)==len(set(coordinates)), coordinates
    anchors={(r,c):(text,rs,cs) for r,c,text,rs,cs in expected_cells}
    continuations={}
    for (r,c),(text,rs,cs) in anchors.items():
        for rr in range(r,r+rs):
            for cc in range(c,c+cs):
                if (rr,cc)!=(r,c):continuations[(rr,cc)]=(r,c)
    assert set(anchors).issubset(coordinates)
    assert set(coordinates).issubset(set(anchors)|set(continuations))
    for cell in cells:
        coord=(cell['row'],cell['column'])
        assert cell['location']['part']=='word/document.xml'
        assert cell['location']['path']==table_path+'/row['+str(coord[0])+']/cell['+str(coord[1])+']'
        if coord in anchors:
            assert not cell.get('merged_into')
            assert (cell['text'],cell['row_span'],cell['column_span'])==anchors[coord]
        else:
            # Sparse anchor-only representation is allowed. Returned continuations
            # must point to their true anchor and must never repeat its text.
            assert cell['text'] in ('',None)
            assert cell['merged_into']==dict(zip(('row','column'),continuations[coord]))


def test_docx_all_parts_tables_and_revisions(tmp_path):
    # TC-008-docx
    f=Fixture(tmp_path);project=f.project('008 Word 文档');truth={}
    for key in ('wordalpha','wordbeta'):
        raw,expected=docx_fixture(key);path=f.file(key+'.docx',raw=raw)
        truth[path.name]={'path':path,'raw':raw,'expected':expected,'before':fingerprint(path)}
    source=f.add(tmp_path/'docs',projects=[project]);refreshed=f.refresh(source)
    assert refreshed['sources'][0]['counts']['ready']==2, 'both supported DOCX files must become searchable'
    hits=f.search('wordalpha wordbeta',scope='project',project_id=project,local=True,limit=50)['results']
    assert len(hits)==2
    assert {Path(h['path']).name for h in hits}==set(truth)
    for hit in hits:
        item=truth[Path(hit['path']).name];expected=item['expected']
        assert hit['format']=='docx' and hit['processing_version']==1 and hit['original_available'] is True
        result=f.read(hit,start=0,end=hit['text_length']);assert_text_result(result,expected)
        for anchor in expected['anchors']:
            found=f.search(anchor['text'],scope='project',project_id=project,local=True,limit=50)['results']
            matching=[h for h in found if h['id']==hit['id']]
            assert len(matching)==1, anchor
            # Search may expose either excerpt-relative or full-snapshot offsets;
            # both must bind the independent source location and actual text.
            located=[loc for loc in matching[0]['locations'] if loc['part']==anchor['part'] and loc['path']==anchor['path']]
            assert len(located)==1, (anchor,matching)
            assert located[0]['start']==result['text'].index(anchor['text'])
            assert located[0]['end']==located[0]['start']+len(anchor['text'])
        locators=result['tables']
        assert len(locators)==len({t['table_id'] for t in locators})==3
        table_map={t['location']['path']:t for t in locators}
        assert set(table_map)==set(expected['table_paths'])
        views=[]
        for path,cells in zip(expected['table_paths'],expected['tables']):
            locator=table_map[path];view=f.read(hit,view='table',table_id=locator['table_id'])
            assert view['table_id']==locator['table_id']
            assert_table_result(view,path,cells);views.append(view)
        assert 'drawing' in result['coverage']['excluded']
        assert result['coverage']['revisions_present'] is True
        info=f.read(hit,view='original-info')
        assert info['available'] is True
        assert info['sha256']==hashlib.sha256(item['raw']).hexdigest() and info['bytes']==len(item['raw'])
        download=f.client.post('/api/documents/original',json={'reference':hit['reference']})
        assert download.status_code==200, download.text
        assert download.content==item['raw']
        assert fingerprint(item['path'])==item['before']
        observe('docx-'+expected['key'],{'hit':hit,'read':result,'tables':views,'original':info,'source':item['before']})


def source_node(root,path):
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    segments=path.split('/'); node=root
    if segments[0]=='body':node=root.find('w:body',ns)
    tags={'paragraph':'p','table':'tbl','row':'tr','cell':'tc'}
    for segment in segments[1:]:
        name,index=segment[:-1].split('[');index=int(index)
        if name=='note':
            node=next(n for n in node if n.attrib.get('{'+ns['w']+'}id')==str(index))
        else:
            node=node.findall('w:'+tags[name],ns)[index-1]
    return node


def golden_result(truth):
    text='\n'.join(truth['words'])
    return {'text':text,'locations':[dict(part=a['part'],path=a['path'],start=text.index(a['text']),end=text.index(a['text'])+len(a['text'])) for a in truth['anchors']]}


def golden_table(path,cells):
    return {'location':{'part':'word/document.xml','path':path},'cells':[{'row':r,'column':c,'text':text,'row_span':rs,'column_span':cs,'location':{'part':'word/document.xml','path':path+'/row['+str(r)+']/cell['+str(c)+']'}} for r,c,text,rs,cs in cells]}


def test_docx_fixture_truth_is_independent():
    for key in ('wordalpha','wordbeta'):
        raw,truth=docx_fixture(key)
        with ZipFile(BytesIO(raw)) as z:
            assert set(truth['parts']).issubset(z.namelist())
            for anchor in truth['anchors']:
                node=source_node(ET.fromstring(z.read(anchor['part'])),anchor['path'])
                actual=''.join(n.text or '' for n in node.iter() if n.tag.endswith('}t'))
                assert actual==anchor['text'], anchor
            assert z.read('word/document.xml').count(b'<w:tbl>')==3
        assert len(truth['words'])==len(set(truth['words']))==16
        assert len(truth['anchors'])==16
        good=golden_result(truth);assert_text_result(good,truth)
        bad=copy.deepcopy(good);bad['locations'][-1]['path']=bad['locations'][0]['path']
        with pytest.raises(AssertionError):assert_text_result(bad,truth)
        bad=copy.deepcopy(good);bad['locations'][-1]['part']='word/header1.xml'
        with pytest.raises(AssertionError):assert_text_result(bad,truth)
        bad=copy.deepcopy(good);bad['locations'][-1]['start']=0
        with pytest.raises(AssertionError):assert_text_result(bad,truth)
        bad=golden_result({**truth,'words':[truth['words'][1],truth['words'][0],*truth['words'][2:]]})
        with pytest.raises(AssertionError):assert_text_result(bad,truth)
        for path,cells in zip(truth['table_paths'],truth['tables']):
            table=golden_table(path,cells);assert_table_result(table,path,cells)
            bad=copy.deepcopy(table);bad['cells'][-1]['location']['path']=bad['cells'][0]['location']['path']
            with pytest.raises(AssertionError):assert_table_result(bad,path,cells)
            for r,c,text,rs,cs in cells:
                if rs>1 or cs>1:
                    rr=r+int(rs>1);cc=c+int(cs>1)
                    continuation={'row':rr,'column':cc,'text':'','merged_into':{'row':r,'column':c},'location':{'part':'word/document.xml','path':path+'/row['+str(rr)+']/cell['+str(cc)+']'}}
                    table['cells'].append(continuation);assert_table_result(table,path,cells)
                    continuation['text']=text
                    with pytest.raises(AssertionError):assert_table_result(table,path,cells)
