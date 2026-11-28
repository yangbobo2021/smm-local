"""Actual collector invocation retains early setup failure bytes."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def collect(tmp_path, prepared):
    work = tmp_path / 'minimum'
    materials = tmp_path / 'minimum-materials.json'
    logs = tmp_path / 'minimum-materials' / 'logs'
    logs.mkdir(parents=True)
    raw = b'original preparation error\r\n\xff\x00'
    (logs / 'resolve-ocr.stderr').write_bytes(raw)
    if prepared:
        work.mkdir()
        (work / 'failure.json').write_text('{"status":"failed","cause":"fixture"}')
        materials.write_text('{"ocr":"fixture"}')
        downloads = work / 'platform' / 'attachments' / 'downloads'
        downloads.mkdir(parents=True)
        (downloads / 'source.bin').write_bytes(b'exact synthetic original bytes')
    output = tmp_path / 'evidence'
    context = tmp_path / 'context.json'
    env = {**os.environ, 'GITHUB_RUN_ID': '123', 'GITHUB_SHA': 'a' * 40,
           'GITHUB_RUN_ATTEMPT': '1', 'RUNNER_OS': 'Windows'}
    p = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/acceptance/document_formats_completion_evidence.py'),
                        '--work', str(work), '--materials', str(materials), '--output', str(output),
                        '--context', str(context)], env=env, capture_output=True, timeout=15)
    assert p.returncode == 0, p.stderr
    assert (output / 'materials-logs' / 'resolve-ocr.stderr').read_bytes() == raw
    assert json.loads(context.read_text()) == {'run_id': '123', 'job_key': 'minimum-Windows',
        'commit': 'a' * 40, 'artifact_name': '008-minimum-Windows-123-1'}
    receipt = json.loads((output / 'collection.json').read_text())
    assert receipt['status'] == 'collected' and receipt['work_exists'] is prepared
    assert receipt['materials_manifest_exists'] is prepared and receipt['materials_logs_exist'] is True
    return output


def test_minimum_collector_retains_failure_before_any_target_or_material_manifest(tmp_path):
    output = collect(tmp_path, False)
    assert {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()} == {
        'collection.json', 'materials-logs/resolve-ocr.stderr'}


def test_minimum_collector_keeps_business_failure_and_exact_download_with_setup_logs(tmp_path):
    output = collect(tmp_path, True)
    assert json.loads((output / 'failure.json').read_text())['status'] == 'failed'
    assert (output / 'platform/attachments/downloads/source.bin').read_bytes() == b'exact synthetic original bytes'
    assert json.loads((output / 'materials.json').read_text()) == {'ocr': 'fixture'}
