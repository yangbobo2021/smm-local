"""The actual detached local service must retain its caller's private CA trust."""
import ipaddress
import json
import socket
import ssl
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.error import URLError
from urllib.request import Request, build_opener, HTTPSHandler, ProxyHandler

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from smm_local import federation, service
from smm_local.core import Archive
from test_federation import record_codex


def test_detached_service_can_upload_through_callers_private_ca(tmp_path, monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
    now = datetime.now(timezone.utc)
    certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()), critical=False)
        .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=True,
            data_encipherment=False, key_agreement=False, key_cert_sign=True, crl_sign=True,
            encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'), x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
        .sign(key, hashes.SHA256()))
    cert, private, token_file = [tmp_path / name for name in ('ca.pem', 'key.pem', 'token')]
    cert.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    private.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    token = 'synthetic-tls-token-' + 't' * 40; token_file.write_text(token)
    monkeypatch.setenv('SSL_CERT_FILE', str(cert)); monkeypatch.setenv('SMM_SERVICE_PORT', '0')
    # The test process imported its shared opener before creating this CA.
    # Fresh product child processes load the environment before importing it.
    opener = build_opener(ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context(cafile=cert)))
    monkeypatch.setattr(service, 'LOCAL_HTTP', opener)
    monkeypatch.setattr(federation, 'LOCAL_HTTP', opener)
    histories, empty = tmp_path / 'sessions', tmp_path / 'empty'; histories.mkdir(); empty.mkdir()
    working = tmp_path / 'A'; working.mkdir()
    record_codex(histories, 'private-ca-session', [(1, 'm1', 'private CA background upload evidence')], cwd=working)
    db = Archive(tmp_path / 'local.sqlite3'); db.set_settings(codex_root=str(histories), claude_root=str(empty)); db.sync_codex()
    with socket.socket() as listener: listener.bind(('127.0.0.1', 0)); port = listener.getsockname()[1]
    address = f'https://localhost:{port}'
    log = (tmp_path / 'hub.log').open('w')
    hub = subprocess.Popen([sys.executable, '-m', 'smm_hub.cli', '--db', str(tmp_path / 'hub.sqlite3'),
        'serve-hub', '--port', str(port), '--token-file', str(token_file), '--tls-cert', str(cert), '--tls-key', str(private)], stdout=log, stderr=log)
    def remote(route, payload=None):
        req = Request(address + '/v1/' + route, data=json.dumps(payload).encode() if payload is not None else None,
                      headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        with service.LOCAL_HTTP.open(req, timeout=3) as response: return json.load(response)
    try:
        until = time.monotonic() + 15
        while True:
            try: remote('info'); break
            except URLError:
                if time.monotonic() > until: raise
                time.sleep(.1)
        assert federation.configure_hub(db, address, 'private-ca-device', str(token_file))['connected']
        assert federation.choose_upload(db, 'all', [])['state'] == 'confirmed'
        result = service.maintain(db, 'sync')
        if result.get('running'):
            until = time.monotonic() + 30
            while service.maintain(db, 'status')['sync']['running']:
                assert time.monotonic() < until; time.sleep(.1)
        hits = remote('search', {'query': 'background upload', 'preview_chars': 0})['results']
        assert len(hits) == 1
        assert hits[0]['matched_messages'][0]['text'] == 'private CA background upload evidence'
        exact = remote('read', {'hub_id': remote('info')['hub_id'], 'reference': hits[0]['reference']})
        assert [m['text'] for m in exact['messages']] == ['private CA background upload evidence']
    finally:
        service.stop_on_demand(db)
        hub.terminate(); hub.wait(timeout=15); log.close()
