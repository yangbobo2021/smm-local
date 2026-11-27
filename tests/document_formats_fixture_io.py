"""Readiness of newly published task-owned fixture metadata, never product input."""
import json
from pathlib import Path
import time


def read_fixture_json(path,*,deadline):
    """Keep the caller's existing deadline; never turn an unreadable file into data."""
    while True:
        try:return json.loads(Path(path).read_text(encoding='utf-8'))
        except (FileNotFoundError,PermissionError):
            if time.monotonic()>=deadline:raise
            time.sleep(min(.005,max(0,deadline-time.monotonic())))
