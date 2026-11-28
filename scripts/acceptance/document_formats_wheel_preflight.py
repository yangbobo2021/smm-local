"""Read exact wheel inputs as the actual business controller, before services."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import traceback
from uuid import uuid4

from document_formats_guard_primitives import actual_identity


def verify_wheel_inputs(config, directory):
    receipt = Path(directory) / ('wheel-read-preflight-' + uuid4().hex + '.json')
    value = {'scope': 'Controller file-read preparation only, not product business acceptance',
             'actual_actor': actual_identity(), 'status': 'running', 'wheels': []}
    def save():
        receipt.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    save()
    try:
        if config.get('expected_actor_sid'):
            actor = value['actual_actor']
            assert actor['sid'] == config['expected_actor_sid'] and not actor['is_admin'] and actor['session_id'] > 0
        assert config.get('hub_wheel'), 'Hub wheel input required; Local optional for base-only receiver'
        for role in ('local', 'hub'):
            if not config.get(role + '_wheel'):
                continue
            path = Path(config[role + '_wheel'])
            entry = {'role': role, 'path': str(path), 'expected_sha256': config[role + '_wheel_sha256']}
            value['wheels'].append(entry)
            save()
            if os.name == 'nt':
                result = subprocess.run(['icacls.exe', str(path)], capture_output=True, timeout=15)
                entry['actual_controller_acl'] = {'exit_code': result.returncode,
                    'stdout_base64': base64.b64encode(result.stdout).decode('ascii'),
                    'stderr_base64': base64.b64encode(result.stderr).decode('ascii')}
                save()
                assert result.returncode == 0, 'Actual controller cannot observe wheel ACL'
            raw = path.read_bytes()
            entry.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            save()
            assert entry['sha256'] == entry['expected_sha256'], 'Prepared wheel bytes changed'
        value['status'] = 'passed'
        save()
        return value
    except BaseException:
        value.update(status='failed', traceback=traceback.format_exc())
        save()
        raise
