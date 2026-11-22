"""Prepare an exclusive local 005 target config, never register a service."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, required=True); p.add_argument('--local-python', required=True); p.add_argument('--hub-python', required=True)
    p.add_argument('--local-wheel', type=Path, required=True); p.add_argument('--hub-wheel', type=Path, required=True)
    p.add_argument('--browser'); p.add_argument('--openssl', default='openssl'); args = p.parse_args()
    assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip(), 'commit candidate before formal package probe'
    candidate = {'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'dirty': False}
    for kind in ('local', 'hub'):
        wheel = getattr(args, kind + '_wheel').resolve()
        with zipfile.ZipFile(wheel) as z:
            candidate['installed_' + kind] = {name: hashlib.sha256(z.read(name)).hexdigest() for name in z.namelist() if name.startswith('smm_' + kind + '/') and not name.endswith('/')}
            for name in candidate['installed_' + kind]:
                if name == 'smm_hub/_archive/__init__.py':
                    expected = (ROOT / 'src/smm_hub/_archive.py').read_text(encoding='utf-8').replace('from smm_local.', 'from .').encode()
                else:
                    source = name.replace('smm_hub/_archive/', 'smm_local/')
                    expected = (ROOT / 'src' / source).read_bytes()
                assert z.read(name) == expected, 'wheel differs from candidate source: ' + name
        candidate[kind + '_wheel'] = {'name': wheel.name, 'sha256': hashlib.sha256(wheel.read_bytes()).hexdigest()}
    work = args.work.resolve(); work.mkdir(parents=True, exist_ok=False)
    cert, key = work / 'cert.pem', work / 'key.pem'
    subprocess.run([args.openssl, 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '3',
                    '-keyout', str(key), '-out', str(cert), '-subj', '/CN=localhost',
                    '-addext', 'subjectAltName=DNS:localhost,IP:127.0.0.1', '-addext', 'basicConstraints=critical,CA:TRUE'], check=True, capture_output=True)
    key.chmod(0o600)
    with socket.socket() as s: s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]
    config = {'work': str(work), 'local_python': str(Path(args.local_python).expanduser().absolute()), 'hub_python': str(Path(args.hub_python).expanduser().absolute()),
              'cert': str(cert), 'key': str(key), 'port': port, 'address': f'https://localhost:{port}', 'candidate': candidate}
    if args.browser: config['browser'] = args.browser
    (work / 'target.json').write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    print(work / 'target.json')


if __name__ == '__main__': main()
