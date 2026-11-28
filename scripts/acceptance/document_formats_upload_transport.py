"""Shared real authenticated upload transport for installed document probes."""
from __future__ import annotations
import hashlib
import http.client
import json
from pathlib import Path
import ssl
import time
from uuid import uuid4

def rows(probe, role):
    value = probe.request(role, probe.path(role, '/documents/files'))
    assert len(value) == len({row['id'] for row in value})
    return {row['id']: row for row in value}


def wait(probe, role, ident, *, timeout=60):
    deadline = time.monotonic() + timeout
    while True:
        entry = rows(probe, role)[ident]
        if entry['latest_attempt']['status'] in {'ready', 'partial', 'failed'}:
            return entry
        assert time.monotonic() < deadline, entry
        time.sleep(.05)


def upload(probe, item, raw, *, replacement=None, await_terminal=True):
    probe.phase = 'explicit-upload'
    role, project = item['role'], item['project']
    body = probe.body(role, project_id=project['id'],
        project_key=project['source_key'] if role == 'hub' else project['stable_key'],
        submission_id=uuid4().hex, name=item['label'] + '.' + item['format'],
        sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    if replacement:
        body.update(document_id=replacement['id'], expected_version=replacement['version'],
            expected_processing_version=replacement['processing_version'],
            expected_revision=replacement['source_revision'],
            capture_id=replacement['latest_attempt']['capture_id'],
            expected_attempt_id=replacement['latest_attempt']['attempt_id'])
    reply = probe.request(role, probe.path(role, '/documents/uploads'), body)
    ident = reply['upload_id']
    for number, start in enumerate(range(0, len(raw), reply['block_bytes'])):
        chunk = raw[start:start + reply['block_bytes']]
        path = probe.path(role, '/documents/uploads/' + ident + '/parts/' + str(number))
        connection = (http.client.HTTPSConnection('127.0.0.1', probe.ports[role],
            context=ssl.create_default_context(cafile=str(probe.ca)), timeout=15)
            if role == 'hub' else http.client.HTTPConnection('127.0.0.1', probe.ports[role], timeout=15))
        try:
            headers = {'X-Chunk-SHA256': hashlib.sha256(chunk).hexdigest(), 'X-SMM-UI': '1'}
            if role == 'hub':
                headers['Authorization'] = 'Bearer ' + probe.token
            connection.request('PUT', path, body=chunk, headers=headers)
            response = connection.getresponse()
            original = response.read()
            probe.keep('lifecycle-http/' + hashlib.sha256(original).hexdigest() + '.json', original)
            probe.calls.append({'label': 'lifecycle-upload-chunk', 'role': role, 'path': path,
                'request_bytes': len(chunk), 'request_sha256': hashlib.sha256(chunk).hexdigest(),
                'status': response.status, 'response': json.loads(original)})
            probe.save('commands', probe.calls)
            assert response.status == 200, original
        finally:
            connection.close()
    receipt = probe.request(role, probe.path(role, '/documents/uploads/' + ident + '/commit'), probe.body(role))
    if not await_terminal:
        return receipt
    entry = wait(probe, role, receipt['document_id'])
    probe.phase = 'archive-only'
    assert entry['latest_attempt']['capture_id'] == receipt['capture_id']
    assert entry['latest_attempt']['attempt_id'] == receipt['attempt_id']
    return entry

