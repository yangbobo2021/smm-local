"""Publication immutability must not assume corpus relevance stays constant."""
from copy import deepcopy
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/acceptance'))
from document_formats_installed_lifecycle import unchanged_publication


def test_new_corpus_score_preserves_all_publication_checks():
    before = {'reference': 'old-reference', 'hit': {'origin': {'document_id': 'one'},
        'version': 1, 'processing_version': 2, 'bm25_score': 3.3650060368620696,
        'reference': 'issued-before', 'project_ids': [5], 'sha256': 'saved'},
        'text': {'text': 'independent truth', 'sha256': 'saved'},
        'tables': [{'cells': [{'text': 'cell', 'row': 1}]}], 'info': {'bytes': 123, 'available': True}}
    after = deepcopy(before)
    after['hit'].update(bm25_score=3.369632265636257, reference='issued-after')
    unchanged_publication(after, before)
    # Never erase the whole hit, stable identity, qualification, body or table.
    for section, key, wrong in [('hit', 'origin', {'document_id': 'other'}),
        ('hit', 'version', 2), ('hit', 'processing_version', 3), ('hit', 'sha256', 'changed'),
        ('hit', 'project_ids', []), ('text', 'text', 'changed'), ('info', 'bytes', 124)]:
        value = deepcopy(after);value[section][key] = wrong
        with pytest.raises(AssertionError):unchanged_publication(value, before)
    value = deepcopy(after);value['tables'][0]['cells'][0]['row'] = 2
    with pytest.raises(AssertionError):unchanged_publication(value, before)
    for wrong in (float('nan'), float('inf'), '3.3', True):
        value = deepcopy(after);value['hit']['bm25_score'] = wrong
        with pytest.raises(AssertionError):unchanged_publication(value, before)
    value = deepcopy(after);value['reference'] = 'different-old-reference'
    with pytest.raises(AssertionError):unchanged_publication(value, before)
