"""Prepare fresh, separate installed Local/Hub products for 008 E/H probes.

The controller may use the checkout. Products use their exact wheels, locked
runtime dependencies, isolated Python and non-source working directories.
Python 3.11 minimum acceptance remains a separate driver and obligation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]


def prepare(work, materials, uv, python, browser=None):
    work = work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    records = []

    def run(label, argv):
        argv = list(map(str, argv))
        # Stream originals to durable files even if preparation times out.
        with (work / (label + '.stdout')).open('wb') as stdout, (work / (label + '.stderr')).open('wb') as stderr:
            try:
                process = subprocess.run(argv, cwd=ROOT, stdout=stdout, stderr=stderr, timeout=300)
                code = process.returncode
            except subprocess.TimeoutExpired:
                records.append({'label': label, 'argv': argv, 'timeout_seconds': 300})
                save(work / 'prepare-commands.json', records)
                raise
        records.append({'label': label, 'argv': argv, 'exit_code': code,
                        'stdout_sha256': sha(work / (label + '.stdout')),
                        'stderr_sha256': sha(work / (label + '.stderr'))})
        save(work / 'prepare-commands.json', records)
        assert code == 0, (label, code, str(work / (label + '.stderr')))

    run('packages', [python, '-I', ROOT / 'scripts/acceptance/hub_documents_packages.py',
                     '--uv', uv, '--output', work / 'packages'])
    requirements = work / 'documents-locked.txt'
    run('locked-export', [uv, 'export', '--frozen', '--extra', 'documents', '--no-dev',
                          '--no-emit-project', '-o', requirements])
    config = {'materials': str(materials.resolve()), 'expected_platform': sys.platform,
              'browser_checks': True, 'browser_uploads': True, 'read_guards': True,
              'source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'source_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT)),
              'purpose': 'Installed 008 foreground E preparation; execution and service/X evidence are separate'}
    if browser is not None:
        assert browser.is_absolute() and browser.is_file()
        config['browser'] = str(browser)
    run('base-python', [python, '-I', '-X', 'utf8', '-c',
        'import json,sys;print(json.dumps({"executable":sys.executable,"base_executable":getattr(sys,"_base_executable",sys.executable),"base_prefix":sys.base_prefix,"version":sys.version}))'])
    base = json.loads((work / 'base-python.stdout').read_text(encoding='utf-8'))
    material_data = json.loads(materials.read_text(encoding='utf-8'))
    config.update(controller_python=str(Path(sys.executable).absolute()), base_python=base,
        read_paths=sorted({str(ROOT / '.venv'), str(Path(base['base_executable']).parent),
            str(Path(material_data['ocr_executable']).parent.parent),
            str(Path(material_data['ocr_data_dir'])), str(Path(material_data['font']['path']).parent),
            *([str(browser.parent)] if browser else [])}))
    for owner in ('local', 'hub'):
        prefix = work / 'packages' / (owner + '-env')
        executable = prefix / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        wheel = next((work / 'packages/wheels').glob('smm_' + owner + '-*.whl'))
        run(owner + '-locked-sync', [uv, 'pip', 'sync', '--python', executable,
                                    '--require-hashes', requirements])
        run(owner + '-exact-wheel', [uv, 'pip', 'install', '--python', executable, '--no-deps', wheel])
        with ZipFile(wheel) as archive:
            assert archive.testzip() is None
        config.update({owner + '_python': str(executable), owner + '_wheel': str(wheel),
                       owner + '_wheel_sha256': sha(wheel),
                       owner + '_expected': str(work / 'packages' / (owner + '-expected.json'))})
    save(work / 'target.json', config)
    return config


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--materials', type=Path, required=True)
    parser.add_argument('--uv', default=shutil.which('uv'))
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--browser', type=Path)
    args = parser.parse_args()
    assert args.uv, 'prepare uv before installing the test products'
    prepare(args.work, args.materials, args.uv, args.python, args.browser)
    print(json.dumps({'status': 'prepared', 'target': str(args.work.resolve() / 'target.json')}))


if __name__ == '__main__':
    main()
