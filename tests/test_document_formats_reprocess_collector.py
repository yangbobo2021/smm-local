"""Explicit saved reprocessing repairs a missing or retired collector."""
from pathlib import Path
import pytest
from document_helpers import Fixture, observe
from document_formats_fixtures import docx_fixture
from test_document_formats_retry import cli, retry_args

pytest.importorskip('defusedxml')


@pytest.mark.parametrize('collector_state', ['missing', 'missing-multiple', 'retired', 'still-valid'])
def test_explicit_reprocess_records_a_current_capture_source_without_reversion(tmp_path, collector_state):
    fixture = Fixture(tmp_path)
    project = fixture.project('saved document')
    raw, _ = docx_fixture('collectorrepair')
    path = fixture.file('collector.docx', raw=raw)
    primary = fixture.add(path, projects=[project])
    fixture.refresh(primary)
    expected = primary['id']
    if collector_state != 'missing':
        overlap = fixture.add(path.parent, projects=[project])
        fixture.refresh(overlap)
        # The latest refresh made overlap the collector; exercise both keeping
        # it and choosing the other surviving continuous authorization.
        expected = overlap['id']
        if collector_state == 'retired':
            fixture.remove(overlap)
            expected = primary['id']
        elif collector_state == 'missing-multiple':
            expected = min(primary['id'], overlap['id'])
            with fixture.db.connect() as connection:
                connection.execute('UPDATE documents SET captured_by_source_id=NULL')
        else:
            # Freeze a valid non-minimal historical collector so an
            # implementation always choosing the minimum cannot pass by luck.
            expected = max(primary['id'], overlap['id'])
            with fixture.db.connect() as connection:
                connection.execute('UPDATE documents SET captured_by_source_id=?', (expected,))
    else:
        # Existing experimental archives can retain this historical bad state.
        with fixture.db.connect() as connection:
            connection.execute('UPDATE documents SET captured_by_source_id=NULL')
    hit = fixture.search('collectorrepair', scope='project', project_id=project, local=True)['results'][0]
    before = fixture.read(hit, start=0, end=hit['text_length'])
    entry = fixture.files(primary)[0]
    target = entry['retry_target']
    cli(fixture, *retry_args(entry, target))
    current = fixture.files(primary)[0]
    assert current['captured_by_source_id'] == expected
    assert current['published_snapshot'] == entry['published_snapshot']
    assert current['version'] == entry['version'] and current['processing_version'] == entry['processing_version']
    after = fixture.read(hit, start=0, end=hit['text_length'])
    assert after['text'] == before['text'] and after['result_sha256'] == before['result_sha256']
    assert after['sha256'] == hit['sha256'] and after['captured_by_source_id'] == expected
    original = fixture.client.post('/api/documents/original', json={'reference': hit['reference']})
    assert original.status_code == 200 and original.content == raw
    assert Path(path).read_bytes() == raw
    observe('explicit-collector-repair-' + collector_state, {'before': entry, 'after': current,
        'same_published_snapshot': True, 'old_reference_readable': True, 'expected_source_id': expected})
