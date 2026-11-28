"""Source-independent complex spreadsheet, deep-table and mixed-PDF oracles.

These checks drive installed products through the caller's real transports.
They add E1 materials; they do not claim service or cross-OS acceptance.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def fixtures(probe):
    from document_formats_xlsx_fixture import xlsx_fixture
    from document_formats_table_fixture import deep_word, deep_xlsx
    from document_formats_mixed_fixture import mixed_pdf
    items = []
    for role in ('a', 'hub'):
        prefix = 'L' if role == 'a' else 'H'
        materials = []
        for index, calendar in enumerate((False, True)):
            key = prefix + 'complex' + str(index)
            raw, truth = xlsx_fixture(key, date1904=calendar,
                                      formula_url='https://invalid.example/never-execute-formula')
            materials.append(('complex-xlsx', key, 'xlsx', index, raw, truth))
        for index, (kind, maker) in enumerate((('docx', deep_word), ('xlsx', deep_xlsx))):
            key = prefix + 'deep' + kind
            raw, truth = maker(key)
            materials.append(('deep', key, kind, index, raw, truth))
        raw, truth = mixed_pdf('mixedalpha' if role == 'a' else 'mixedbeta', probe.materials['font']['path'])
        materials.append(('mixed', prefix + 'mixed', 'pdf', 0, raw, truth))
        for kind, key, fmt, group, raw, truth in materials:
            project = probe.projects[role][group]
            path = probe.fixtures / (key + '.' + fmt)
            path.write_bytes(raw)
            probe.keep('extended-inputs/' + path.name, raw)
            probe.keep('extended-truth/' + key + '.json', json.dumps(truth, ensure_ascii=False).encode())
            probe.phase = 'explicit-refresh'
            source = probe.cli(role, 'documents', 'add', path, '--project-id', project['id'])
            assert source['status'] == 'pending'
            probe.cli(role, 'documents', 'refresh', '--source-id', source['id'])
            probe.phase = 'archive-only'
            rows = probe.cli(role, 'documents', 'files', '--source-id', source['id'])
            assert len(rows) == 1 and rows[0]['latest_attempt']['status'] == 'ready', rows
            entry = rows[0]
            assert entry['version'] == entry['processing_version'] == 1
            assert entry['sha256'] == hashlib.sha256(raw).hexdigest()
            truth['project'] = project['id']
            query = (key + 'Title' if kind == 'complex-xlsx' else truth['query'] if kind == 'deep'
                     else truth['pages'][0]['heading'])
            items.append({'role': role, 'project': project, 'source': source, 'path': path,
                          'id': entry['id'], 'entry': entry, 'kind': kind, 'format': fmt,
                          'label': key, 'query': query, 'raw': raw, 'truth': truth,
                          'sha256': hashlib.sha256(raw).hexdigest(), 'version': 1,
                          'processing_version': 1})
    return items


class Surface:
    """Read/search adapter; never imports or calls the product in-process."""
    def __init__(self, probe, item, *, transport='http', role=None, reference=None):
        self.probe, self.item = probe, item
        self.transport, self.role = transport, role or item['role']
        self.reference = reference
        self.reads = []

    def metadata(self, value):
        item = self.item
        assert value['origin'] == self.probe.expected_origin(item)
        assert value['version'] == item['version'] and value['processing_version'] == item['processing_version']
        assert value['sha256'] == item['sha256'] and value['format'] == item['format']

    def search(self, query, **kwargs):
        p, item = self.probe, self.item
        remote = self.role == 'a' and item['role'] == 'hub'
        body = {'query': query, 'scope': 'project', 'limit': 50,
                ('hub_project_id' if remote else 'project_id'): item['project']['id']}
        if self.role == 'a' and not remote:
            body['local'] = True
        if self.transport == 'http':
            result = p.request(self.role, p.path(self.role, '/documents/search'), p.body(self.role, **body))
        else:
            args = ['documents', 'search', query, '--scope', 'project', '--limit', 50,
                    '--hub-project-id' if remote else '--project-id', item['project']['id']]
            if self.role == 'a' and not remote:
                args.append('--local')
            result = p.cli(self.role, *args)
        own = [h for h in result['results'] if h['origin'] == p.expected_origin(item)]
        assert len(own) == 1
        self.metadata(own[0])
        return result

    def read(self, hit, **kwargs):
        p, item = self.probe, self.item
        reference = self.reference or hit['reference']
        if self.transport == 'http':
            value = p.request(self.role, p.path(self.role, '/documents/read'),
                              p.body(self.role, reference=reference, **kwargs))
        else:
            args = ['documents', 'read', '--reference', reference]
            for name, val in kwargs.items():
                args.extend(['--' + name.replace('_', '-'), val])
            value = p.cli(self.role, *args)
        self.metadata(value)
        self.reads.append({'request': kwargs, 'response': value})
        return value

    def hit(self):
        return next(h for h in self.search(self.item['query'])['results']
                    if h['origin'] == self.probe.expected_origin(self.item))


def full_text(surface, hit, expected):
    from test_document_formats_table_context import assert_text_window
    parts = []
    for start in range(0, len(expected), 16000):
        value = surface.read(hit, start=start, end=min(start + 16000, len(expected)))
        assert_text_window(value, {'text': expected})
        assert value['start'] == start and value['end'] == min(start + 16000, len(expected))
        parts.append(value['text'])
    assert ''.join(parts) == expected


def verify_deep(surface, hit, truth):
    from test_document_formats_table_context import assert_location, assert_text_window, assert_window
    assert_text_window(hit, truth)
    default = surface.read(hit)
    assert_text_window(default, truth)
    assert (default['start'], default['end']) == (hit['start'], hit['end'])
    full_text(surface, hit, truth['text'])
    assert len(default['tables']) == 2 and len({t['table_id'] for t in default['tables']}) == 2
    candidates = [t for t in default['tables'] if all(t['location'].get(k) == v for k, v in truth['location'].items())]
    assert len(candidates) == 1
    table = candidates[0]
    assert_location(table['location'], truth['location'])
    assert hit['table_context']['table_id'] == table['table_id']
    value = surface.read(hit, view='table', table_id=table['table_id'])
    assert_window(value, truth, target=truth['target'], window=hit['table_context']['suggested_window'])
    assert value['header_context'] == hit['table_context']['header_context']
    seen = set()
    for start in range(1, truth['rows'] + 1, 40):
        bounds = {'row_start': start, 'row_end': min(start + 40, truth['rows'] + 1),
                  'column_start': 1, 'column_end': truth['columns'] + 1}
        value = surface.read(hit, view='table', table_id=table['table_id'], **bounds)
        assert_window(value, truth, window=bounds)
        for cell in value['cells']:
            position = (cell['row'], cell['column'])
            assert position not in seen
            seen.add(position)
    assert seen == {(c['row'], c['column']) for c in truth['cells']}
    overview = next(t for t in default['tables'] if t['table_id'] != table['table_id'])
    value = surface.read(hit, view='table', table_id=overview['table_id'], row_start=1,
                         row_end=overview['rows'] + 1, column_start=1, column_end=overview['columns'] + 1)
    key = surface.item['label']
    expected = [(1, 1, key + 'Overview1'), (1, 2, key + 'Overview2')] if truth['format'] == 'docx' else [(1, 1, key + 'Overview')]
    assert (value['rows'], value['columns']) == (1, len(expected))
    assert [(c['row'], c['column'], c['text']) for c in value['cells']] == expected
    assert all(c['row_span'] == c['column_span'] == 1 for c in value['cells'])


def verify_mixed(surface, hit, truth):
    from test_document_formats_pdf_mixed import assert_dimensions, assert_coverage, assert_region, assert_table_summary
    from test_document_formats_pdf_ocr import distance, normal, assert_box
    value = surface.read(hit, start=0, end=hit['text_length'])
    assert_dimensions(hit, truth)
    assert_dimensions(value, truth)
    assert_coverage(value, truth)
    expected, actual = normal(truth['text']), normal(value['text'])
    assert distance(expected, actual) / len(expected) <= .01
    assert value['coverage']['errors'] == []
    assert len(value['tables']) == len({t['table_id'] for t in value['tables']}) == 3
    for page in truth['pages']:
        heading = page['heading']
        assert value['text'].count(heading) == 1
        start = value['text'].index(heading)
        end = start + len(heading)
        locs = assert_region(value, start, end, page['page'], 'native', page['heading_bbox'])
        found = surface.search(heading)
        own = [h for h in found['results'] if h['origin'] == surface.probe.expected_origin(surface.item)]
        assert len(own) == 1
        assert_dimensions(own[0], truth)
        assert any(loc in own[0]['locations'] for loc in locs)
        limit = value['text'].index(truth['pages'][page['page']]['heading']) if page['page'] < 3 else len(value['text'])
        indices = [i for i in range(end, limit) if not value['text'][i].isspace()]
        section = ''.join(value['text'][i] for i in indices)
        if page['page'] < 3:
            for field in ('title', 'paragraph'):
                word = normal(page[field]); offset = section.index(word)
                assert section.count(word) == 1
                assert_region(value, indices[offset], indices[offset + len(word) - 1] + 1,
                              page['page'], 'ocr', [.09, 140 / 900, .95, 310 / 900])
        tables = [t for t in value['tables'] if t['location']['page'] == page['page']]
        assert len(tables) == len(page['tables'])
        cursor = 0
        for wanted in page['tables']:
            for cell in wanted['cells']:
                word = normal(cell['text']); offset = section.index(word, cursor); cursor = offset + len(word)
                assert_region(value, indices[offset], indices[cursor - 1] + 1, page['page'], 'ocr', cell['bbox'])
            matches = [t for t in tables if all(abs(a - b) < .01 for a, b in zip(t['location']['bbox'], wanted['bbox']))]
            assert len(matches) == 1
            table = matches[0]
            assert_table_summary(table, wanted, page)
            view = surface.read(hit, view='table', table_id=table['table_id'])
            assert_dimensions(view, truth)
            assert (view['rows'], view['columns']) == (wanted['rows'], wanted['columns'])
            assert view['location']['page'] == page['page'] and view['location']['method'] == 'ocr'
            assert_box(view['location']['bbox'], wanted['bbox'])
            cells = {(c['row'], c['column']): c for c in view['cells']}
            assert len(cells) == len(view['cells']) == len(wanted['cells'])
            for source in wanted['cells']:
                cell = cells[(source['row'], source['column'])]
                assert cell['text'] == source['text'] and cell['row_span'] == cell['column_span'] == 1
                assert cell['location']['page'] == page['page'] and cell['location']['method'] == 'ocr'
                assert_box(cell['location']['bbox'], source['bbox'])
                search = surface.search(source['text'])
                own = [h for h in search['results'] if h['origin'] == surface.probe.expected_origin(surface.item)]
                assert len(own) == 1
                locations = [loc for loc in own[0]['locations'] if loc['page'] == page['page']
                             and value['text'][loc['start']:loc['end']] == source['text']
                             and all(abs(a - b) < .01 for a, b in zip(loc['bbox'], source['bbox']))]
                assert len(locations) == 1 and locations[0]['method'] == 'ocr'
            assert view['header_context']['role'] == 'first_content_row'
            assert sorted(view['header_context']['cells'], key=lambda c: c['column']) == [cells[(1, c)] for c in range(1, wanted['columns'] + 1)]


def verify(surface):
    item = surface.item
    hit = surface.hit()
    if item['kind'] == 'complex-xlsx':
        from test_document_formats_xlsx import verify_xlsx
        value = verify_xlsx(surface, hit, item['truth'])
        expected = '\n'.join(cell['text'] for sheet in item['truth']['sheets'].values() for cell in sheet.values())
        assert value['text'] == expected
    elif item['kind'] == 'deep':
        verify_deep(surface, hit, item['truth'])
    else:
        verify_mixed(surface, hit, item['truth'])
    info = surface.read(hit, view='original-info')
    assert info['available'] is True and info['bytes'] == len(item['raw'])
    assert surface.probe.raw_original(surface.role, surface.reference or hit['reference']) == item['raw']
    return hit
