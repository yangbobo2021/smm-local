"""Fixed entry for provisioned ordinary-account cross-OS acceptance."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from document_formats_cross_os import produce, receive


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--target-config', type=Path, required=True)
parser.add_argument('--output', type=Path)
parser.add_argument('--bind', choices=['produce', 'receive'])
parser.add_argument('--bundle', type=Path)
parser.add_argument('--source-platform')
args = parser.parse_args()
config = json.loads(args.target_config.read_text(encoding='utf-8-sig'))
if args.bind:
    assert 'cross_os_phase' not in config and args.bundle
    config.update(cross_os_phase=args.bind, bundle=str(args.bundle.resolve()), source_platform=args.source_platform)
    args.target_config.write_text(json.dumps(config, indent=2), encoding='utf-8')
else:
    assert args.output
    from document_formats_wheel_preflight import verify_wheel_inputs
    verify_wheel_inputs(config, args.target_config.resolve().parent)
    if config['cross_os_phase'] == 'produce':
        produce(config, args.output.resolve(), Path(config['bundle']))
    else:
        receive(config, args.output.resolve(), Path(config['bundle']), config['source_platform'])
