"""Raw C1 custody includes pytest temporaries and pre-business failures."""
import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess
import tarfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/acceptance'))
import document_formats_source_suite as suite


def test_source_collector_preserves_temporary_invalid_inputs_and_outer_logs(tmp_path, monkeypatch):
    work = tmp_path / 'work'
    files = {'platform/run.stdout': b'6 passed\n', 'pytest-tmp/case/a.docx': b'not a ZIP',
             'pytest-tmp/case/leading-bom.json': b'\xef\xbb\xbf{"valid":true}',
             'logs/sync.stderr': b'preparation failure before pytest\n'}
    for name, raw in files.items():
        path = work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    monkeypatch.setenv('GITHUB_RUN_ID', 'local-custody-control')
    monkeypatch.setenv('GITHUB_SHA', 'not-an-actual-ci-run')
    monkeypatch.setenv('RUNNER_OS', 'local-control')
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT', '1')
    output = tmp_path / 'evidence'
    suite.collect(work, tmp_path / 'missing-materials.json', output, tmp_path / 'context.json')
    index = json.loads((output / 'raw-index.json').read_bytes())
    assert set(index) == set(files)
    with tarfile.open(output / 'source-suite-raw.tar.gz') as archive:
        for name, raw in files.items():
            assert archive.extractfile(name).read() == raw
            assert index[name] == {'kind': 'file', 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


@pytest.mark.skipif(os.name == 'nt', reason='Windows junction/link paths covered in actual Windows source suite')
def test_source_collector_records_links_without_opening_their_targets(tmp_path, monkeypatch):
    work = tmp_path / 'work'
    work.mkdir()
    # Missing external target must remain a link, not be followed or omitted.
    link = work / 'outside-link'
    target = tmp_path / 'not-present'
    link.symlink_to(target)
    fifo = work / 'test-fifo'
    os.mkfifo(fifo)
    for name, value in {'GITHUB_RUN_ID': 'local-link-control', 'GITHUB_SHA': 'not-ci',
                        'RUNNER_OS': 'local', 'GITHUB_RUN_ATTEMPT': '1'}.items():
        monkeypatch.setenv(name, value)
    output = tmp_path / 'evidence'
    suite.collect(work, tmp_path / 'missing.json', output, tmp_path / 'context.json')
    index = json.loads((output / 'raw-index.json').read_bytes())
    assert index == {'outside-link': {'kind': 'symlink', 'target': str(target)}, 'test-fifo': {'kind': 'fifo'}}
    with tarfile.open(output / 'source-suite-raw.tar.gz') as archive:
        assert archive.getmember('outside-link').issym()
        assert archive.getmember('outside-link').linkname == str(target)
        assert archive.getmember('test-fifo').isfifo()


def test_source_prebusiness_failure_keeps_failure_receipt(tmp_path):
    output = tmp_path / 'platform'
    with pytest.raises(FileNotFoundError):
        suite.run(tmp_path / 'missing-config.json', output)
    value = json.loads((output / 'failure.json').read_bytes())
    assert 'missing-config.json' in value['traceback'] and 'FileNotFoundError' in value['traceback']


@pytest.mark.skipif(os.name != 'nt', reason='requires a real Windows directory junction')
def test_source_collector_prunes_actual_windows_junction(tmp_path, monkeypatch):
    work = tmp_path / 'work'
    work.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'must-not-collect.docx').write_bytes(b'outside sentinel, never a source member')
    link = work / 'junction'
    created = subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(link), str(outside)], capture_output=True)
    assert created.returncode == 0, (created.stdout, created.stderr)
    try:
        target = os.readlink(link)
        tag = link.lstat().st_reparse_tag
        for name, value in {'GITHUB_RUN_ID': 'local-junction-control', 'GITHUB_SHA': 'not-ci',
                            'RUNNER_OS': 'local', 'GITHUB_RUN_ATTEMPT': '1'}.items():
            monkeypatch.setenv(name, value)
        output = tmp_path / 'evidence'
        suite.collect(work, tmp_path / 'missing.json', output, tmp_path / 'context.json')
        index = json.loads((output / 'raw-index.json').read_bytes())
        assert index == {'junction': {'kind': 'junction', 'target': target, 'reparse_tag': tag}}
        with tarfile.open(output / 'source-suite-raw.tar.gz') as archive:
            assert len(archive.getmembers()) == 1
            assert archive.getmember('junction').issym() and archive.getmember('junction').linkname == target
        assert (outside / 'must-not-collect.docx').read_bytes() == b'outside sentinel, never a source member'
    finally:
        link.rmdir()
