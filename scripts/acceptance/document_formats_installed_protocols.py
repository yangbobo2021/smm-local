"""008 installed products: real creator CLI, browser and MCP protocols.

Uses only new task archives. Fixture generation may import checkout helpers;
CLI/Web/MCP entry interpreters use the independently installed wheels with -I.
Workers retain the product launch flags; their actual prefixes, cwd and identity
are observed separately.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
from collections import deque
import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess
import sqlite3
import time
import traceback
import shutil
from types import SimpleNamespace
from urllib.request import Request
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hub_documents_platform import Probe, now, sha


class FormatProbe(Probe):
    @staticmethod
    def actor():
        value = Probe.actor()
        from document_formats_guard_primitives import actual_identity
        value.update(actual_identity())
        if os.name == 'nt':
            import ctypes
            import re
            session = ctypes.c_ulong()
            assert ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(session))
            value['session_id'] = session.value
            raw = subprocess.check_output(['whoami.exe', '/groups', '/fo', 'csv', '/nh'])
            value['group_sids'] = sorted({sid.decode('ascii') for sid in re.findall(rb'S-\d-(?:\d+-)*\d+', raw)})
            value['groups_original_base64'] = base64.b64encode(raw).decode('ascii')
            assert 'S-1-5-32-544' not in value['group_sids'], 'E requires a separate non-administrator account'
            assert value['session_id'] > 0, 'E requires an actual interactive session, not session0'
        else:
            assert value['euid'] == value['uid'] != 0
        return value

    def save(self, name, value):
        if name == 'commands':
            # Capture each real call once, at observation time. Rewriting a
            # growing list costs quadratic I/O and can destroy the previous
            # complete log when storage fills. Raw stdout/base64 fields remain
            # intact in the append-only stream, including non-UTF8 controls.
            path = self.out / 'commands.jsonl'
            if not hasattr(self, '_commands_digest'):
                assert not path.exists()
                self._commands_digest = hashlib.sha256()
                self._commands_bytes = self._commands_count = 0
                self._commands_pending = deque()
                self._commands_dirty = False
            observed = self._commands_count + len(self._commands_pending)
            assert len(value) >= observed, 'command observations must be append-only'
            # Freeze even the not-yet-durable observations. A caller changing a
            # request object after an I/O error cannot rewrite its earlier call.
            self._commands_pending.extend(
                (json.dumps(record, ensure_ascii=False, separators=(',', ':'), default=str) + '\n').encode('utf-8')
                for record in value[observed:])
            with path.open('r+b' if path.exists() else 'x+b', buffering=0) as stream:
                if self._commands_dirty:
                    # A failed write/fsync may leave an incomplete or complete
                    # unconfirmed tail. Keep and verify the last durable prefix,
                    # then discard only that unconfirmed tail before replay.
                    stream.seek(0)
                    prefix = hashlib.sha256()
                    remaining = self._commands_bytes
                    while remaining:
                        raw = stream.read(min(1048576, remaining))
                        assert raw, 'durable command prefix was truncated'
                        prefix.update(raw)
                        remaining -= len(raw)
                    assert prefix.digest() == self._commands_digest.digest(), 'durable command prefix changed'
                    stream.truncate(self._commands_bytes)
                    stream.flush()
                    os.fsync(stream.fileno())
                    self._commands_dirty = False
                stream.seek(0, os.SEEK_END)
                assert stream.tell() == self._commands_bytes, 'unexpected command log tail'
                while self._commands_pending:
                    raw = self._commands_pending[0]
                    self._commands_dirty = True
                    remaining = memoryview(raw)
                    while remaining:
                        written = stream.write(remaining)
                        if not written:
                            raise OSError('command log write made no progress')
                        remaining = remaining[written:]
                    stream.flush()
                    os.fsync(stream.fileno())
                    self._commands_digest.update(raw)
                    self._commands_bytes += len(raw)
                    self._commands_count += 1
                    self._commands_pending.popleft()
                    self._commands_dirty = False
            value = {'schema': 'smm-008-command-jsonl-v1', 'path': 'commands.jsonl',
                     'records': self._commands_count, 'bytes': self._commands_bytes,
                     'sha256': self._commands_digest.hexdigest(),
                     'semantics': 'one frozen real request/response per line; original stdout/stderr base64 preserved'}
        target = self.out / (name + '.json')
        temporary = target.with_name(target.name + '.' + uuid4().hex + '.tmp')
        try:
            with temporary.open('x', encoding='utf-8') as stream:
                stream.write(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)

    def __init__(self, config, out):
        if config.get("expected_actor_sid"):
            assert self.actor()["sid"] == config["expected_actor_sid"]
        super().__init__(config, out)
        self.materials = json.loads(Path(config['materials']).read_text(encoding='utf-8'))
        os.environ.update(SMM_008_OCR_EXECUTABLE=self.materials['ocr_executable'],
                          SMM_008_OCR_DATA=self.materials['ocr_data_dir'],
                          SMM_008_FONT=self.materials['font']['path'],
                          ACCEPTANCE_EVIDENCE_DIR=str(out / 'attachments'))
        sys.path.insert(0, str(ROOT / 'tests'))
        from test_document_formats_installed_minimum import assert_complete_source_text, source_tables_match
        self.text_oracle = assert_complete_source_text
        self.native_table_oracle = source_tables_match
        self.items = []
        if config.get('read_guards'):
            from document_formats_protocol_guards import install
            install(self)

    def env(self, role='a'):
        value = super().env(role)
        # Products receive absolute OCR paths; no login-shell or developer PATH.
        value['PATH'] = (str(Path(os.environ['SystemRoot']) / 'System32') if os.name == 'nt' else '/usr/bin:/bin')
        return value

    def run(self, label, argv, **options):
        if label == 'openssl':
            # Controller-owned test TLS works without an interactive PATH or
            # a platform-specific openssl installation. Product TLS is real.
            from datetime import datetime, timedelta, timezone
            from ipaddress import ip_address
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.x509.oid import NameOID
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
            current = datetime.now(timezone.utc)
            cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                    .public_key(key.public_key()).serial_number(x509.random_serial_number())
                    .not_valid_before(current - timedelta(minutes=1)).not_valid_after(current + timedelta(days=2))
                    .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
                    .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
                    .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()), critical=False)
                    .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
                        key_encipherment=True, data_encipherment=False, key_agreement=False,
                        key_cert_sign=True, crl_sign=True, encipher_only=False, decipher_only=False), critical=True)
                    .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'), x509.IPAddress(ip_address('127.0.0.1'))]), critical=False)
                    .sign(key, hashes.SHA256()))
            self.key.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                    serialization.NoEncryption()))
            self.ca.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            self.save('task-tls-generation', {'implementation': 'controller cryptography',
                'certificate_sha256': sha(self.ca.read_bytes()), 'names': ['localhost', '127.0.0.1'],
                'purpose': 'isolated test service TLS; private key stays in private task evidence'})
            return ''
        return super().run(label, argv, **options)

    def version_bindings(self):
        return {p.relative_to(ROOT).as_posix(): sha(p.read_bytes())
                for name in ('src', 'tests', 'scripts/acceptance') for p in sorted((ROOT / name).rglob('*'))
                if p.is_file() and p.suffix in {'.py', '.ps1', '.html'} and '__pycache__' not in p.parts}

    def origins(self):
        self.archive_identities = {}
        for role, database in (('a', self.db['a']), ('hub', self.hub_db)):
            with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as c:
                value = json.loads(c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
            self.archive_identities[role] = value
        # A connected Local uses its persisted registration device ID, which
        # differs from the archive ID; read only this field, never export token.
        config_file = self.db['a'].with_suffix(self.db['a'].suffix + '.hub.json')
        self.device_identities = {'a': json.loads(config_file.read_text(encoding='utf-8'))['device_id'],
                                  'hub': self.hub_context['hub_id']}
        self.save('independent-archive-identities', {'archives': self.archive_identities, 'devices': self.device_identities})

    def expected_origin(self, item):
        archive = self.archive_identities[item['role']]
        return {'device_id': self.device_identities[item['role']],
                'archive_id': archive, 'document_id': item['id']}

    def register_source_paths(self):
        if self.config.get('read_guards'):
            temporary = self.source_paths.with_suffix('.new')
            temporary.write_text(json.dumps(sorted({os.path.normcase(os.path.abspath(i['path'])) for i in self.items})), encoding='utf-8')
            temporary.replace(self.source_paths)

    def original_info(self, value, item):
        assert value['origin'] == self.expected_origin(item) and value['id'] == item['id']
        assert value['available'] is True and value['sha256'] == item['sha256'] and value['bytes'] == len(item['raw'])
        assert value['version'] == value['processing_version'] == 1

    def path(self, role, name):
        return ('/v1' if role == 'hub' else '/api') + name

    def body(self, role, **value):
        return {**(self.hub_context if role == 'hub' else {}), **value}

    def keep(self, name, raw):
        p = self.out / 'attachments' / name
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            assert p.read_bytes() == raw
        else:
            p.write_bytes(raw)

    def raw_original(self, role, reference):
        body = self.body(role, reference=reference)
        headers = {'Content-Type': 'application/json', 'X-SMM-UI': '1'}
        if role == 'hub':
            headers['Authorization'] = 'Bearer ' + self.token
        request = Request(self.address[role] + self.path(role, '/documents/original'),
                          data=json.dumps(body).encode(), headers=headers, method='POST')
        with self.http.open(request, timeout=15) as response:
            raw = response.read()
            assert response.status == 200
        self.keep('downloads/' + sha(raw) + '.bin', raw)
        self.calls.append({'label': 'actual-http-original', 'role': role, 'request': body,
                           'status': 200, 'sha256': sha(raw), 'bytes': len(raw)})
        self.save('commands', self.calls)
        return raw

    def table_oracle(self, value, truth):
        if not truth.get('ocr'):
            return self.native_table_oracle(value, truth)
        from copy import deepcopy
        import re
        actual = deepcopy(value)
        for cell in actual['cells']:
            if isinstance(cell['text'], str):
                cell['text'] = re.sub(r'\s+', '', cell['text'])
        expected = {**truth, 'cells': [(r, c, re.sub(r'\s+', '', text), rs, cs)
                                       for r, c, text, rs, cs in truth['cells']]}
        return self.native_table_oracle(actual, expected)

    def material(self, kind, label, ocr_variant=None):
        from test_document_formats_management import native_input
        from test_document_formats_retry import scan_pdf
        if kind == 'ocrpdf' and ocr_variant is not None:
            from document_formats_ocr_fixture import scanned_fixture
            raw, source = scanned_fixture(self.materials['font']['path'], ocr_variant)
            truth = {'words': source['text'].splitlines(), 'excluded': [], 'ocr_quality': source,
                     'tables': [{'rows': 3, 'columns': 2, 'ocr': True, 'location': {'page': page['page']},
                                 'cells': [(c['row'], c['column'], c['text'], 1, 1) for c in page['cells']]}
                                for page in source['pages']]}
            fmt = 'pdf'
        elif kind == 'ocrpdf':
            raw = scan_pdf(label)
            truth = {'words': [label + ' RETRY 73428', 'CAPTURED ORIGINAL 12345.67'],
                     'excluded': [], 'tables': []}
            fmt = 'pdf'
        else:
            fmt = 'pdf' if kind == 'nativepdf' else kind
            raw, truth = native_input(fmt, label)
            if kind == 'docx':
                truth['ordered_groups'] = [truth['words'][:12]]
                from document_formats_fixtures import docx_fixture
                truth['part_positions'] = docx_fixture(label)[1]['anchors']
            elif kind == 'nativepdf':
                truth['ordered_groups'] = [truth['words']]
                from document_formats_pdf_fixture import native_pdf
                independent, positions = native_pdf(label)
                assert independent == raw
                truth['native_positions'] = positions
                from io import BytesIO
                import pdfplumber
                with pdfplumber.open(BytesIO(raw)) as source:
                    original_text = '\n'.join(page.extract_text() or '' for page in source.pages)
                assert all(original_text.count(word) == 1 for word in truth['words']), 'source fixture text overlaps before SMM'
        self.keep('inputs/' + label + '.' + fmt, raw)
        self.keep('truth/' + label + '.json', json.dumps(truth, ensure_ascii=False).encode())
        return {'kind': kind, 'format': fmt, 'label': label, 'raw': raw, 'truth': truth,
                'query': truth['words'][0].split()[0], 'sha256': sha(raw)}

    def prepare_formats(self):
        self.check_install()
        for role in ('hub', 'a'):
            self.start(role)
        info = self.request('hub', '/v1/info')
        self.hub_context = {k: info[k] for k in ('hub_id', 'document_epoch')}
        result = self.cli('a', 'configure-hub', self.address['hub'], '008 installed local',
                          '--token-file', self.token_file)
        assert result['connected']
        self.wait_idle('a')
        self.request('a', '/api/settings', {'sync_interval_seconds': 3600}, method='PUT')
        self.projects = {}
        for role in ('a', 'hub'):
            self.phase = 'prepare'
            self.projects[role] = [self.cli(role, 'project', 'create', '008 ordinary'),
                                   self.cli(role, 'project', 'ensure-global'),
                                   self.cli(role, 'project', 'create', 'unrelated')]
            configured = self.cli(role, 'documents', 'processing-configure', '--expected-revision', 0,
                                  '--ocr-executable', self.materials['ocr_executable'],
                                  '--ocr-data-dir', self.materials['ocr_data_dir'], '--languages', 'chi_sim+eng')
            checked = self.cli(role, 'documents', 'processing-status', '--check')
            assert checked['config']['revision'] == configured['config']['revision'] == 1
            assert checked['ocr']['ready'] is True and checked['ocr']['errors'] == []
            for group, project in enumerate(self.projects[role][:2]):
                directory = self.fixtures / (role + '-path-' + str(group))
                directory.mkdir()
                own = []
                for kind in ('docx', 'xlsx', 'nativepdf', 'ocrpdf'):
                    prefix = 'LOCAL' if role == 'a' else 'HUB'
                    variant = 'ALPHA' if group == 0 else 'BETA'
                    label = prefix + ('SCAN' + variant if kind == 'ocrpdf' else 'PATH' + variant + kind.upper())
                    if kind == 'nativepdf':
                        # Fixed-width source grid needs short, unambiguous keys;
                        # overflowing labels would overlap in the actual PDF.
                        label = ('L' if role == 'a' else 'H') + 'N' + ('A' if group == 0 else 'B')
                    item = self.material(kind, label)
                    path = directory / (item['label'] + '.' + item['format'])
                    path.write_bytes(item['raw'])
                    item.update(role=role, project=project, path=path, acquisition='path')
                    own.append(item)
                added = self.cli(role, 'documents', 'add', directory, '--project-id', project['id'])
                assert added['status'] == 'pending'
                self.phase = 'explicit-refresh'
                self.cli(role, 'documents', 'refresh', '--source-id', added['id'])
                self.phase = 'archive-only'
                rows = self.cli(role, 'documents', 'files', '--source-id', added['id'])
                assert len(rows) == len({r['id'] for r in rows}) == 4
                assert {Path(r['path']).name for r in rows} == {i['path'].name for i in own}
                for item in own:
                    entry = next(r for r in rows if Path(r['path']).name == item['path'].name)
                    assert entry['latest_attempt']['status'] == 'ready'
                    item.update(id=entry['id'], entry=entry)
                self.items.extend(own)
        self.origins()
        self.register_source_paths()

    def search(self, item):
        role = item['role']
        value = self.cli(role, 'documents', 'search', item['query'], '--scope', 'project',
                         '--project-id', item['project']['id'], '--limit', 50,
                         *(['--local'] if role == 'a' else []))
        assert len(value['results']) == 1
        hit = value['results'][0]
        assert hit['id'] == item['id'] and hit['sha256'] == item['sha256']
        assert hit['origin'] == self.expected_origin(item)
        assert hit['version'] == hit['processing_version'] == 1
        for project in self.projects[role]:
            if project['id'] == item['project']['id']:
                continue
            other = self.cli(role, 'documents', 'search', item['query'], '--scope', 'project',
                             '--project-id', project['id'], '--limit', 50,
                             *(['--local'] if role == 'a' else []))
            assert other['results'] == []
        return hit

    def text(self, value, item):
        assert value['id'] == item['id'] and value['format'] == item['format']
        assert value['origin'] == self.expected_origin(item)
        assert value['version'] == value['processing_version'] == 1 and value['sha256'] == item['sha256']
        assert value['processing_status'] == 'ready'
        if 'ocr_quality' in item['truth']:
            from test_document_formats_pdf_ocr import distance, normal
            source = item['truth']['ocr_quality']
            expected, actual = normal(source['text']), normal(value['text'])
            assert distance(expected, actual) / len(expected) <= .01
            for page in source['pages']:
                assert normal(page['title']) in actual and normal(page['paragraph']) in actual
                assert all(normal(c['text']) in actual for c in page['cells'])
        else:
            self.text_oracle(value['text'], item['truth'], item['kind'] == 'ocrpdf')
        assert all(word not in value['text'] for word in item['truth']['excluded'])
        assert len(value['tables']) == len(item['truth']['tables'])
        assert value['coverage']['errors'] == []
        from document_formats_protocol_positions import text_positions
        text_positions(value, item['truth'])
        if item['kind'] == 'ocrpdf':
            assert value['locations'] and all(l['method'] == 'ocr' for l in value['locations'])

    def table(self, value, truth, item, summary):
        assert value['id'] == item['id'] and value['origin'] == self.expected_origin(item)
        assert value['table_id'] == summary['table_id'] and value['location'] == summary['location']
        assert value['version'] == value['processing_version'] == 1 and value['sha256'] == item['sha256']
        assert self.table_oracle(value, truth)
        assert all(value['location'].get(k) == v for k, v in truth['location'].items())
        from document_formats_protocol_positions import table_positions
        table_positions(value, item['truth'])
        from test_document_formats_pdf_ocr import normal
        for cell in value['cells']:
            if not cell.get('text'):
                continue
            location = cell['location']
            text = normal(cell['text']) if item['kind'] == 'ocrpdf' else cell['text']
            expected = []
            for loc in item['snapshot']['locations']:
                content = item['snapshot']['text'][loc['start']:loc['end']]
                if item['kind'] == 'ocrpdf':
                    content = normal(content)
                keys = ('page', 'part', 'coordinate', 'sheet_index') if item['format'] == 'docx' else ('page', 'part', 'path', 'coordinate', 'sheet_index')
                if content == text and all(loc.get(k) == location.get(k) for k in keys):
                    expected.append(loc)
            assert len(expected) == 1
            # Word table locations identify the cell, whereas text locations
            # identify its paragraph. Character spans are optional on the cell;
            # if supplied, they must identify the independently checked text.
            if 'start' in location or 'end' in location:
                assert all(location.get(k) == expected[0][k] for k in ('start', 'end'))
            for key in ('page', 'bbox', 'page_width', 'page_height', 'rotation', 'method', 'confidence', 'part', 'coordinate', 'sheet', 'sheet_index'):
                if key in location:
                    assert location[key] == expected[0].get(key)

    def complete_cli_http(self, phase):
        for item in self.items:
            role = item['role']
            hit = self.search(item)
            if 'hit' in item:
                assert hit['reference'] == item['hit']['reference']
            else:
                item['hit'] = hit
            reference = item['hit']['reference']
            value = self.cli(role, 'documents', 'read', '--reference', reference, '--start', 0, '--end', hit['text_length'])
            self.text(value, item)
            http = self.request(role, self.path(role, '/documents/read'), self.body(role, reference=reference, start=0, end=hit['text_length']))
            assert http == value
            if 'snapshot' in item:
                assert value == item['snapshot']
            else:
                item['snapshot'] = value
            self.page_searches(item, value)
            actual_tables = []
            for summary in value['tables']:
                matches = [t for t in item['truth']['tables'] if (summary['rows'], summary['columns']) == (t['rows'], t['columns'])
                           and all(summary['location'].get(k) == v for k, v in t['location'].items())]
                assert matches
                rows, columns = summary['rows'], summary['columns']
                request = dict(reference=reference, view='table', table_id=summary['table_id'], row_start=1,
                               row_end=rows + 1, column_start=1, column_end=columns + 1)
                table = self.request(role, self.path(role, '/documents/read'), self.body(role, **request))
                matches = [t for t in matches if self.table_oracle(table, t)]
                assert len(matches) == 1
                truth = matches[0]
                self.table(table, truth, item, summary)
                cli = self.cli(role, 'documents', 'read', '--reference', reference, '--view', 'table',
                               '--table-id', summary['table_id'], '--row-start', 1, '--row-end', rows + 1,
                               '--column-start', 1, '--column-end', columns + 1)
                assert cli == table
                actual_tables.append(table)
            assert len({t['table_id'] for t in actual_tables}) == len(item['truth']['tables'])
            assert all(sum(self.table_oracle(t, truth) and all(t['location'].get(k) == v for k, v in truth['location'].items())
                           for t in actual_tables) == 1 for truth in item['truth']['tables'])
            info = self.cli(role, 'documents', 'read', '--reference', reference, '--view', 'original-info')
            self.original_info(info, item)
            output = self.out / (phase + '-' + item['label'] + '.' + item['format'])
            downloaded = self.cli(role, 'documents', 'read', '--reference', reference, '--original-output', output)
            assert output.read_bytes() == self.raw_original(role, reference) == item['raw']
            assert downloaded['sha256'] == item['sha256']
        self.save(phase + '-full-reads', {'ids': [i['id'] for i in self.items], 'count': len(self.items)})

    def page_searches(self, item, value):
        from document_formats_protocol_positions import page_anchors
        from test_document_formats_pdf_ocr import normal
        role = item['role']
        for query, page in page_anchors(item['truth']):
            found = self.cli(role, 'documents', 'search', query, '--scope', 'project',
                '--project-id', item['project']['id'], '--limit', 50, *(['--local'] if role == 'a' else []))
            own = [hit for hit in found['results'] if hit['id'] == item['id']]
            assert len(own) == 1 and own[0]['origin'] == self.expected_origin(item)
            expected = [loc for loc in value['locations'] if loc['page'] == page
                        and normal(value['text'][loc['start']:loc['end']]) == normal(query)]
            assert len(expected) == 1
            assert expected[0] in own[0]['locations']

    def mcp_formats(self, phase):
        own = self.items
        queries = [('search_documents', {'query': i['query'], 'scope': 'project', 'limit': 50,
                   **({'project_id': i['project']['id'], 'local': True} if i['role'] == 'a'
                      else {'hub_project_id': i['project']['id']})}) for i in own]
        found = asyncio.run(self.mcp('a', queries))
        assert len(found) == len(own)
        for item, value in zip(own, found):
            assert len(value['results']) == 1 and value['results'][0]['id'] == item['id']
            assert value['results'][0]['origin'] == self.expected_origin(item)
            if 'mcp_hit' in item:
                assert value['results'][0]['reference'] == item['mcp_hit']['reference']
            else:
                item['mcp_hit'] = value['results'][0]
        requests = [('read_document', {'reference': i['mcp_hit']['reference'], 'start': 0, 'end': i['hit']['text_length']}) for i in own]
        answers = asyncio.run(self.mcp('a', requests))
        assert len(answers) == len(own)
        for item, value in zip(own, answers):
            self.text(value, item)
            assert value == item['snapshot']
        details = []
        tags = []
        for index, item in enumerate(own):
            for summary in item['snapshot']['tables']:
                request = {'reference': item['mcp_hit']['reference'], 'view': 'table', 'table_id': summary['table_id'],
                           'row_start': 1, 'row_end': summary['rows'] + 1, 'column_start': 1, 'column_end': summary['columns'] + 1}
                details.append(('read_document', request))
                tags.append((index, summary))
            details.append(('read_document', {'reference': item['mcp_hit']['reference'], 'view': 'original-info'}))
            tags.append((index, None))
        values = asyncio.run(self.mcp('a', details))
        assert len(values) == len(tags) == len(details)
        by_item = {index: [] for index in range(len(own))}
        for (index, summary), value in zip(tags, values):
            item = own[index]
            if summary is None:
                self.original_info(value, item)
            else:
                matches = [truth for truth in item['truth']['tables'] if self.table_oracle(value, truth)
                           and all(value['location'].get(k) == v for k, v in truth['location'].items())]
                assert len(matches) == 1
                truth = matches[0]
                self.table(value, truth, item, summary)
                by_item[index].append(value)
        for index, item in enumerate(own):
            tables = by_item[index]
            assert len({t['table_id'] for t in tables}) == len(item['truth']['tables'])
            assert all(sum(self.table_oracle(t, truth) and all(t['location'].get(k) == v for k, v in truth['location'].items())
                           for t in tables) == 1 for truth in item['truth']['tables'])
            reference = item['mcp_hit']['reference']
            assert self.raw_original('a', reference) == item['raw']
            output = self.out / (phase + '-mcp-original-' + item['label'] + '.' + item['format'])
            download = self.cli('a', 'documents', 'read', '--reference', reference, '--original-output', output)
            assert output.read_bytes() == item['raw'] and download['sha256'] == item['sha256']
        self.save(phase + '-mcp-complete', {'ids': [i['id'] for i in own], 'actual_stdio': True})

    def local_hub_cli(self, phase):
        for item in (i for i in self.items if i['role'] == 'hub'):
            found = self.cli('a', 'documents', 'search', item['query'], '--scope', 'project',
                             '--hub-project-id', item['project']['id'], '--limit', 50)
            assert len(found['results']) == 1
            hit = found['results'][0]
            assert hit['id'] == item['id'] and hit['origin'] == self.expected_origin(item)
            if 'local_route_hit' not in item:
                item['local_route_hit'] = hit
            assert hit['reference'] == item['local_route_hit']['reference']
            ref = item['local_route_hit']['reference']
            value = self.cli('a', 'documents', 'read', '--reference', ref, '--start', 0, '--end', hit['text_length'])
            self.text(value, item)
            assert value == item['snapshot']
            for summary in value['tables']:
                view = self.cli('a', 'documents', 'read', '--reference', ref, '--view', 'table',
                    '--table-id', summary['table_id'], '--row-start', 1, '--row-end', summary['rows'] + 1,
                    '--column-start', 1, '--column-end', summary['columns'] + 1)
                matched = [t for t in item['truth']['tables'] if self.table_oracle(view, t)
                           and all(view['location'].get(k) == v for k, v in t['location'].items())]
                assert len(matched) == 1
                self.table(view, matched[0], item, summary)
            self.original_info(self.cli('a', 'documents', 'read', '--reference', ref, '--view', 'original-info'), item)
            output = self.out / (phase + '-local-route-' + item['label'] + '.' + item['format'])
            self.cli('a', 'documents', 'read', '--reference', ref, '--original-output', output)
            assert output.read_bytes() == item['raw']
        self.save(phase + '-local-hub-cli', {'ids': [i['id'] for i in self.items if i['role'] == 'hub']})

    def browser(self, role, phase):
        from document_formats_web_helpers import Browser
        from playwright.sync_api import sync_playwright, expect
        probe = self
        server = SimpleNamespace(owner='local' if role == 'a' else 'hub', port=self.ports[role],
                                 prefix='/api' if role == 'a' else '/v1', token=self.token)
        evidence = self.out / 'browser' / phase / role
        evidence.mkdir(parents=True)
        from cryptography import x509
        from cryptography.hazmat.primitives import serialization
        der = x509.load_pem_x509_certificate(self.ca.read_bytes()).public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        pin = base64.b64encode(hashlib.sha256(der).digest()).decode()

        class InstalledBrowser(Browser):
            def search(self, project, query, remote=False):
                if self.owner != 'local' or not remote:
                    if self.owner == 'local':
                        self.page.locator('#doc-archive-mode').select_option('combined')
                        self.page.locator('#doc-scope').select_option('project')
                        self.page.locator('#doc-root-kind').select_option('local')
                    return super().search(project, query)
                self.page.locator('#doc-archive-mode').select_option('combined')
                self.page.locator('#doc-scope').select_option('project')
                self.page.locator('#doc-root-kind').select_option('hub')
                expect(self.page.locator('#doc-hub-project')).to_be_enabled()
                self.page.locator('#doc-hub-project').select_option(str(project['id']))
                expect(self.page.locator('#doc-hub-project')).to_have_value(str(project['id']))
                self.page.locator('#doc-query').fill(query)
                return self.action(None, self.page.locator('#doc-search-submit').click, '/documents/search')

            def open(self):
                self.pw = sync_playwright().start()
                self.browser = self.pw.chromium.launch(headless=True, args=['--ignore-certificate-errors-spki-list=' + pin],
                    **({'executable_path': probe.config['browser']} if probe.config.get('browser') else {}))
                self.context = self.browser.new_context(viewport={'width': 1280, 'height': 900}, accept_downloads=True)
                self.version = self.browser.version
                self.context.tracing.start(screenshots=True, snapshots=True, sources=True)
                self.context.route('**/*', self.guard)
                self.page = self.context.new_page()
                self.page.on('pageerror', lambda e: self.errors.append(str(e)))
                self.page.on('response', self.record)
                self.page.goto(self.base, wait_until='networkidle')
                if self.owner == 'hub':
                    self.page.locator('#credential').set_input_files({'name': 'task-token.txt', 'mimeType': 'text/plain', 'buffer': server.token.encode()})
                    expect(self.page.locator('#workspace')).to_be_visible()
                    self.page.wait_for_load_state('networkidle')
                else:
                    self.page.locator('nav [data-tab=documents]').click()
                return self

        browser = InstalledBrowser(server, evidence)
        browser.base = self.address[role]
        self.save('browser-tls-' + phase + '-' + role, {'certificate_sha256': sha(self.ca.read_bytes()),
            'spki_sha256_base64': pin, 'trust': 'Only task certificate SPKI; no blanket HTTPS bypass'})
        return browser

    def browser_formats(self, phase):
        from playwright.sync_api import expect
        for role in ('a', 'hub'):
            with self.browser(role, phase) as browser:
                for item in (i for i in self.items if role == 'a' or i['role'] == role):
                    found = browser.search(item['project'], item['query'], remote=role == 'a' and item['role'] == 'hub')
                    assert len(found['results']) == 1 and found['results'][0]['id'] == item['id']
                    assert found['results'][0]['origin'] == self.expected_origin(item)
                    key = 'web_hit_' + role
                    if key not in item:
                        item[key] = found['results'][0]
                    assert found['results'][0]['reference'] == item[key]['reference']
                    default = browser.read()
                    hit = found['results'][0]
                    assert (default['start'], default['end']) == (hit['start'], hit['end'])
                    assert default['text'] == item['snapshot']['text'][default['start']:default['end']]
                    value = browser.text_range(0, len(item['snapshot']['text']))
                    self.text(value, item)
                    assert value == item['snapshot']
                    node = browser.page.locator('#doc-reader-text' if role == 'a' else '#hub-read-text')
                    expect(node).to_be_visible()
                    assert node.text_content() == value['text']
                    browser.screenshot(item['label'] + '-text')
                    seen = []
                    for summary in value['tables']:
                        browser.page.locator('#' + browser.prefix + '-table-select').select_option(summary['table_id'])
                        table = browser.table_range((1, summary['rows'], 1, summary['columns']))
                        matches = [t for t in item['truth']['tables'] if self.table_oracle(table, t)
                                   and all(table['location'].get(k) == v for k, v in t['location'].items())]
                        assert len(matches) == 1
                        self.table(table, matches[0], item, summary)
                        visible = browser.page.locator('#' + browser.prefix + '-table-cells').inner_text()
                        assert all(str(c['text']) in visible for c in table['cells'] if c['text'])
                        seen.append(table)
                    assert len(seen) == len(item['truth']['tables'])
                    info = browser.info()
                    self.original_info(info, item)
                    browser.download(browser.page.locator('#' + browser.prefix + '-original-download'), item)
                self.save('web-' + phase + '-' + role, {'ids': [i['id'] for i in self.items if i['role'] == role],
                    'events': browser.events, 'errors': browser.errors})

    def browser_uploads(self):
        from playwright.sync_api import expect
        self.phase = 'explicit-upload'
        for role in ('a', 'hub'):
            with self.browser(role, 'uploads') as browser:
                for group, project in enumerate(self.projects[role][:2]):
                    expect(browser.page.locator('#' + browser.prefix + '-upload-files')).to_be_enabled(timeout=45000)
                    browser.project(project, library=True)
                    own = []
                    for kind in ('docx', 'xlsx', 'nativepdf', 'ocrpdf'):
                        prefix = 'LOCAL' if role == 'a' else 'HUB'
                        variant = 'DELTA' if group == 0 else 'GAMMA'
                        label = prefix + ('SCAN' + variant if kind == 'ocrpdf' else 'WEB' + variant + kind.upper())
                        if kind == 'nativepdf':
                            label = ('L' if role == 'a' else 'H') + 'W' + ('A' if group == 0 else 'B')
                        item = self.material(kind, label, ('alpha' if group == 0 else 'beta') if kind == 'ocrpdf' else None)
                        item.update(role=role, project=project, acquisition='chooser' if group == 0 else 'drop')
                        own.append(item)
                    files = [{'name': 'same.' + i['format'], 'mimeType': 'application/octet-stream', 'buffer': i['raw']} for i in own]
                    expect(browser.page.locator('#' + browser.prefix + '-upload-files')).to_be_enabled(timeout=45000)
                    expect(browser.page.locator('#doc-library-project' if role == 'a' else '#hub-project')).to_have_value(str(project['id']))
                    event_start = len(browser.events)
                    if group == 0:
                        with browser.page.expect_file_chooser() as chosen:
                            browser.page.locator('#' + browser.prefix + '-upload-files').click()
                        chosen.value.set_files(files)
                    else:
                        transfer = browser.page.evaluate_handle('''files=>{const dt=new DataTransfer();for(const f of files){dt.items.add(new File([Uint8Array.from(atob(f.base64),c=>c.charCodeAt(0))],f.name,{type:'application/octet-stream'}));}return dt}''',
                            [{'name': f['name'], 'base64': base64.b64encode(f['buffer']).decode()} for f in files])
                        browser.page.locator('#doc-upload-drop' if role == 'a' else '#hub-drop').dispatch_event('drop', {'dataTransfer': transfer})
                        transfer.dispose()
                    expect(browser.page.locator('#' + browser.prefix + '-upload-results li')).to_have_count(4, timeout=45000)
                    until = time.monotonic() + 60
                    while True:
                        assert not any('失败' in s for s in browser.page.locator('#' + browser.prefix + '-upload-results li').all_text_contents())
                        rows = self.request(role, self.path(role, '/documents/library?project_id=' + str(project['id'])))
                        events = browser.events[event_start:]
                        ready = []
                        for item in own:
                            starts = [e for e in events if e['method'] == 'POST' and e['path'] == self.path(role, '/documents/uploads') and e['request'].get('sha256') == item['sha256']]
                            if not starts:
                                continue
                            assert len(starts) == 1 and starts[0]['status'] == 200
                            upload_id = json.loads(browser.responses[starts[0]['sha256']])['upload_id']
                            commits = [e for e in events if e['method'] == 'POST' and e['path'] == self.path(role, '/documents/uploads/' + upload_id + '/commit')]
                            if not commits:
                                continue
                            assert len(commits) == 1 and commits[0]['status'] == 200
                            receipt = json.loads(browser.responses[commits[0]['sha256']])
                            found = [r for r in rows if r['id'] == receipt['document_id']]
                            if not found:
                                continue
                            assert len(found) == 1
                            entry = found[0]
                            assert entry['latest_attempt']['capture_id'] == receipt['capture_id'] and entry['latest_attempt']['attempt_id'] == receipt['attempt_id']
                            if entry['latest_attempt']['status'] in {'ready', 'partial', 'failed'}:
                                assert entry['latest_attempt']['status'] == 'ready', entry
                                publication = entry.get('published_snapshot')
                                if not publication or publication['capture_id'] != receipt['capture_id']:
                                    continue
                                assert publication['status'] == 'ready' and entry['version'] == entry['processing_version'] == 1
                                assert entry['sha256'] == item['sha256'] and entry['project_ids'] == [project['id']]
                                item.update(id=entry['id'], entry=entry, path=Path(entry['path']))
                                ready.append(item)
                        if len(ready) == 4:
                            break
                        assert time.monotonic() < until, rows
                        browser.page.wait_for_timeout(100)
                    assert len({i['id'] for i in own}) == 4
                    for item in own:
                        row = browser.page.locator('#doc-library-list .result' if role == 'a' else '#hub-library-list .result').filter(has_text=item['id'])
                        expect(row).to_have_count(1)
                        expect(row).to_contain_text('ready', timeout=15000)
                    browser.screenshot(('chooser' if group == 0 else 'drop') + '-published')
                    expect(browser.page.locator('#' + browser.prefix + '-upload-files')).to_be_enabled(timeout=45000)
                    self.items.extend(own)
                    self.register_source_paths()
                self.save('web-uploads-' + role, {'ids': [i['id'] for i in self.items if i['role'] == role and i['acquisition'] != 'path'],
                    'events': browser.events, 'errors': browser.errors})

    def cleanup(self):
        self.phase = 'cleanup'
        return super().cleanup()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target-config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.target_config = args.target_config.resolve()
    config = json.loads(args.target_config.read_text(encoding='utf-8'))
    probe = FormatProbe(config, args.output.resolve())
    cwd = probe.out / 'non-source-cwd'
    cwd.mkdir()
    os.chdir(cwd)
    bindings = probe.version_bindings()
    for name, expected in bindings.items():
        raw = (ROOT / name).read_bytes()
        assert sha(raw) == expected
        probe.keep('source-snapshot/' + name, raw)
    probe.save('execution-source-bindings', {'files': bindings, 'target_config_sha256': sha(args.target_config.resolve().read_bytes()),
        'controller_cwd': str(cwd), 'actual_product_environment': {k: probe.env('a').get(k)
            for k in ('PATH', 'PYTHONUTF8', 'PYTHONIOENCODING', 'PYTHONPATH', 'VIRTUAL_ENV')}})
    result = None
    try:
        probe.prepare_formats()
        if config.get('browser_uploads'):
            probe.browser_uploads()
        if config.get('read_guards'):
            from document_formats_protocol_guards import controls, events, assert_read_only
            controls(probe)
            probe.phase = 'read-only'
            reading_start = len(events(probe))
        probe.complete_cli_http('before-restart')
        probe.local_hub_cli('before-restart')
        probe.mcp_formats('before-restart')
        if config.get('browser_checks'):
            probe.browser_formats('before-restart')
        if config.get('read_guards'):
            assert_read_only(probe, reading_start)
        probe.phase = 'service-control'
        for role in ('a', 'hub'):
            probe.stop(role)
        for item in probe.items:
            item['path'].unlink()
        if config.get('read_guards'):
            reading_start = len(events(probe))
        for role in ('hub', 'a'):
            probe.start(role)
        probe.phase = 'read-only'
        probe.complete_cli_http('after-restart-offline')
        probe.local_hub_cli('after-restart-offline')
        probe.mcp_formats('after-restart-offline')
        if config.get('browser_checks'):
            probe.browser_formats('after-restart-offline')
        if config.get('read_guards'):
            assert_read_only(probe, reading_start)
        assert probe.version_bindings() == bindings
        result = {'status': 'passed', 'kind': '008 installed path acquisition and CLI/HTTP/stdio foreground subset',
                  'documents': len(probe.items), 'actual_actor': probe.actor(), 'finished_at': now(),
                  'browser_reads': bool(config.get('browser_checks')),
                  'browser_uploads': bool(config.get('browser_uploads')),
                  'read_only_guards': bool(config.get('read_guards')),
                  'not_covered': ['all lifecycle', 'native service', 'cross-OS transfer']}
    except BaseException:
        probe.save('failure', {'traceback': traceback.format_exc(), 'at': now()})
        raise
    finally:
        probe.cleanup()
    probe.save('result', result)


if __name__ == '__main__':
    main()
