"""Exact C1 legacy coverage across the Windows maintenance/ordinary roles.

Only the explicitly configured source-C1 lane splits roles. Ordinary pytest
continues to execute its original complete legacy batch.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import shutil
import tempfile
import stat
import tarfile

ROOT = Path(__file__).resolve().parents[2]
FILES = ['tests/test_005_contracts.py', 'tests/test_upload_policy.py',
         'tests/test_upload_isolation.py', 'tests/test_vibeinsight_sync.py',
         'tests/test_vibeinsight_boundaries.py', 'tests/test_cli_help.py']
ADMIN_NODE = 'tests/test_vibeinsight_sync.py::test_managed_hub_credential_restart_and_mixed_project_search'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def actor():
    import ctypes
    import csv
    import io
    assert os.name == 'nt', 'role splitting is only the explicit Windows C1 lane'
    raw = subprocess.check_output(['whoami.exe', '/user', '/fo', 'csv', '/nh'], encoding='utf-8')
    return {'pid': os.getpid(), 'sid': list(csv.reader(io.StringIO(raw)))[-1][1],
            'is_admin': bool(ctypes.windll.shell32.IsUserAnAdmin()),
            'executable': sys.executable, 'whoami_user_csv': raw}


def validate_union(expected, standard, admin):
    """No missing, duplicate, extra, skipped or failed original item may pass."""
    assert expected and len(expected) == len(set(expected)) and ADMIN_NODE in expected
    for items in (standard, admin):
        assert all(phases == {'setup': 'passed', 'call': 'passed', 'teardown': 'passed'}
                   for phases in items.values()), items
    assert set(admin) == {ADMIN_NODE}
    assert not set(standard) & set(admin)
    assert set(expected) == set(standard) | set(admin)
    return {'expected': len(expected), 'standard': len(standard), 'admin': len(admin),
            'missing': [], 'extra': [], 'overlap': [], 'status': 'passed'}


def verify_items(data, expected, *, collect=False):
    assert data['collected'] == expected and len(expected) == len(set(expected))
    phases = {}
    for event in data['reports']:
        assert event['nodeid'] in expected
        node = phases.setdefault(event['nodeid'], {})
        assert event['when'] not in node, 'duplicate phase report'
        node[event['when']] = event['outcome']
    assert phases == data['phases']
    if collect: assert phases == {}
    else:
        assert set(phases) == set(expected)
        assert all(p == {'setup': 'passed', 'call': 'passed', 'teardown': 'passed'} for p in phases.values())
    return phases


def original_manifest(directory):
    result = {}
    def scan(base):
        for path in sorted(base.iterdir()):
            info = path.lstat()
            reparse = bool(getattr(info, 'st_file_attributes', 0) & 0x400)
            if stat.S_ISLNK(info.st_mode) or reparse:
                result[path.relative_to(directory).as_posix()] = {'kind': 'link', 'target': os.readlink(path),
                    'reparse_tag': getattr(info, 'st_reparse_tag', None)}
            elif stat.S_ISDIR(info.st_mode): scan(path)
            else:
                assert stat.S_ISREG(info.st_mode), 'unexpected special legacy evidence file'
                if path == directory / 'receipt.json': continue
                result[path.relative_to(directory).as_posix()] = {'kind': 'file', 'bytes': info.st_size, 'sha256': digest(path)}
    scan(directory)
    return result


def preserve_temporary(source, output):
    """Losslessly retain files and link metadata without walking link targets."""
    manifest = original_manifest(source)
    archive = output / 'pytest-temporary.tar.gz'
    with tarfile.open(archive, 'w:gz', dereference=False) as bundle:
        for name, value in manifest.items():
            path = source / name
            member = bundle.gettarinfo(str(path), arcname=name)
            if value['kind'] == 'link':
                member.type = tarfile.SYMTYPE;member.linkname = value['target'];member.size = 0
                bundle.addfile(member)
            else:
                member.type = tarfile.REGTYPE;member.linkname = '';member.size = value['bytes']
                with path.open('rb') as stream: bundle.addfile(member, stream)
    with tarfile.open(archive, 'r:gz') as bundle:
        members = bundle.getmembers()
        assert len(members) == len(manifest) and {m.name for m in members} == set(manifest)
        for member in members:
            expected = manifest[member.name]
            if expected['kind'] == 'link': assert member.issym() and member.linkname == expected['target']
            else:
                assert member.isfile() and member.size == expected['bytes']
                with bundle.extractfile(member) as stream:
                    assert hashlib.sha256(stream.read()).hexdigest() == expected['sha256']
    write(output / 'pytest-temporary-index.json', {'files': manifest, 'archive_sha256': digest(archive),
          'scope': 'Every ended fixture file and link metadata; no link target traversal.'})


def verify_admin_originals(directory):
    receipt = json.loads((directory / 'receipt.json').read_text(encoding='utf-8'))
    assert receipt['originals'] and original_manifest(directory) == receipt['originals']
    collection = json.loads((directory / 'collection/items.json').read_text(encoding='utf-8'))
    execution = json.loads((directory / 'execution/items.json').read_text(encoding='utf-8'))
    verify_items(collection, receipt['expected'], collect=True)
    assert verify_items(execution, [ADMIN_NODE]) == receipt['phases']
    assert receipt['actor']['is_admin'] is True
    return receipt


def verify_copied_admin(directory, config_path):
    from document_formats_source_suite import bindings
    config = json.loads(config_path.read_text(encoding='utf-8'))
    bound = config['admin_legacy']
    assert directory.resolve().parent == config_path.resolve().parent
    assert digest(directory / 'receipt.json') == bound['sha256'], 'copied administrator receipt differs from the bound original'
    receipt = verify_admin_originals(directory)
    assert receipt['bindings'] == config['bindings'] == bindings()
    assert receipt['head'] == config['head'] == subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    ledgers = list((directory.parent / 'platform/attachments').glob('*/legacy-role-batch/role-ledger.json'))
    assert len(ledgers) == 1, 'one actual ordinary-account original ledger required'
    ledger = json.loads(ledgers[0].read_text(encoding='utf-8'))
    assert ledger['administrator_receipt_sha256'] == bound['sha256']
    assert ledger['expected_nodes'] == receipt['expected']
    assert ledger['admin_phases'] == receipt['phases']
    assert ledger['actor']['is_admin'] is False and ledger['actor']['sid'] != receipt['actor']['sid']
    proof = validate_union(receipt['expected'], ledger['standard_phases'], receipt['phases'])
    return {**proof, 'original_member_count': len(receipt['originals']), 'receipt_sha256': bound['sha256'],
            'ledger_sha256': digest(ledgers[0]), 'head': config['head'],
            'source_bindings_sha256': hashlib.sha256(json.dumps(config['bindings'], sort_keys=True).encode()).hexdigest(),
            'scope': 'Same bound administrator originals and exact ordinary-account original ledger; copied bytes, complete collection and all execution phases verified after child exit.'}


def pytest_child(directory, *, collect=False, admin=False):
    directory.mkdir(parents=True, exist_ok=False)
    args = [sys.executable, '-X', 'utf8', str(Path(__file__).resolve()), '--inner',
            '--output', str(directory)]
    if collect: args.append('--collect')
    if admin: args.append('--admin')
    env = {**os.environ, 'ACCEPTANCE_EVIDENCE_DIR': str(directory / 'attachments')}
    with (directory / 'stdout.log').open('wb') as out, (directory / 'stderr.log').open('wb') as err:
        p = subprocess.run(args, cwd=ROOT, env=env, stdout=out, stderr=err, timeout=180)
    write(directory / 'process.json', {'argv': args, 'returncode': p.returncode})
    assert p.returncode == 0, (directory / 'stdout.log').read_text(encoding='utf-8', errors='replace')
    return json.loads((directory / 'items.json').read_text(encoding='utf-8'))


def prepare_admin(output):
    from document_formats_source_suite import bindings
    actual = actor()
    assert actual['is_admin'], actual
    output.mkdir(parents=True, exist_ok=False)
    before = bindings()
    collection = pytest_child(output / 'collection', collect=True)
    expected = collection['collected']
    verify_items(collection, expected, collect=True)
    executed = pytest_child(output / 'execution', admin=True)
    verify_items(executed, [ADMIN_NODE])
    assert before == bindings(), 'source changed during administrator test'
    write(output / 'receipt.json', {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
          'actor': actual, 'bindings': before, 'expected': expected, 'phases': executed['phases'],
          'originals': original_manifest(output)})
    verify_admin_originals(output)


def standard_batch(directory, receipt_path, expected_sha):
    from scripts.acceptance.document_formats_source_suite import bindings
    assert digest(receipt_path) == expected_sha, 'administrator evidence changed'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    actual = actor()
    assert not actual['is_admin'] and actual['sid'] != receipt['actor']['sid']
    assert receipt['actor']['is_admin'] and receipt['actor']['executable'] == actual['executable']
    assert receipt['head'] == subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert receipt['bindings'] == bindings(), 'administrator/standard source mismatch'
    collection = pytest_child(directory / 'collection', collect=True)
    current = collection['collected']
    verify_items(collection, current, collect=True)
    assert current == receipt['expected'], 'original legacy collection changed'
    executed = pytest_child(directory / 'execution')
    verify_items(executed, [node for node in current if node != ADMIN_NODE])
    ledger = validate_union(current, executed['phases'], receipt['phases'])
    assert digest(receipt_path) == expected_sha
    write(directory / 'role-ledger.json', {**ledger, 'expected_nodes': current,
          'standard_phases': executed['phases'], 'admin_phases': receipt['phases'],
          'administrator_receipt_sha256': expected_sha, 'actor': actual})
    return ledger


def inner(output, collect, admin):
    import pytest
    data = {'collected': [], 'phases': {}, 'reports': []}
    class Items:
        def pytest_collection_finish(self, session):
            data['collected'] = [item.nodeid for item in session.items]
            write(output / 'items.json', data)
        def pytest_runtest_logreport(self, report):
            data['reports'].append({'nodeid': report.nodeid, 'when': report.when, 'outcome': report.outcome})
            previous = data['phases'].setdefault(report.nodeid, {})
            duplicate = report.when in previous
            if not duplicate: previous[report.when] = report.outcome
            write(output / 'items.json', data)
            assert not duplicate, 'duplicate actual pytest phase report'
    # Test repositories must be outside this checkout's Git root, matching the
    # original nested pytest default. Otherwise project-path discovery would
    # resolve the synthetic duplicate-name projects as the SMM checkout.
    temporary = Path(tempfile.mkdtemp(prefix='smm-008-legacy-'))
    write(output / 'temporary-custody.json', {'path': str(temporary), 'status': 'owned_fixture_live'})
    args = ['-q', '--junitxml=' + str(output / 'junit.xml'), '--basetemp=' + str(temporary / 'pytest-tmp')]
    if collect: args += ['--collect-only', *FILES]
    elif admin: args += [ADMIN_NODE]
    else: args += [*FILES, '--deselect=' + ADMIN_NODE]
    try: code = pytest.main(args, plugins=[Items()])
    finally:
        preserve_temporary(temporary, output)
        shutil.rmtree(temporary)
        write(output / 'temporary-custody.json', {'path': str(temporary), 'status': 'all_originals_archived_and_verified_then_owned_fixture_removed'})
    raise SystemExit(code)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare-admin', action='store_true')
    p.add_argument('--inner', action='store_true')
    p.add_argument('--verify-admin-originals', action='store_true')
    p.add_argument('--collect', action='store_true')
    p.add_argument('--admin', action='store_true')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--verification-receipt', type=Path)
    p.add_argument('--target-config', type=Path)
    a = p.parse_args()
    if a.prepare_admin: prepare_admin(a.output)
    elif a.verify_admin_originals:
        proof = verify_copied_admin(a.output, a.target_config)
        assert a.verification_receipt is not None and not a.verification_receipt.resolve().is_relative_to(a.output.resolve())
        write(a.verification_receipt, proof)
    else: inner(a.output, a.collect, a.admin)
