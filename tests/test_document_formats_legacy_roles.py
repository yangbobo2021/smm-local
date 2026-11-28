"""C1 role ledger must account for every original case and all three phases."""
from copy import deepcopy
import json
import os
import subprocess
import tarfile
import pytest
from scripts.acceptance.document_formats_legacy_roles import ADMIN_NODE, validate_union, verify_items, original_manifest, preserve_temporary, verify_admin_originals, verify_copied_admin, digest, write


def proof():
    expected = ['tests/test_005_contracts.py::test_policy', ADMIN_NODE]
    phases = {'setup': 'passed', 'call': 'passed', 'teardown': 'passed'}
    return expected, {expected[0]: dict(phases)}, {ADMIN_NODE: dict(phases)}


def test_exact_legacy_role_union_accepts_complete_original_cases():
    assert validate_union(*proof()) == {'expected': 2, 'standard': 1, 'admin': 1,
        'missing': [], 'extra': [], 'overlap': [], 'status': 'passed'}


@pytest.mark.parametrize('fault', ['missing', 'extra', 'overlap', 'skip', 'setup', 'call', 'teardown',
                                  'absent-call', 'duplicate-collection', 'wrong-admin'])
def test_legacy_role_union_rejects_incomplete_or_incorrect_receipts(fault):
    expected, standard, admin = deepcopy(proof())
    node = expected[0]
    if fault == 'missing': standard.clear()
    elif fault == 'extra': standard['tests/extra.py::test_extra'] = dict(standard[node])
    elif fault == 'overlap': standard[ADMIN_NODE] = dict(admin[ADMIN_NODE])
    elif fault == 'skip': standard[node]['call'] = 'skipped'
    elif fault in {'setup', 'call', 'teardown'}: standard[node][fault] = 'failed'
    elif fault == 'absent-call': del standard[node]['call']
    elif fault == 'duplicate-collection': expected.append(expected[0])
    elif fault == 'wrong-admin': admin['tests/other.py::test_other'] = admin.pop(ADMIN_NODE)
    with pytest.raises(AssertionError): validate_union(expected, standard, admin)


@pytest.mark.parametrize('fault', ['duplicate-item', 'duplicate-phase', 'fail-then-pass', 'missing-phase', 'wrong-order'])
def test_actual_report_ledger_rejects_duplicate_or_lost_history(fault):
    nodes = ['tests/legacy.py::test_first', 'tests/legacy.py::test_second']
    reports = [{'nodeid': node, 'when': phase, 'outcome': 'passed'}
               for node in nodes for phase in ('setup', 'call', 'teardown')]
    phases = {node: {'setup': 'passed', 'call': 'passed', 'teardown': 'passed'} for node in nodes}
    data = {'collected': list(nodes), 'reports': reports, 'phases': phases}
    verify_items(data, nodes)
    if fault == 'duplicate-item': data['collected'].append(nodes[0])
    elif fault == 'duplicate-phase': reports.append(dict(reports[1]))
    elif fault == 'fail-then-pass': reports.insert(1, {**reports[1], 'outcome': 'failed'})
    elif fault == 'missing-phase': reports.pop()
    else: data['collected'].reverse()
    with pytest.raises(AssertionError): verify_items(data, nodes)


def test_original_manifest_detects_missing_changed_and_extra_admin_bytes(tmp_path):
    execution = tmp_path / 'execution';execution.mkdir()
    raw = execution / 'stdout.log';raw.write_bytes(b'actual original\r\n')
    manifest = original_manifest(tmp_path)
    raw.write_bytes(b'changed original\r\n')
    assert original_manifest(tmp_path) != manifest
    raw.unlink()
    assert original_manifest(tmp_path) != manifest
    raw.write_bytes(b'actual original\r\n')
    assert original_manifest(tmp_path) == manifest
    (execution / 'unaccounted.json').write_text('{}')
    assert original_manifest(tmp_path) != manifest


def test_fixture_archive_retains_link_metadata_without_reading_its_target(tmp_path, monkeypatch):
    source = tmp_path / 'source';source.mkdir()
    output = tmp_path / 'output';output.mkdir()
    external = tmp_path / 'external';external.mkdir()
    secret = external / 'outside.txt';secret.write_bytes(b'outside fixture must not be read')
    (source / 'own.txt').write_bytes(b'owned fixture original')
    link = source / 'pytest-current'
    if os.name == 'nt':
        result = subprocess.run(['cmd.exe', '/c', 'mklink', '/J', str(link), str(external)], capture_output=True)
        assert result.returncode == 0, result.stdout + result.stderr
    else: link.symlink_to(external, target_is_directory=True)
    native = type(secret).open;reads = []
    def observed(path, *args, **kwargs):
        if path == secret:
            reads.append(str(path));raise AssertionError('link target read')
        return native(path, *args, **kwargs)
    monkeypatch.setattr(type(secret), 'open', observed)
    preserve_temporary(source, output)
    manifest = json.loads((output / 'pytest-temporary-index.json').read_text())['files']
    assert set(manifest) == {'own.txt', 'pytest-current'}
    assert manifest['pytest-current']['kind'] == 'link'
    assert manifest['pytest-current']['target'] == os.readlink(link)
    with tarfile.open(output / 'pytest-temporary.tar.gz') as archive:
        assert archive.getmember('pytest-current').issym()
        assert archive.getmember('pytest-current').linkname == os.readlink(link)
        assert archive.extractfile('own.txt').read() == b'owned fixture original'
    assert reads == []


def test_other_self_consistent_admin_copy_cannot_replace_the_bound_receipt(tmp_path, monkeypatch):
    from pathlib import Path
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts/acceptance'))
    original = tmp_path / 'administrator-legacy-originals';original.mkdir()
    expected, standard, admin = proof()
    write(original / 'collection/items.json', {'collected': expected, 'phases': {}, 'reports': []})
    write(original / 'execution/items.json', {'collected': [ADMIN_NODE], 'phases': admin,
        'reports': [{'nodeid': ADMIN_NODE, 'when': phase, 'outcome': 'passed'} for phase in ('setup', 'call', 'teardown')]})
    receipt = {'expected': expected, 'phases': admin, 'actor': {'is_admin': True},
               'head': 'synthetic-previous-receipt', 'originals': original_manifest(original)}
    write(original / 'receipt.json', receipt)
    bound = digest(original / 'receipt.json')
    receipt['head'] = 'synthetic-other-self-consistent-receipt'
    write(original / 'receipt.json', receipt)
    verify_admin_originals(original)  # Its own raw manifest remains valid.
    write(tmp_path / 'target.json', {'admin_legacy': {'sha256': bound}})
    with pytest.raises(AssertionError, match='differs from the bound original'):
        verify_copied_admin(original, tmp_path / 'target.json')
