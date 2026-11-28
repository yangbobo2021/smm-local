"""Preserve an actual non-JSON HTTP failure before decoding the response."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
from urllib.request import build_opener, ProxyHandler

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/acceptance'))
from hub_documents_platform import Probe


def test_actual_http_non_json_error_has_original_status_and_bytes(tmp_path):
    raw = '真实 HTTP 500\r\nnot JSON'.encode('utf-8')
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(500)
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        def log_message(self, *args):pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=server.serve_forever)
    worker.start()
    probe = Probe.__new__(Probe)
    probe.out, probe.calls = tmp_path, []
    probe.address = {'a': 'http://127.0.0.1:' + str(server.server_port)}
    probe.http = build_opener(ProxyHandler({}))
    probe.phase = 'http-error-control'
    try:
        with pytest.raises(json.JSONDecodeError):
            probe.request('a', '/actual-failure')
    finally:
        server.shutdown();worker.join();server.server_close()
    records = json.loads((tmp_path / 'commands.json').read_text())
    assert len(records) == 1 and records[0]['status'] == 500
    record = records[0]
    assert (tmp_path / record['response_file']).read_bytes() == raw
    assert record['response_sha256'] == hashlib.sha256(raw).hexdigest()
    assert record['response_bytes'] == len(raw) and record['json_error']
