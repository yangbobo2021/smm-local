"""Collect task-owned minimum-install receipts; keep environments off artifacts."""
import argparse
import json
import os
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--work', type=Path, required=True)
parser.add_argument('--materials', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--context', type=Path, required=True)
args = parser.parse_args()
if args.output.resolve().is_relative_to(args.work.resolve()):
    raise ValueError('evidence destination must be outside the source work directory')
args.output.mkdir(parents=True, exist_ok=False)
for source in args.work.rglob('*'):
    if not source.is_file() or source.is_symlink():
        continue
    relative = source.relative_to(args.work)
    # All actual inputs, truth, protocol raw responses, downloads and JUnit live
    # under attachments. Pytest temp databases are retained only on the runner.
    if any(part.endswith('-env') or part in {'tmp', '.pytest_cache', '__pycache__'} for part in relative.parts):
        continue
    if source.suffix not in {'.json', '.xml', '.stdout', '.stderr', '.whl', '.txt', '.gz', '.pdf', '.docx', '.xlsx', '.bin', '.log'}:
        continue
    target = args.output / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
if args.materials.is_file():
    shutil.copyfile(args.materials, args.output / 'materials.json')
materials_work = args.materials.with_suffix('')
logs = materials_work / 'logs'
for source in logs.rglob('*'):
    if not source.is_file() or source.is_symlink():
        continue
    target = args.output / 'materials-logs' / source.relative_to(logs)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
# This receipt also survives an early preparation failure before target.json or
# materials.json exists. It reports collection, never a business pass.
(args.output / 'collection.json').write_text(json.dumps({
    'status': 'collected', 'work_exists': args.work.is_dir(),
    'materials_manifest_exists': args.materials.is_file(),
    'materials_logs_exist': logs.is_dir(),
    'files': sorted(p.relative_to(args.output).as_posix() for p in args.output.rglob('*') if p.is_file()),
}, indent=2), encoding='utf-8')
context = {'run_id': os.environ['GITHUB_RUN_ID'], 'job_key': 'minimum-' + os.environ['RUNNER_OS'],
           'commit': os.environ['GITHUB_SHA'],
           'artifact_name': '008-minimum-' + os.environ['RUNNER_OS'] + '-' + os.environ['GITHUB_RUN_ID'] + '-' + os.environ['GITHUB_RUN_ATTEMPT']}
args.context.write_text(json.dumps(context, indent=2), encoding='utf-8')
