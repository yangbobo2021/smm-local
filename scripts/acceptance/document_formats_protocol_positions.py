"""Source-derived location checks used by the installed protocol driver."""
from __future__ import annotations


def text_positions(value, truth):
    from test_document_formats_pdf_ocr import normal, assert_box
    for anchor in truth.get('part_positions', []):
        matches = [loc for loc in value['locations']
                   if value['text'][loc['start']:loc['end']] == anchor['text']]
        assert len(matches) == 1
        assert all(matches[0].get(k) == anchor[k] for k in ('part', 'path'))
    source = truth.get('native_positions')
    if source:
        from test_document_formats_pdf_native import assert_native_location_metadata
        assert_native_location_metadata(value, source)
        assert {u['page'] for u in value['coverage']['units']} == {p['page'] for p in source['pages']}
        for page in source['pages']:
            for paragraph in page['paragraphs']:
                locs = [loc for loc in value['locations'] if value['text'][loc['start']:loc['end']] == paragraph['text']]
                assert len(locs) == 1 and locs[0]['page'] == page['page']
                assert paragraph['top_min'] <= locs[0]['bbox'][1] * page['height'] <= paragraph['top_max']
            for table in page['tables']:
                for cell in table['cells']:
                    locs = [loc for loc in value['locations'] if value['text'][loc['start']:loc['end']] == cell['text']]
                    assert len(locs) == 1 and locs[0]['page'] == page['page']
                    assert_box(locs[0]['bbox'], cell['bbox'])
    source = truth.get('ocr_quality')
    if source:
        assert {u['page'] for u in value['coverage']['units']} == {1, 2}
        assert all(u['method'] == 'ocr' and u['status'] == 'ready' for u in value['coverage']['units'])
        for loc in value['locations']:
            assert loc['page_width'] == 240 and loc['page_height'] == 216
            assert loc['method'] == 'ocr' and loc['rotation'] == 0
        for page in source['pages']:
            for field, region in (('title', 'title_region'), ('paragraph', 'paragraph_region')):
                locs = [loc for loc in value['locations'] if loc['page'] == page['page']
                        and normal(value['text'][loc['start']:loc['end']]) == normal(page[field])]
                assert len(locs) == 1
                box, bounds = locs[0]['bbox'], page[region]
                assert len(box) == 4 and bounds[0] - .01 <= box[0] < box[2] <= bounds[2] + .01
                assert bounds[1] - .01 <= box[1] < box[3] <= bounds[3] + .01
            for cell in page['cells']:
                locs = [loc for loc in value['locations'] if loc['page'] == page['page']
                        and normal(value['text'][loc['start']:loc['end']]) == normal(cell['text'])]
                assert len(locs) == 1
                assert_box(locs[0]['bbox'], cell['bbox'])


def table_positions(value, truth):
    from test_document_formats_pdf_ocr import assert_box
    source = truth.get('native_positions')
    if source:
        from test_document_formats_pdf_native import assert_native_location_metadata
        assert_native_location_metadata(value, source)
        page = next(p for p in source['pages'] if p['page'] == value['location']['page'])
        candidates = [t for t in page['tables'] if all(any(c['text'] == v['text'] for v in value['cells']) for c in t['cells'])]
        assert len(candidates) == 1
        wanted = candidates[0]
    elif truth.get('ocr_quality'):
        page = next(p for p in truth['ocr_quality']['pages'] if p['page'] == value['location']['page'])
        wanted = page
        assert value['location']['method'] == 'ocr'
        assert value['location']['page_width'] == 240 and value['location']['page_height'] == 216
        assert value['location']['rotation'] == 0
    else:
        # Office cells retain independent source part and coordinate/path.
        for cell in value['cells']:
            loc = cell['location']
            if 'sheet_index' in value['location']:
                from document_formats_table_fixture import letters
                assert loc['part'] == 'xl/worksheets/sheet' + str(value['location']['sheet_index']) + '.xml'
                assert loc['coordinate'] == letters(cell['column']) + str(cell['row'])
                assert loc['sheet'] == value['location']['sheet']
            elif 'path' in value['location']:
                anchors = [a for a in truth['part_positions'] if a['text'] == cell['text']]
                assert len(anchors) == 1
                assert loc['part'] == anchors[0]['part']
                assert loc['path'] == anchors[0]['path'].rsplit('/paragraph[', 1)[0]
        return
    assert_box(value['location']['bbox'], wanted['bbox'])
    expected = {(c['row'], c['column']): c for c in wanted['cells']}
    assert len(value['cells']) == len(expected)
    for cell in value['cells']:
        target = expected[cell['row'], cell['column']]
        assert cell['location']['page'] == page['page']
        assert cell['location']['method'] == ('native' if source else 'ocr')
        assert_box(cell['location']['bbox'], target['bbox'])


def page_anchors(truth):
    """Search each source page/critical table cell, including repeated headers."""
    if truth.get('native_positions'):
        return [(text, page['page']) for page in truth['native_positions']['pages']
                for text in [*[p['text'] for p in page['paragraphs']], *[c['text'] for c in page['cells']]]]
    if truth.get('ocr_quality'):
        return [(text, page['page']) for page in truth['ocr_quality']['pages']
                for text in [page['title'], page['paragraph'], *[c['text'] for c in page['cells']]]]
    return []
