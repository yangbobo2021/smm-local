"""Receive creator-produced results without importing any document processor."""
from __future__ import annotations
import json
from ._archive import (
    BlobTransfers, DocumentSnapshots, processed_validate, processed_encode,
    processed_sha, document_identity, document_integer, digest, utcnow,
)

CONTEXT = ('hub_id', 'document_epoch', 'device_id', 'archive_id', 'project_key', 'generation')
PROCESSED_FIELDS = {'processing_version', 'result_sha256', 'result_bytes', 'raw_bytes', 'format', 'profile_sha256', 'capture_id', 'schema'}
BASE_FIELDS = {'document_id', 'version', 'sha256', 'text_sha256', 'path', 'display_name', 'captured_at', 'captured_by_source_id', 'capture_sequence'}


class ProcessedDocuments:
    def __init__(self, hub):
        self.hub = hub
        self.snapshots = hub.documents.snapshots
        self.transfers = BlobTransfers(self.snapshots)
        with hub.db.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS hub_processed_stages(
                device_id TEXT, archive_id TEXT, document_id TEXT, version INTEGER,
                processing_version INTEGER, result_sha256 TEXT, payload TEXT NOT NULL,
                PRIMARY KEY(device_id,archive_id,document_id,version,processing_version))''')

    def _allowed(self, binding):
        with self.hub.db.connect() as c:
            return self.hub._control_row(c, binding)

    @staticmethod
    def metadata(value):
        if not isinstance(value, dict) or set(value) != BASE_FIELDS | PROCESSED_FIELDS:
            raise ValueError('已处理文档元信息字段无效')
        for key in ('document_id', 'capture_id', 'captured_by_source_id'):
            document_identity(value[key], key)
        for key in ('version', 'processing_version', 'capture_sequence', 'raw_bytes', 'result_bytes'):
            document_integer(value[key], key)
        for key in ('sha256', 'text_sha256', 'result_sha256', 'profile_sha256'):
            if not isinstance(value[key], str) or len(value[key]) != 64 or any(ch not in '0123456789abcdef' for ch in value[key]):
                raise ValueError('处理文档摘要无效')
        if value['schema'] != 'processed_documents_v1' or value['format'] not in {'docx', 'xlsx', 'pdf'}:
            raise ValueError('不支持的处理schema或格式')
        for key in ('path', 'display_name', 'captured_at'):
            if not isinstance(value[key], str) or not value[key] or '\0' in value[key]:
                raise ValueError('处理文档显示信息无效')
        return value

    def begin(self, p):
        if set(p) != set(CONTEXT) | {'submission_id', 'document'}:
            raise ValueError('处理文档暂存请求字段无效')
        document_identity(p['submission_id'])
        value = self.metadata(p['document'])
        with self.hub.guard.hold():
            self._allowed(p)
            return self.transfers.begin(p, {
                'raw': {'sha256': value['sha256'], 'bytes': value['raw_bytes']},
                'results': {'sha256': value['result_sha256'], 'bytes': value['result_bytes']},
            })

    def part(self, transfer_id, kind, offset, raw, expected_sha):
        binding = self.transfers.binding(transfer_id)
        with self.hub.guard.hold():
            self._allowed(binding)
            return self.transfers.part(transfer_id, kind, offset, raw, expected_sha)

    def _validate_finished(self, binding, raw, result_raw):
        value = self.metadata(binding['document'])
        result = processed_validate(json.loads(result_raw))
        if processed_encode(result) != result_raw:
            raise ValueError('处理结果不是规范化结果字节')
        if result['raw_sha256'] != value['sha256'] or result['format'] != value['format'] or result['text_sha256'] != value['text_sha256'] or processed_sha(processed_encode(result['profile'])) != value['profile_sha256']:
            raise ValueError('原件/结果/profile绑定不匹配')
        return result

    def commit(self, p):
        if set(p) != {'transfer_id'}:
            raise ValueError('处理传输提交字段无效')
        transfer_id = p['transfer_id']
        binding = self.transfers.binding(transfer_id)
        self._allowed(binding)
        # Hash/schema checks and blob I/O happen before the short publication lock.
        binding, result = self.transfers.commit(transfer_id, self._validate_finished)
        value = binding['document']
        with self.hub.guard.hold(), self.hub.db.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            self.hub._control_row(c, binding)
            key = (binding['device_id'], binding['archive_id'], value['document_id'], value['version'], value['processing_version'])
            old = c.execute('SELECT payload FROM hub_processed_stages WHERE device_id=? AND archive_id=? AND document_id=? AND version=? AND processing_version=?', key).fetchone()
            if old:
                previous = json.loads(old[0])
                if any(previous[k] != value[k] for k in ('sha256', 'text_sha256', 'result_sha256', 'profile_sha256', 'format')):
                    raise ValueError('同身份和V/P不能有不同原件或结果')
                if previous['capture_sequence'] > value['capture_sequence']:
                    return {'staged': True, 'document_id': value['document_id'], 'version': value['version'], 'processing_version': value['processing_version']}
            c.execute('INSERT INTO hub_processed_stages VALUES(?,?,?,?,?,?,?) ON CONFLICT(device_id,archive_id,document_id,version,processing_version) DO UPDATE SET payload=excluded.payload', (*key, value['result_sha256'], json.dumps(value, ensure_ascii=False)))
        return {'staged': True, 'document_id': value['document_id'], 'version': value['version'], 'processing_version': value['processing_version']}

    def staged(self, c, p, item):
        row = c.execute('SELECT payload FROM hub_processed_stages WHERE device_id=? AND archive_id=? AND document_id=? AND version=? AND processing_version=?', (p['device_id'], p['archive_id'], item['document_id'], item['version'], item['processing_version'])).fetchone()
        if row is None:
            raise ValueError('完整清单含未暂存的原件/结果')
        value = self.metadata(json.loads(row[0]))
        if any(item[k] != value[k] for k in BASE_FIELDS | PROCESSED_FIELDS):
            raise ValueError('完整清单与处理快照不匹配')
        result = self.snapshots.load_result(value['result_sha256'])
        if result['raw_sha256'] != value['sha256']:
            raise ValueError('处理快照原件绑定不匹配')
        return {**value, 'text': result['text'], 'text_length': result['text_length']}

    def install(self, c, pk, value, p):
        cid = digest([p['device_id'], p['archive_id'], value['capture_id']])[:32]
        existing = c.execute('SELECT * FROM document_captures WHERE id=?', (cid,)).fetchone()
        if existing and (existing['document_pk'] != pk or existing['raw_sha256'] != value['sha256']):
            raise ValueError('接收捕获身份冲突')
        c.execute('INSERT OR IGNORE INTO document_captures VALUES(?,?,?,?,?,?,?)', (cid, pk, value['sha256'], value['raw_bytes'], value['format'], value['capture_sequence'], value['captured_at']))
        c.execute('INSERT INTO document_snapshot_state(document_pk,current_capture,latest_attempt,published_capture,result_sha256,processing_version,profile_sha256,published_status) VALUES(?,?,NULL,?,?,?,?,?) ON CONFLICT(document_pk) DO UPDATE SET current_capture=excluded.current_capture,latest_attempt=NULL,published_capture=excluded.published_capture,result_sha256=excluded.result_sha256,processing_version=excluded.processing_version,profile_sha256=excluded.profile_sha256,published_status=excluded.published_status', (pk, cid, cid, value['result_sha256'], value['processing_version'], value['profile_sha256'], self.snapshots.load_result(value['result_sha256'])['status']))
        c.executemany('INSERT OR IGNORE INTO document_published_blobs(kind,sha256) VALUES(?,?)', [('raw', value['sha256']), ('results', value['result_sha256'])])
