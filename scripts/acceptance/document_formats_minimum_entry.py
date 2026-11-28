"""Fixed ordinary-account entry compatible with the task provisioner."""
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from document_formats_minimum import execute

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--target-config", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
output = Path(os.environ['ACCEPTANCE_EVIDENCE_DIR']) / 'installed-minimum' if os.environ.get('ACCEPTANCE_EVIDENCE_DIR') else args.output
execute(args.target_config, output)
