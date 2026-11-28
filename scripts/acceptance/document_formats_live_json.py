"""Read an atomically replaced observation file within its existing deadline.

Every failed open remains evidence. A persistent denial is never accepted as
an absent task, a successful task, or permission to alter the product's ACL.
"""
import hashlib
import json
import time


def read_live_json(path, deadline, *, observe, current):
    attempts = []
    while True:
        current()  # The original enrolled task must still be the target.
        started = time.monotonic()
        try:
            raw = path.read_bytes()
        except (PermissionError, FileNotFoundError) as error:
            attempts.append({'started': started, 'finished': time.monotonic(),
                'type': type(error).__name__, 'errno': error.errno,
                'winerror': getattr(error, 'winerror', None), 'filename': str(error.filename),
                'message': str(error)})
            observe({'path': str(path), 'status': 'open_failed', 'attempts': list(attempts)})
            if time.monotonic() >= deadline: raise
            time.sleep(min(.01, max(0, deadline - time.monotonic())))
            continue
        # A complete but invalid JSON snapshot is not an atomic-open race.
        # Preserve the original parser failure instead of retrying it away.
        try: result = json.loads(raw)
        except (ValueError, UnicodeError):
            observe({'path': str(path), 'status': 'invalid_json', 'attempts': list(attempts),
                     'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
            raise
        current()
        if time.monotonic() > deadline:
            observe({'path': str(path), 'status': 'deadline_exceeded', 'attempts': list(attempts),
                     'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
            raise TimeoutError('live snapshot observation exceeded its original deadline')
        observe({'path': str(path), 'status': 'read', 'attempts': list(attempts),
                 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
                 'started': started, 'finished': time.monotonic()})
        if time.monotonic() > deadline:
            raise TimeoutError('live snapshot evidence exceeded its original deadline')
        return result
