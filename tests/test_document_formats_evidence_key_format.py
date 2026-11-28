"""Equivalent PEM line endings must identify the same durable evidence key."""
import hashlib
import json
from pathlib import Path
import struct

import pytest

from test_document_formats_evidence import E, preserve_control, bundle


@pytest.mark.parametrize('newline', [b'\n', b'\r\n'], ids=['LF', 'Windows-CRLF'])
def test_evidence_key_identity_is_independent_of_pem_file_line_endings(tmp_path, newline):
    source = tmp_path / 'source'
    source.mkdir()
    expected = b'fixed independent original bytes\r\n\xff\x00'
    (source / 'original.bin').write_bytes(expected)
    keys = tmp_path / 'keys'
    E.keygen(keys)
    canonical = (keys / 'public.pem').read_bytes()
    public = tmp_path / 'checked-out-public.pem'
    public.write_bytes(canonical.replace(b'\n', newline))
    context = {'run_id': 'test-run', 'job_key': 'key-line-endings', 'commit': 'a' * 40}
    envelope = tmp_path / 'raw.smm-evidence'
    E.pack(source, public, context, envelope)
    recovered = tmp_path / 'recovered.zip'
    E.decrypt(envelope, keys / 'private.pem', recovered, context)
    import zipfile
    with zipfile.ZipFile(recovered) as archive:
        assert archive.testzip() is None
        assert archive.read('original.bin') == expected
        manifest = json.loads(archive.read('evidence-manifest.json'))
        assert manifest['files']['original.bin'] == {'sha256': hashlib.sha256(expected).hexdigest(), 'bytes': len(expected)}
    raw = envelope.read_bytes()
    length = struct.unpack('>I', raw[len(E.MAGIC):len(E.MAGIC) + 4])[0]
    header = json.loads(raw[len(E.MAGIC) + 4:len(E.MAGIC) + 4 + length])
    assert header['public_key_sha256'] == hashlib.sha256(canonical).hexdigest()
    preserve_control('key-format-' + ('CRLF' if newline == b'\r\n' else 'LF'), [public, envelope, recovered],
                     {'expected_original_sha256': hashlib.sha256(expected).hexdigest(), 'canonical_public_sha256': hashlib.sha256(canonical).hexdigest(), 'header': header})


@pytest.mark.parametrize('valid', [True, False], ids=['Windows-UTF8-BOM', 'malformed-JSON-still-rejected'])
def test_evidence_reads_windows_json_bom_without_hiding_json_errors(bundle, tmp_path, valid):
    import zipfile
    for name in ('original.json', 'cleanup.json'):
        path = bundle.source / name
        path.write_bytes(b'\xef\xbb\xbf' + path.read_bytes())
    if not valid:
        path = bundle.source / 'original.json'
        path.write_bytes(path.read_bytes() + b'\xef\xbb\xbf')
    expected_bytes = {name: (bundle.source / name).read_bytes() for name in ('original.json', 'cleanup.json')}
    envelope = tmp_path / 'windows-json.smm-evidence'
    E.pack(bundle.source, bundle.key / 'public.pem', bundle.context, envelope)
    archive = tmp_path / 'windows-json.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.write(envelope, envelope.name)
    metadata = {**bundle.metadata, 'digest': 'sha256:' + E.sha(archive), 'size_in_bytes': archive.stat().st_size}
    destination = tmp_path / 'verified-windows-json'
    if valid:
        receipt = E.verify(archive, metadata, bundle.key / 'private.pem', bundle.context, destination, 'cleanup.json')
        assert receipt['status'] == 'recovered_verified'
        for name in ('original.json', 'cleanup.json'):
            assert (bundle.source / name).read_bytes() == expected_bytes[name]
            assert (destination / name).read_bytes() == expected_bytes[name]
        assert receipt['opened']['original.json'] == {'reader': 'JSON', 'root_type': 'dict'}
    else:
        with pytest.raises(json.JSONDecodeError):
            E.verify(archive, metadata, bundle.key / 'private.pem', bundle.context, destination, 'cleanup.json')
        assert not destination.exists()
        assert all((bundle.source / name).read_bytes() == raw for name, raw in expected_bytes.items())
