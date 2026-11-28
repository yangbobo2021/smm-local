"""Actual SCM Web DOCX/XLSX/PDF/OCR capability with a real standard client.

This supplements the Word import red/green. It is not complete Windows H1-H5.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(Path(__file__).resolve().parent), str(ROOT / 'tests')]
import hub_documents_scm_platform as scm
from document_formats_scm_word import WordAdministrator, WordClient
from document_formats_installed_protocols import FormatProbe
from document_formats_installed_lifecycle import snapshot
from document_formats_lifecycle_readback import fields, TEXT, TABLE, INFO
from document_formats_windows_identity import sample_process, validate_chain
from hub_documents_platform import now


class FormatsAdministrator(WordAdministrator):
    def __init__(self, config, output):
        super().__init__(config, output)
        self.materials = json.loads(Path(config['materials']).read_text(encoding='utf-8'))
        self.monitor_stop = threading.Event()
        self.monitor_thread = None
        self.ocr_records, self.ocr_errors = [], []
        # Only the frozen task runtime/data become readable to LocalService;
        # protected Hub state and service-code write permissions are unchanged.
        for directory in {Path(self.materials['ocr_executable']).parent.parent,
                          Path(self.materials['ocr_data_dir'])}:
            self.run('grant-task-ocr-read', ['icacls.exe', directory, '/grant', '*S-1-5-19:(OI)(CI)RX', '/T'])

    def service_identity(self):
        value = super().service_identity()
        import psutil
        self.sampled_service = sample_process(psutil.Process(self.service_pid))
        assert self.sampled_service['sid'] == 'S-1-5-19' and self.sampled_service['session_id'] == 0
        if self.monitor_thread is None:
            self.monitor_thread = threading.Thread(target=self.monitor_ocr)
            self.monitor_thread.start()
        return value

    def monitor_ocr(self):
        import psutil
        observed = set()
        while not self.monitor_stop.wait(.01):
            pid = self.service_pid
            if pid is None:continue
            try:children = psutil.Process(pid).children(recursive=True)
            except (psutil.NoSuchProcess, psutil.ZombieProcess):continue
            for process in children:
                try:
                    stamp = (process.pid, process.create_time())
                    if stamp in observed:continue
                    argv = process.cmdline()
                    if not os.path.samefile(process.exe(), self.materials['ocr_executable']):continue
                    if '--tessdata-dir' not in argv or '-l' not in argv:continue
                    source = Path(argv[1]).resolve()
                    relative = source.relative_to((self.hub_state / '.document-snapshots/tasks').resolve())
                    aid = relative.parts[0]
                    assert len(aid) == 32 and all(c in '0123456789abcdef' for c in aid)
                    worker = psutil.Process(process.ppid())
                    worker_argv = worker.cmdline()
                    assert 'smm_hub._archive.document_worker' in worker_argv
                    assert worker_argv[worker_argv.index('--task-token') + 1] == aid
                    identity, parent = sample_process(process), sample_process(worker)
                    assert identity['parent_pid'] == worker.pid
                    assert identity['argv'] == argv and parent['argv'] == worker_argv
                    ancestors = [p.pid for p in worker.parents()]
                    service = sample_process(psutil.Process(pid))
                    assert service['creation_filetime'] == self.sampled_service['creation_filetime']
                    validate_chain(identity, parent, service, sid='S-1-5-19', session=0,
                        attempt_id=aid, ancestors=ancestors)
                    active = json.loads((self.hub_state / '.document-snapshots/tasks/active.json').read_text())
                    assert active['worker']['pid'] == worker.pid
                    assert active['worker']['created'] == worker.create_time()
                    assert abs(active['worker']['created'] - parent['created']) < .001
                    assert active['windows_job']['atomic'] is True and active['gate_open'] is True
                    assert process.create_time() == stamp[1] and process.is_running()
                    self.ocr_records.append({'at': now(), 'attempt_id': aid, 'ocr': identity,
                        'created': stamp[1], 'executable': process.exe(), 'argv': argv,
                        'worker': parent, 'worker_created': worker.create_time(), 'worker_argv': worker_argv,
                        'service': service, 'service_pid': pid, 'ancestors': ancestors,
                        'supervision': active})
                    observed.add(stamp)
                    self.save('actual-ocr-process-identities', self.ocr_records)
                except (psutil.NoSuchProcess, psutil.ZombieProcess):continue
                except OSError as error:
                    # An exited short-lived process is not a token sample.
                    try:alive = process.is_running()
                    except psutil.NoSuchProcess:alive = False
                    if alive:
                        self.ocr_errors.append({'pid': process.pid, 'error': str(error),
                            'winerror': getattr(error, 'winerror', None), 'at': now()})
                        self.save('ocr-observer-errors', self.ocr_errors)
                except BaseException as error:
                    self.ocr_errors.append({'pid': process.pid, 'type': type(error).__name__,
                        'error': str(error), 'at': now()})
                    self.save('ocr-observer-errors', self.ocr_errors)

    def rpc(self, request):
        operation = request['operation']
        if operation == 'formats_status':
            assert set(request) == {'operation'}
            return self.cli('hub', 'documents', 'processing-status', '--check')
        if operation == 'formats_configure':
            assert set(request) == {'operation', 'expected_revision'}
            revision = request['expected_revision']
            assert type(revision) is int and revision >= 0
            return self.cli('hub', 'documents', 'processing-configure', '--expected-revision', revision,
                '--ocr-executable', self.materials['ocr_executable'], '--ocr-data-dir', self.materials['ocr_data_dir'],
                '--languages', 'chi_sim+eng')
        if operation == 'formats_ocr_observations':
            assert set(request) == {'operation'}
            return {'records': list(self.ocr_records), 'errors': list(self.ocr_errors)}
        return super().rpc(request)

    def stop_monitor(self):
        self.monitor_stop.set()
        if self.monitor_thread is not None:self.monitor_thread.join(timeout=10)
        assert self.monitor_thread is None or not self.monitor_thread.is_alive()
        self.save('ocr-observer-finished', {'records': len(self.ocr_records), 'errors': self.ocr_errors})


class FormatsClient(FormatProbe, WordClient):
    def __init__(self, config, output):
        super().__init__({**config, 'read_guards': False}, output)


def ordinary(config, output):
    from playwright.sync_api import expect
    from document_formats_lifecycle_readback import visible_table
    probe = FormatsClient(config, output)
    result = None
    try:
        probe.check_install()
        probe.start('hub')
        info = probe.request('hub', '/v1/info')
        probe.hub_context = {key: info[key] for key in ('hub_id', 'document_epoch')}
        probe.archive_identities = {'hub': probe.rpc('archive_identity')['archive_id']}
        probe.device_identities = {'hub': info['hub_id']}
        status = probe.rpc('formats_status')
        configured = probe.rpc('formats_configure', expected_revision=status['config']['revision'])
        assert configured['ocr']['ready'] is True
        # This is explicitly an administrator maintenance probe. Actual OCR
        # identity/access are established separately from real service children.
        probe.save('administrator-component-probe', configured)
        with probe.browser('hub', 'scm-formats-project') as browser:
            browser.page.locator('#hub-project-name').fill('008 SCM formats Web project')
            project = browser.action(None, browser.page.locator('#hub-project-create').click, '/projects')
            browser.screenshot('actual-created-project')
        assert project['owner'] == info['hub_id']
        probe.projects = {'hub': [project], 'a': []}
        probe.browser_uploads(roles=('hub',), project_overrides={'hub': [project]},
            phase='scm-formats-uploads', label_namespace='S')
        assert len(probe.items) == 4 and {i['kind'] for i in probe.items} == {'docx', 'xlsx', 'nativepdf', 'ocrpdf'}
        saved = {}
        for item in probe.items:
            item.update(version=1, processing_version=1)
            saved[item['id']] = snapshot(probe, item)
        with probe.browser('hub', 'scm-formats-read') as browser:
            browser.page.locator('#hub-limit').select_option('50')
            for item in probe.items:
                canonical = saved[item['id']]
                found = browser.search(project, item['query'])
                own = [hit for hit in found['results'] if hit['origin'] == probe.expected_origin(item)]
                assert len(own) == 1
                row = browser.page.locator('#hub-results .result').filter(has_text=item['id'])
                default = browser.action('text', row.get_by_role('button', name='读取原文', exact=True).click)
                assert (default['start'], default['end']) == (own[0]['start'], own[0]['end'])
                assert default['text'] == canonical['text']['text'][own[0]['start']:own[0]['end']]
                value = browser.text_range(0, canonical['hit']['text_length'])
                assert fields(value, TEXT) == fields(canonical['text'], TEXT)
                node = browser.page.locator('#hub-read-text')
                expect(node).to_be_visible()
                assert node.text_content() == canonical['text']['text']
                for table in canonical['tables']:
                    browser.page.locator('#hub-table-select').select_option(table['table_id'])
                    value = browser.table_range((1, table['rows'], 1, table['columns']))
                    assert fields(value, TABLE) == fields(table, TABLE)
                    visible_table(browser, table)
                assert fields(browser.info(), INFO) == fields(canonical['info'], INFO)
                browser.download(browser.page.locator('#hub-original-download'), item)
                browser.screenshot(item['label'] + '-verified')
        observations = probe.rpc('formats_ocr_observations')
        assert not observations['errors'], observations['errors']
        target = next(i for i in probe.items if i['kind'] == 'ocrpdf')
        aid = target['entry']['latest_attempt']['attempt_id']
        own = [record for record in observations['records'] if record['attempt_id'] == aid]
        assert own, 'No actual service OCR process token observed for the published OCR document'
        probe.save('service-ocr-evidence', {'document_id': target['id'], 'attempt_id': aid,
            'actual_process_tokens': own, 'observer_errors': observations['errors']})
        result = {'status': 'passed', 'scope': 'actual SCM four-format Web capability component only',
            'actor': probe.actor(), 'documents': 4, 'actual_ocr_identity_samples': len(own),
            'finished_at': now(), 'not_covered': ['complete H1-H5', 'CLI path', 'Local projection', 'service restart', 'failure recovery']}
    except BaseException:
        probe.save('failure', {'traceback': traceback.format_exc(), 'at': now()})
        raise
    finally:probe.cleanup()
    probe.save('result', result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target-config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.target_config.read_text(encoding='utf-8-sig'))
    if config.get('external_hub'):
        ordinary(config, args.output.resolve())
    else:
        managers = []
        def factory(value, output):
            manager = FormatsAdministrator(value, output)
            managers.append(manager)
            return manager
        try:
            scm.administrator(config, args.output.resolve(), manager_factory=factory,
                runner=Path(__file__).resolve(), wrapper=Path(__file__).with_name('document_formats_installed_standard_user.ps1'))
        finally:
            for manager in managers:manager.stop_monitor()
