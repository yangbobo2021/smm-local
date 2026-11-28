"""Preserve X originals and install receipts, excluding replaceable programs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--work', type=Path, required=True)
parser.add_argument('--materials', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--context', type=Path, required=True)
parser.add_argument('--job-key', required=True)
args = parser.parse_args()
assert not args.output.resolve().is_relative_to(args.work.resolve())
args.output.mkdir(parents=True, exist_ok=False)
index = {}
links = []


def copy(source, relative):
    state = source.lstat()
    if source.is_symlink() or getattr(state, 'st_file_attributes', 0) & 0x400:
        links.append({'path': relative.as_posix(), 'target': os.readlink(source)})
        return
    assert stat.S_ISREG(state.st_mode)
    raw = source.read_bytes()
    target = args.output / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    assert target.read_bytes() == raw
    index[relative.as_posix()] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def walk(directory, prefix=Path()):
    if not directory.exists():
        return
    for source in sorted(directory.iterdir()):
        relative = prefix / source.name
        if source.name.endswith('-env') or source.name in {'__pycache__', '.pytest_cache'}:
            continue
        state = source.lstat()
        if source.is_symlink() or getattr(state, 'st_file_attributes', 0) & 0x400:
            links.append({'path': relative.as_posix(), 'target': os.readlink(source)})
        elif stat.S_ISDIR(state.st_mode):
            walk(source, relative)
        else:
            copy(source, relative)


walk(args.work)
if args.materials.is_file():
    copy(args.materials, Path('materials.json'))
logs = args.materials.with_suffix('') / 'logs'
if logs.is_dir():
    walk(logs, Path('materials-logs'))
context = {'run_id': os.environ['GITHUB_RUN_ID'], 'job_key': args.job_key,
           'commit': os.environ['GITHUB_SHA'],
           'artifact_name': '008-' + args.job_key + '-' + os.environ['GITHUB_RUN_ID'] + '-' + os.environ['GITHUB_RUN_ATTEMPT']}
(args.output / 'collection.json').write_text(json.dumps({'status': 'collected', 'context': context,
    'scope': 'Original business state, inputs/truth/protocol/downloads/guards and exact wheels/install receipts; replaceable dependency environments excluded. Collection is never business pass.',
    'files': index, 'links_metadata_only': links}, indent=2), encoding='utf-8')
args.context.write_text(json.dumps(context, indent=2), encoding='utf-8')
