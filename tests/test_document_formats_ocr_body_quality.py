"""Clear unframed scan text retains critical source identifiers and amounts."""
import hashlib
import json

import pytest

from document_helpers import Fixture, fingerprint, observe
from test_document_formats_retry import ENGINE, DATA, FONT, scan_pdf, cli, keep
from test_document_formats_pdf_ocr import normal, distance

pytestmark = pytest.mark.skipif(not all((ENGINE, DATA, FONT)), reason='requires explicit real local OCR assets')


@pytest.mark.parametrize('label', ['LOCALSCANGAMMA', 'HUBSCANGAMMA'])
def test_clear_body_identifiers_survive_actual_capture_and_read(tmp_path, label):
    # These are source labels, not claims about the executing creator's role.
    # The same fixture recipe generated the retained debug8 regression original.
    f = Fixture(tmp_path)
    project = f.project('body OCR ' + label)
    raw = scan_pdf(label)
    expected = label + ' RETRY 73428\nCAPTURED ORIGINAL 12345.67'
    path = f.file(label + '.pdf', raw=raw)
    before = fingerprint(path)
    truth = {'label': label, 'text': expected, 'critical': ['73428', '12345.67'],
             'source_pixels': [2000, 600], 'page_size': [600, 180],
             'regions': [[.045, .20, .95, .44], [.045, .48, .95, .76]]}
    keep('inputs/' + label + '.pdf', raw)
    keep('truth/' + label + '.json', json.dumps(truth).encode())
    status = cli(f, 'processing-status')
    cli(f, 'processing-configure', '--expected-revision', status['config']['revision'],
        '--ocr-executable', ENGINE, '--ocr-data-dir', DATA, '--languages', 'chi_sim+eng')
    source = f.add(path, projects=[project])
    f.refresh(source)
    hits = f.search(label, scope='project', project_id=project, local=True, limit=50)['results']
    assert len(hits) == 1 and hits[0]['sha256'] == hashlib.sha256(raw).hexdigest()
    hit = hits[0]
    result = f.read(hit, start=0, end=hit['text_length'])
    cer = distance(normal(expected), normal(result['text'])) / len(normal(expected))
    observe('body-quality-' + label, {'truth': truth, 'hit': hit, 'read': result, 'cer': cer,
                                     'source_fingerprint': before})
    assert result['processing_status'] == 'ready' and result['coverage']['errors'] == []
    assert cer <= .01, {'expected': expected, 'actual': result['text'], 'cer': cer}
    for critical in truth['critical']:
        assert critical in result['text']
        found = f.search(critical, scope='project', project_id=project, local=True, limit=50)['results']
        assert [h['id'] for h in found] == [hit['id']]
    assert result['tables'] == []
    for text, bounds in zip(expected.splitlines(), truth['regions']):
        located = [loc for loc in result['locations'] if normal(result['text'][loc['start']:loc['end']]) == normal(text)]
        assert len(located) == 1
        loc = located[0]
        assert loc['page'] == 1 and loc['method'] == 'ocr' and loc['page_width'] == 600 and loc['page_height'] == 180
        box = loc['bbox']
        assert len(box) == 4 and bounds[0] <= box[0] < box[2] <= bounds[2] and bounds[1] <= box[1] < box[3] <= bounds[3]
    response = f.client.post('/api/documents/original', json={'reference': hit['reference']})
    assert response.status_code == 200 and response.content == raw
    keep('downloads/' + label + '.pdf', response.content)
    assert fingerprint(path) == before
