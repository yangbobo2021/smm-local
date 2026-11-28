"""Actual installed wrong-end management refuses before content work/state changes."""
from __future__ import annotations
import base64
from uuid import uuid4
from document_formats_upload_transport import rows


def verify(probe, projected):
    from document_formats_installed_lifecycle import snapshot, unchanged_publication
    from document_formats_protocol_guards import events, assert_read_only
    local = next(i for i in probe.items if i['role'] == 'a' and i['kind'] == 'docx'
                 and i['project']['id'] == probe.projects['a'][0]['id'])
    native = next(i for i in probe.items if i['role'] == 'hub' and i['kind'] == 'docx')
    received = next(r for r in rows(probe, 'hub').values() if r['origin'] == probe.expected_origin(local))
    source = next(s for s in probe.cli('hub', 'documents', 'sources')
        if (s.get('origin') or {}).get('device_id') == probe.device_identities['a']
        and projected['id'] in s['project_ids'])
    before = {role: rows(probe, role) for role in ('a', 'hub')}
    snapshots = {i['id']: snapshot(probe, {**i, 'version': i.get('version', 1),
        'processing_version': i.get('processing_version', 1)}) for i in (local, native)}
    probe.phase = 'read-only'
    start = len(events(probe))
    for action, args in [('set', [source['id'], '--project-id', projected['id']]),
                         ('remove', [source['id']]), ('refresh', ['--source-id', source['id']])]:
        probe.cli('hub', 'documents', action, *args, code=2)
        assert '设备同步投影只读' in probe.calls[-1]['stderr']
    for role, item, project in [('hub', {**local, 'id': received['id']}, projected),
                                ('a', native, native['project'])]:
        creator = before['a'][local['id']] if role == 'hub' else before['hub'][native['id']]
        latest = creator['latest_attempt']
        if role == 'hub':
            assert received['retry_target'] is None and received['latest_attempt'] is None
        capture = received['published_snapshot']['capture_id'] if role == 'hub' else latest['capture_id']
        # This is a well-formed current project ID/key from the other owner,
        # not an invalid numeric ID masquerading as an ownership check.
        denied = probe.request(role, probe.path(role, '/documents/uploads'), probe.body(role,
            project_id=project['id'], project_key=project['source_key'],
            submission_id=uuid4().hex, name='wrong-owner.docx', sha256=item['sha256'],
            bytes=len(item['raw'])), code=400)
        assert ('仅Hub创建的项目可在Hub管理文档' if role == 'hub' else '本机项目身份已变化') in denied['detail']
        target_project = projected if role == 'hub' else probe.projects['a'][0]
        key = target_project['source_key'] if role == 'hub' else target_project['stable_key']
        comparison = dict(project_id=target_project['id'], project_key=key,
            expected_version=item.get('version', 1), expected_processing_version=item.get('processing_version', 1),
            expected_revision=creator['source_revision'], capture_id=capture,
            expected_attempt_id=latest['attempt_id'])
        denied = probe.request(role, probe.path(role, '/documents/library/' + item['id']),
            probe.body(role, **comparison), method='DELETE', code=400)
        assert ('仅Hub创建的项目可在Hub管理文档' if role == 'hub' else '管理文档不存在或已移除') in denied['detail']
        update = {k: v for k, v in comparison.items() if k in {
            'project_id', 'project_key', 'expected_version', 'expected_revision'}}
        denied = probe.request(role, probe.path(role, '/documents/library/' + item['id']),
            probe.body(role, **update, submission_id=uuid4().hex,
                content_base64=base64.b64encode(b'valid independent UTF-8 update').decode()), method='PUT', code=400)
        assert ('仅Hub创建的项目可在Hub管理文档' if role == 'hub' else '管理文档不存在或已移除') in denied['detail']
        probe.cli(role, 'documents', 'reprocess', '--document-id', item['id'],
            '--capture-id', capture, '--expected-attempt-id', latest['attempt_id'],
            '--expected-version', item.get('version', 1),
            '--expected-processing-version', item.get('processing_version', 1), code=2)
        reason = probe.calls[-1]['stderr']
        assert any(message in reason for message in (
            ['设备同步投影只读', '当前捕获没有有效采集来源'] if role == 'hub' else ['文档不存在']))
    assert_read_only(probe, start)
    assert {role: rows(probe, role) for role in ('a', 'hub')} == before
    for item in (local, native):
        unchanged_publication(snapshot(probe, {**item, 'version': item.get('version', 1),
            'processing_version': item.get('processing_version', 1)},
            reference=snapshots[item['id']]['reference']), snapshots[item['id']])
    probe.save('lifecycle-wrong-end-management', {'source': source['id'], 'received_id': received['id'],
        'local_id': local['id'], 'hub_native_id': native['id'], 'state_unchanged': True,
        'scope': 'Representative ready source/project ownership refusals, wrong-end library document absence, and reprocess absence/no-receiver-authorization at actual CLI and authenticated HTTP; a projection has no legitimate receiver retry target/AID. Full comparison/state combinations remain C1.'})
