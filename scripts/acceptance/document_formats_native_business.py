"""Real service web creation and interruption of a verified actual OCR process."""
from __future__ import annotations
import os
from pathlib import Path
import time


def web_project(probe):
    from playwright.sync_api import expect
    with probe.browser('hub', 'native-project-creation') as browser:
        browser.page.locator('#hub-project-name').fill('008 Hub native Web project')
        project = browser.action(None, browser.page.locator('#hub-project-create').click, '/projects')
        expect(browser.page.locator('#hub-project')).to_have_value(str(project['id']))
        browser.screenshot('actual-created-project')
        probe.save('native-web-created-project', {'project': project, 'events': browser.events})
    assert project['owner'] == probe.hub_context['hub_id']
    probe.browser_uploads(roles=('hub',), project_overrides={'hub': [project]},
        phase='native-web-created-uploads', label_namespace='C')


def dependency_isolation(probe, role, failed):
    if role != 'hub':return
    from document_formats_installed_lifecycle import snapshot
    from document_formats_protocol_guards import events, assert_read_only
    assert failed['latest_attempt']['status'] == 'failed'
    assert 'chi_sim.traineddata' in failed['latest_attempt']['error']
    probe.phase = 'read-only'
    start = len(events(probe))
    documents = [i for i in probe.items if i['role'] == 'hub' and i['kind'] in {'docx', 'xlsx', 'nativepdf'}]
    assert {i['kind'] for i in documents} == {'docx', 'xlsx', 'nativepdf'}
    for item in documents:
        snapshot(probe, {**item, 'version': item.get('version', 1),
            'processing_version': item.get('processing_version', 1)})
    item = next(i for i in probe.items if i['role'] == 'a' and i['kind'] == 'ocrpdf'
                and i['project']['id'] == probe.projects['a'][0]['id'])
    received = snapshot(probe, {**item, 'read_role': 'hub', 'read_project': probe.native_projected_project,
        'version': item.get('version', 1), 'processing_version': item.get('processing_version', 1)})
    assert_read_only(probe, start)
    serial = getattr(probe, 'native_isolation_serial', 0) + 1
    probe.native_isolation_serial = serial
    probe.save('native-missing-language-isolation-' + str(serial), {'native_documents': [i['id'] for i in documents],
        'received_scan_origin': received['hit']['origin'], 'read_only_observation_start': start,
        'actual_service_failure': failed['latest_attempt']})
    probe.phase = 'archive-only'


def interrupted_ocr(probe):
    import psutil
    from document_formats_installed_lifecycle import upload, wait, rows, library_entry, snapshot, retry, unchanged_publication
    from document_formats_platform import spawn_identity, matching_process
    records = []
    for index, action in enumerate(('retain', 'remove', 'replace')):
        item = probe.material('ocrpdf', 'NATIVEOCR' + action.upper())
        item.update(role='hub', project=probe.projects['hub'][0], version=1, processing_version=1, query='73428')
        receipt = upload(probe, item, item['raw'], await_terminal=False)
        item['id'] = receipt['document_id']
        deadline = time.monotonic() + 30
        engine = None
        while engine is None:
            assert time.monotonic() < deadline, 'No actual OCR process observed'
            service = psutil.Process(probe.service_pid)
            for process in service.children(recursive=True):
                candidate=None
                try:
                    argv = process.cmdline()
                    if not os.path.samefile(process.exe(), probe.materials['ocr_executable']):continue
                    if '--tessdata-dir' not in argv or '-l' not in argv:continue
                    source = Path(argv[1]).resolve()
                    task = probe.hub_state / '.document-snapshots/tasks' / receipt['attempt_id']
                    if not source.is_relative_to(task.resolve()):continue
                    candidate = {'stamp': spawn_identity(process), 'argv': argv, 'exe': process.exe(),
                              'uid': process.uids().effective, 'source': str(source)}
                    assert candidate['uid'] == os.getuid() != 0
                    worker=psutil.Process(process.ppid())
                    candidate['worker']={'stamp':spawn_identity(worker),'uid':worker.uids().effective,
                        'exe':worker.exe(),'argv':worker.cmdline()}
                    assert candidate['worker']['uid']==candidate['uid']
                    command=candidate['worker']['argv']
                    assert 'smm_hub._archive.document_worker' in command
                    assert command[command.index('--task-token')+1]==receipt['attempt_id']
                    candidate['service']=dict(probe.service_events[-1])
                    assert service.create_time()==candidate['service']['created']
                    process.suspend()
                    assert process.create_time()==candidate['stamp']['created']
                    probe.save('native-actual-held-ocr-'+receipt['attempt_id'],
                        {'receipt':receipt,'action':action,'actual_ocr':candidate})
                    engine=candidate
                    break
                except (psutil.NoSuchProcess, FileNotFoundError):
                    # Never continue with a partially sampled held process.
                    # A still-owned suspended OCR must be released first.
                    if candidate is not None:
                        held=matching_process(candidate['stamp'])
                        if held is not None:held.resume()
                    continue
            if engine is None:time.sleep(.002)
        current = library_entry(probe, 'hub', item['id'])
        assert current['published_snapshot'] is None and current['version'] == current['processing_version'] == 0
        assert current['latest_attempt']['capture_id'] == receipt['capture_id']
        assert current['latest_attempt']['attempt_id'] == receipt['attempt_id']
        assert current['latest_attempt']['status'] in {'pending','processing'}
        item['path'] = Path(current['path'])
        original_attempt = dict(current['latest_attempt'])
        # Keep a second, independent published document readable while real
        # OCR is in flight. The OS suspension changes timing, not OCR output.
        other = next(i for i in probe.items if i['role'] == 'hub' and i['kind'] == 'docx' and i.get('version') == 2)
        saved = snapshot(probe, other)
        if action == 'remove':
            probe.request('hub', '/v1/documents/library/' + item['id'], probe.body('hub',
                project_id=item['project']['id'], project_key=item['project']['source_key'],
                expected_version=0, expected_processing_version=0, expected_revision=current['source_revision'],
                capture_id=receipt['capture_id'], expected_attempt_id=receipt['attempt_id']), method='DELETE')
        elif action == 'replace':
            replacement = probe.material('nativepdf', 'R' + str(index))
            finished = upload(probe, item, replacement['raw'], replacement=current)
            assert finished['latest_attempt']['status'] == 'ready'
            assert finished['latest_attempt']['capture_id'] != receipt['capture_id']
            item.update({key: replacement[key] for key in ('raw', 'truth', 'sha256', 'query', 'kind')})
            item['path'] = Path(finished['path'])
        import threading
        from document_formats_protocol_guards import events
        failures = []
        def stop_service():
            try:probe.stop('hub')
            except BaseException as error:failures.append(error)
        stopper = threading.Thread(target=stop_service)
        probe.pending_native_stop=stopper
        event_start = len(events(probe))
        try:
            if action=='retain':assert matching_process(engine['stamp']) is not None
            stopper.start()
            until, dispatch = time.monotonic() + 15, None
            while dispatch is None:
                for event in events(probe)[event_start:]:
                    argv = event.get('argv')
                    if event['kind'] != 'child-start' or not isinstance(argv, list):continue
                    if ('launchctl' in argv and 'bootout' in argv and 'system/' + probe.label in argv) or (
                            'systemctl' in argv and 'disable' in argv and '--now' in argv and probe.unit in argv):
                        dispatch = event
                        break
                assert time.monotonic() < until and not failures, failures
                if dispatch is None:time.sleep(.01)
            if action != 'retain':
                held = matching_process(engine['stamp'])
                if held is not None:held.resume()
            # Retain keeps this one-page actual OCR in flight through native stop.
            # Its real bounded OCR timeout can fail the attempt during graceful
            # shutdown; that is a supported saved-capture explicit retry path.
            # No ready publication before restart is accepted as an interruption.
            stopper.join(timeout=60)
            assert not stopper.is_alive() and not failures, failures
        finally:
            # Finish the owned native stop before outer cleanup can issue a
            # second disable if an observation assertion fails mid-stop.
            if stopper.is_alive():stopper.join(timeout=60)
        stopped = matching_process(engine['stamp'])
        assert stopped is None, 'Old OCR process survived actual service stop'
        offline = {row['id']: row for row in probe.cli('hub', 'documents', 'files')}
        if action == 'retain':
            offline_entry = offline[item['id']]
            assert offline_entry['published_snapshot'] is None
            assert offline_entry['version'] == offline_entry['processing_version'] == 0
            assert offline_entry['latest_attempt']['status'] in {'pending', 'processing', 'failed'}
            assert offline_entry['latest_attempt']['capture_id'] == receipt['capture_id']
        elif action == 'remove':
            assert item['id'] not in offline
        else:
            assert offline[item['id']]['published_snapshot']['capture_id'] != receipt['capture_id']
        item['path'].unlink(missing_ok=True)
        pending=action=='retain' and offline_entry['latest_attempt']['status'] in {'pending','processing'}
        resume_start=len(events(probe))
        if pending:
            pending_ids={row['latest_attempt']['attempt_id'] for row in offline.values()
                if (row.get('latest_attempt') or {}).get('status') in {'pending','processing'}}
            assert pending_ids=={receipt['attempt_id']}
            probe.native_resume_aid=receipt['attempt_id']
            probe.resume_attempt_path.write_text(receipt['attempt_id'])
        probe.start('hub')
        if not pending:probe.phase='archive-only'
        if action == 'retain':
            try:finished = wait(probe, 'hub', item['id'])
            finally:
                probe.native_resume_aid=None;probe.resume_attempt_path.write_text('');probe.phase='archive-only'
            resume_events=events(probe)[resume_start:]
            assert not [event for event in resume_events if event['kind']=='source-open'
                or (event['kind'] in {'content-processing','child-start','network-call'} and not event['allowed'])],resume_events
            probe.save('native-resume-observations-'+receipt['attempt_id'],{'events':resume_events,'fixture_denials':[]})
            resume_mode = 'pending_same_attempt'
            if finished['latest_attempt']['status'] == 'failed':
                assert finished['retry_target']['capture_id'] == receipt['capture_id']
                failed_attempt = finished['latest_attempt']['attempt_id']
                finished = retry(probe, 'hub', finished)
                assert finished['latest_attempt']['attempt_id'] != failed_attempt
                resume_mode = 'explicit_saved_capture_retry'
            assert finished['latest_attempt']['status'] == 'ready'
            assert finished['latest_attempt']['capture_id'] == receipt['capture_id']
            if resume_mode == 'pending_same_attempt':
                assert finished['latest_attempt']['attempt_id'] == receipt['attempt_id']
            snapshot(probe, item)
            probe.items.append(item)
        elif action == 'remove':
            assert item['id'] not in rows(probe, 'hub')
        else:
            finished = library_entry(probe, 'hub', item['id'])
            assert finished['latest_attempt']['status'] == 'ready'
            assert finished['latest_attempt']['capture_id'] != receipt['capture_id']
            snapshot(probe, item)
            probe.items.append(item)
        assert matching_process(engine['stamp']) is None
        unchanged_publication(snapshot(probe, other, reference=saved['reference']), saved)
        probe.register_source_paths()
        records.append({'action': action, 'original_attempt': original_attempt, 'actual_ocr': engine,
            'actual_service_stop_start': True, 'old_ocr_gone': True,
            'actual_native_stop_dispatch': dispatch, 'offline_before_restart': offline.get(item['id']),
            'resume_mode': resume_mode if action == 'retain' else 'old_candidate_not_revived',
            'final_attempt': None if action == 'remove' else finished['latest_attempt'],
            'source_copy_removed': True, 'other_publication_unchanged': True})
    probe.save('native-actual-ocr-interruptions', records)
