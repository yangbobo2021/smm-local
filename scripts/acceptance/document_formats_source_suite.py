"""Opt-in C1 source regression with real prepared OCR and browser assets.

This is component/source acceptance, separate from installed E/H/X. Each
pytest item receives its own raw-evidence directory to prevent overwrites.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import tarfile
import traceback

ROOT = Path(__file__).resolve().parents[2]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def bindings():
    paths = [p for directory in ('src', 'tests', 'scripts/acceptance') for p in (ROOT / directory).rglob('*')
             if p.is_file() and p.suffix in {'.py', '.html', '.ps1'} and '__pycache__' not in p.parts]
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def prepare(work, materials, browsers, test_files=None):
    work = work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    assert not (work / 'target.json').exists(), 'target inputs already bound'
    actual_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    config = {'purpose': 'C1 source only; not installed E/H/X', 'head': actual_head,
              'expected_system': platform.system(), 'materials': str(materials.resolve()),
              'browsers': str(browsers.resolve()), 'bindings': bindings(), 'test_files': test_files or [],
              'selection': 'explicit orchestration smoke subset' if test_files else 'all document source tests',
              'read_paths': [str(ROOT / '.venv'), str(materials.resolve().with_suffix('')),
                             str(browsers.resolve()), str(Path(getattr(sys, '_base_executable', sys.executable)).parent)]}
    write(work / 'target.json', config)


def run(config_path, output):
    output.mkdir(parents=True, exist_ok=False)
    try:
        return run_checked(config_path, output)
    except BaseException:
        write(output / 'failure.json', {'traceback': traceback.format_exc()})
        raise


def run_checked(config_path, output):
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    assert config['expected_system'] == platform.system()
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha for name, sha in config['bindings'].items())
    sys.path.insert(0, str(ROOT / 'scripts/acceptance'))
    from hub_documents_platform import Probe
    actor = Probe.actor()
    if os.name == 'nt':
        import csv
        import io
        user = subprocess.check_output(['whoami.exe', '/user', '/fo', 'csv', '/nh'], text=True, encoding='utf-8')
        groups = subprocess.check_output(['whoami.exe', '/groups', '/fo', 'csv', '/nh'], text=True, encoding='utf-8')
        actor['sid'] = list(csv.reader(io.StringIO(user)))[-1][1]
        assert actor['sid'].startswith('S-1-5-21-') and 'S-1-5-32-544' not in groups
        actor['administrator_group'] = False
        (output / 'actual-user.csv').write_text(user, encoding='utf-8')
        (output / 'actual-groups.csv').write_text(groups, encoding='utf-8')
    write(output / 'controller-identity.json', actor)
    write(output / 'source-bindings.json', config)
    materials = json.loads(Path(config['materials']).read_text(encoding='utf-8'))
    empty = output.parent / 'empty-agent'
    empty.mkdir(exist_ok=True)
    env = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8', 'SMM_CODEX_ROOT': str(empty),
           'SMM_CLAUDE_ROOT': str(empty), 'SMM_008_OCR_EXECUTABLE': materials['ocr_executable'],
           'SMM_008_OCR_DATA': materials['ocr_data_dir'], 'SMM_008_FONT': materials['font']['path'],
           'PLAYWRIGHT_BROWSERS_PATH': config['browsers']}
    argv = [sys.executable, '-I', '-X', 'utf8', str(Path(__file__).resolve()), '--inner',
            '--target-config', str(config_path.resolve()), '--output', str(output.resolve())]
    try:
        with (output / 'run.stdout').open('wb') as stdout, (output / 'run.stderr').open('wb') as stderr:
            p = subprocess.run(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, timeout=6600)
        unchanged = all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha for name, sha in config['bindings'].items())
        result = {'status': 'passed' if p.returncode == 0 and unchanged else 'failed', 'exit_code': p.returncode,
                  'head': config['head'], 'actor': actor, 'source_unchanged': unchanged, 'argv': argv,
                  'scope': 'C1 source tests only; skips and E/H/X obligations remain separately accounted'}
        write(output / 'result.json', result)
        assert result['status'] == 'passed', result
    except BaseException:
        write(output / 'failure.json', {'traceback': traceback.format_exc()})
        raise


def inner(output, config_path):
    import pytest
    mapping = {}

    class PerItem:
        @pytest.hookimpl(hookwrapper=True)
        def pytest_runtest_protocol(self, item, nextitem):
            key = hashlib.sha256(item.nodeid.encode()).hexdigest()[:24]
            assert key not in mapping
            mapping[key] = item.nodeid
            directory = output / 'attachments' / key
            directory.mkdir(parents=True, exist_ok=False)
            old = os.environ.get('ACCEPTANCE_EVIDENCE_DIR')
            os.environ['ACCEPTANCE_EVIDENCE_DIR'] = str(directory)
            write(output / 'case-map.json', mapping)
            try:
                yield
            finally:
                if old is None:
                    os.environ.pop('ACCEPTANCE_EVIDENCE_DIR', None)
                else:
                    os.environ['ACCEPTANCE_EVIDENCE_DIR'] = old

    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    selected = ([ROOT / p for p in config['test_files']] if config['test_files'] else
                sorted({*ROOT.joinpath('tests').glob('test_document*.py'), *ROOT.joinpath('tests').glob('test_hub_documents*.py')}))
    assert all(p.resolve().is_relative_to((ROOT / 'tests').resolve()) and p.is_file() and p.suffix == '.py' for p in selected)
    args = ['-q', '--tb=short', '--junitxml', str(output / 'junit.xml'), '--basetemp', str(output.parent / 'pytest-tmp'),
            *[str(p) for p in selected]]
    write(output / 'pytest-selection.json', {'argv': args, 'files': [p.relative_to(ROOT).as_posix() for p in selected]})
    raise SystemExit(pytest.main(args, plugins=[PerItem()]))


def collect(work, materials, output, context_path):
    import shutil
    output.mkdir(parents=True, exist_ok=False)
    source = work
    index = {}
    # Raw negative-test inputs may deliberately be invalid Word/PDF documents.
    # Keep the complete bytes in a lossless archive. Semantic checks belong to
    # their test case, never to a blanket assumption based on file extension.
    archive = output / 'source-suite-raw.tar.gz'
    def digest(path):
        value = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                value.update(block)
        return value.hexdigest()

    def is_reparse(info):
        return bool(getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400))

    def entries(directory):
        # Path.rglob may descend into Windows junctions before the caller sees
        # their lstat. Classify each entry before scheduling recursion.
        for path in sorted(directory.iterdir()):
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or is_reparse(info):
                yield path, info
            elif stat.S_ISDIR(info.st_mode):
                yield from entries(path)
            else:
                yield path, info

    root_info = source.lstat()
    assert stat.S_ISDIR(root_info.st_mode) and not is_reparse(root_info) and not source.is_symlink()

    with tarfile.open(archive, 'w:gz', dereference=False) as bundle:
        for path, info in entries(source):
            mode = info.st_mode
            name = path.relative_to(source).as_posix()
            member = bundle.gettarinfo(str(path), arcname=name)
            if stat.S_ISLNK(mode) or is_reparse(info):
                # Preserve hostile test links as metadata, never read targets.
                kind = 'junction' if stat.S_ISDIR(mode) else 'symlink'
                index[name] = {'kind': kind, 'target': os.readlink(path)}
                if is_reparse(info):
                    index[name]['reparse_tag'] = info.st_reparse_tag
                member.type = tarfile.SYMTYPE
                member.linkname = index[name]['target']
                member.size = 0
                bundle.addfile(member)
            elif stat.S_ISREG(mode):
                index[name] = {'kind': 'file', 'bytes': path.stat().st_size, 'sha256': digest(path)}
                # Store bytes independently even if gettarinfo detected a hardlink.
                member.type = tarfile.REGTYPE
                member.linkname = ''
                member.size = index[name]['bytes']
                with path.open('rb') as stream:
                    bundle.addfile(member, stream)
            elif stat.S_ISFIFO(mode):
                index[name] = {'kind': 'fifo'}
                bundle.addfile(member)
            else:
                raise ValueError('unsupported raw evidence file type: ' + name)
    write(output / 'raw-index.json', index)
    with tarfile.open(archive, 'r:gz') as bundle:
        members = bundle.getmembers()
        assert len(members) == len(index) and {m.name for m in members} == set(index)
        for member in members:
            expected = index[member.name]
            if expected['kind'] == 'file':
                assert member.isfile() and member.size == expected['bytes']
                value = hashlib.sha256()
                with bundle.extractfile(member) as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b''):
                        value.update(block)
                assert value.hexdigest() == expected['sha256']
            elif expected['kind'] in {'symlink', 'junction'}:
                assert member.issym() and member.linkname == expected['target']
            else:
                assert expected['kind'] == 'fifo' and member.isfifo()
    logs = materials.with_suffix('') / 'logs'
    for directory, prefix in ((work, 'controller'), (logs, 'materials-logs')):
        for path in sorted(directory.glob('*')):
            if path.is_file() and path.suffix in {'.json', '.stdout', '.stderr', '.log'}:
                target = output / prefix / path.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
    if materials.is_file():
        shutil.copyfile(materials, output / 'materials.json')
    context = {'run_id': os.environ['GITHUB_RUN_ID'], 'job_key': 'source-' + os.environ['RUNNER_OS'],
               'commit': os.environ['GITHUB_SHA'],
               'artifact_name': '008-source-' + os.environ['RUNNER_OS'] + '-' + os.environ['GITHUB_RUN_ID'] + '-' + os.environ['GITHUB_RUN_ATTEMPT']}
    write(context_path, context)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare', action='store_true')
    p.add_argument('--collect', action='store_true')
    p.add_argument('--inner', action='store_true')
    p.add_argument('--materials', type=Path)
    p.add_argument('--browsers', type=Path)
    p.add_argument('--work', type=Path)
    p.add_argument('--target-config', type=Path)
    p.add_argument('--context', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--test-file', action='append')
    a = p.parse_args()
    if a.prepare:
        prepare(a.work, a.materials, a.browsers, a.test_file)
    elif a.collect:
        collect(a.work, a.materials, a.output, a.context)
    elif a.inner:
        inner(a.output, a.target_config)
    else:
        run(a.target_config, a.output)


if __name__ == '__main__':
    main()
