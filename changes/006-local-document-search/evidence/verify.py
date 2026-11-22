"""Verify every published byte; optionally also check private originals locally."""
from pathlib import Path
import hashlib,json,argparse
p=argparse.ArgumentParser();p.add_argument('--raw-root',type=Path);a=p.parse_args()
root=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
manifest=json.loads((root/'SHA256SUMS.json').read_text())
for name,expected in manifest.items():
 path=(root/name).resolve();assert path.is_relative_to(root),name
 assert sha(path.read_bytes())==expected,name
if a.raw_root:
 for item in json.loads((root/'provenance.json').read_text())['files']:
  assert sha((a.raw_root/item['source']).read_bytes())==item['source_sha256'],item['source']
print(f'Verified {len(manifest)} published files'+(' and private original SHA' if a.raw_root else ''))
