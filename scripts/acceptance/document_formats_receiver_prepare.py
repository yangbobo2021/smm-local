"""Prepare a locked base-only Hub for genuine cross-OS result consumption."""
from __future__ import annotations

import argparse
from email.parser import BytesParser
import hashlib
from importlib import metadata
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from zipfile import ZipFile

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[2]


def locked_base_requirements(wheel, exported):
    with ZipFile(wheel) as archive:
        info = BytesParser().parsebytes(archive.read(next(n for n in archive.namelist() if n.endswith('/METADATA'))))
    env = {**default_environment(), 'extra': ''}
    pending = [Requirement(value) for value in info.get_all('Requires-Dist', [])]
    selected, graph = set(), []
    while pending:
        requirement = pending.pop()
        if requirement.marker and not requirement.marker.evaluate(env):
            continue
        name = canonicalize_name(requirement.name)
        distribution = metadata.distribution(name)
        assert distribution.version in requirement.specifier, (name, distribution.version, str(requirement))
        graph.append({'requirement': str(requirement), 'actual_frozen_version': distribution.version})
        if name in selected:
            continue
        selected.add(name)
        pending.extend(Requirement(value) for value in distribution.requires or [])
    blocks = re.split(r'(?m)(?=^[A-Za-z0-9][A-Za-z0-9_.-]*==)', exported)
    chosen, found = [], set()
    for block in blocks:
        match = re.match(r'^([A-Za-z0-9_.-]+)==', block)
        if match and canonicalize_name(match[1]) in selected:
            assert '--hash=sha256:' in block
            found.add(canonicalize_name(match[1]))
            chosen.append(block)
    assert found == selected, (found, selected)
    assert not selected & {'pillow', 'pdfplumber', 'pdfminer-six', 'pypdfium2', 'defusedxml', 'psutil', 'mcp'}
    return ''.join(chosen), graph


def prepare(work, uv):
    work.mkdir(parents=True, exist_ok=False)
    commands = []

    def run(label, argv):
        argv = list(map(str, argv))
        with (work / (label + '.stdout')).open('wb') as stdout, (work / (label + '.stderr')).open('wb') as stderr:
            result = subprocess.run(argv, cwd=ROOT, stdout=stdout, stderr=stderr, timeout=300)
        commands.append({'label': label, 'argv': argv, 'exit_code': result.returncode})
        (work / 'commands.json').write_text(json.dumps(commands, indent=2), encoding='utf-8')
        assert result.returncode == 0, (label, result.returncode)

    run('packages', [sys.executable, '-I', ROOT / 'scripts/acceptance/hub_documents_packages.py', '--uv', uv, '--output', work / 'packages'])
    exported = work / 'all-base-locked.txt'
    run('locked-export', [uv, 'export', '--frozen', '--no-dev', '--no-emit-project', '-o', exported])
    wheel = next((work / 'packages/wheels').glob('smm_hub-*.whl'))
    locked, graph = locked_base_requirements(wheel, exported.read_text(encoding='utf-8'))
    requirements = work / 'hub-base-locked.txt'
    requirements.write_text(locked, encoding='utf-8')
    (work / 'base-dependency-closure.json').write_text(json.dumps(graph, indent=2), encoding='utf-8')
    prefix = work / 'packages/hub-env'
    python = prefix / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    run('locked-sync', [uv, 'pip', 'sync', '--python', python, '--require-hashes', requirements])
    run('exact-hub-wheel', [uv, 'pip', 'install', '--python', python, '--no-deps', wheel])
    run('actual-base-prefix', [python, '-I', '-X', 'utf8', '-c',
        'import json,sys;print(json.dumps({"base_executable":sys._base_executable,"version":sys.version}))'])
    base = json.loads((work / 'actual-base-prefix.stdout').read_text(encoding='utf-8'))
    config = {'expected_platform': sys.platform, 'hub_python': str(python), 'hub_wheel': str(wheel),
              'hub_wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
              'hub_expected': str(work / 'packages/hub-expected.json'),
              'read_paths': [str(ROOT / '.venv'), str(Path(base['base_executable']).parent)],
              'source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'purpose': 'Base-only isolated X receiver; preparation does not assert business pass'}
    (work / 'target.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    return config


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--uv', default=shutil.which('uv'))
    args = parser.parse_args()
    assert args.uv
    prepare(args.work.resolve(), args.uv)
