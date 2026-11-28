"""Read-only native-stop observation of already enrolled process identities."""
import threading
import time
import traceback


def sample(stamp):
    import psutil
    value = {'identity': stamp, 'started': time.monotonic(), 'waiting': True}
    def recorded(**fields):
        return {**value, **fields, 'finished': time.monotonic()}
    try:
        process = psutil.Process(stamp['pid'])
        created = process.create_time()
    except psutil.ZombieProcess:
        return recorded(state='creation-unconfirmed-zombie')
    except psutil.NoSuchProcess:
        return recorded(state='gone',waiting=False)
    except psutil.AccessDenied:
        return recorded(state='creation-access-denied')
    assert created == stamp['created'], ('owned process identity changed', stamp, created)
    try:
        status = process.status()
        waiting = process.is_running() and status != psutil.STATUS_ZOMBIE
        return recorded(actual_created=created,state=status,waiting=waiting)
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return recorded(actual_created=created,state='exited',waiting=False)
    except psutil.AccessDenied:
        return recorded(actual_created=created,state='status-access-denied')


def watch_stop(members, controller, stop, save, *, timeout=60, join_timeout=60, own_thread=None):
    """Sample during native stop, separating its duration from child cleanup.

    A PID which still exists may be an exited zombie. Unknown identities and
    denied status never prove exit. The five-second child-cleanup bound starts
    conservatively at the last confirmed live controller observation, once its
    exit is confirmed; it is not a bound on launchctl/systemctl runtime.
    """
    assert members and controller in members
    assert len(members) == len({v['pid'] for v in members})
    assert all(set(v) == {'pid', 'created', 'argv', 'exe'} for v in members)
    began = time.monotonic()
    history = []
    errors = []
    last_live = began
    exited = None
    cleaned_at = None
    result = None
    confirmed_exits = {}

    def observations():
        rows = []
        for identity in members:
            key = (identity['pid'], identity['created'])
            if key in confirmed_exits:
                rows.append({**confirmed_exits[key], 'retained_exit_proof': True})
                continue
            row = sample(identity)
            if not row['waiting']:
                # A confirmed exact identity cannot become live again. Never
                # poll or signal an unrelated process which later reuses its PID.
                confirmed_exits[key] = row
            rows.append(row)
        return rows

    def invoke():
        try:
            stop()
        except BaseException:
            errors.append(traceback.format_exc())

    worker = threading.Thread(target=invoke)
    if own_thread is not None:own_thread(worker)
    try:
        initial = observations()
        own = next(v for v in initial if v['identity'] == controller)
        assert own['waiting'] and own['state'] not in {
            'creation-unconfirmed-zombie', 'creation-access-denied', 'status-access-denied'}
        last_live = own['started']
        history.append(initial)
        worker.start()
        while True:
            current = observations()
            history.append(current)
            own = next(v for v in current if v['identity'] == controller)
            if not own['waiting'] and exited is None:
                exited = {'last_confirmed_live': last_live, 'first_confirmed_exit': own['finished']}
            elif own['waiting'] and own['state'] not in {
                    'creation-unconfirmed-zombie', 'creation-access-denied', 'status-access-denied'}:
                assert exited is None, 'an exited owned identity became live again'
                last_live = own['started']
            assert not errors, errors
            waiting = [v for v in current if v['waiting']]
            if not waiting and cleaned_at is None:
                cleaned_at = max(v['finished'] for v in current)
            if exited is not None and waiting:
                assert time.monotonic() - exited['last_confirmed_live'] <= 5, ('owned children survived controller exit', waiting)
            if not waiting and not worker.is_alive():
                worker.join()
                assert not errors,errors
                bound = cleaned_at - exited['last_confirmed_live']
                assert bound <= 5, ('could not prove cleanup within five seconds', bound)
                result = {'status': 'verified', 'controller_exit': exited,
                          'cleanup_upper_bound_seconds': bound, 'stop_seconds': time.monotonic() - began}
                return result
            assert time.monotonic() - began < timeout, 'native stop observation deadline'
            time.sleep(.01)
    finally:
        if worker.ident is not None:
            worker.join(timeout=join_timeout)
        save({'result': result, 'samples': history, 'stop_errors': errors,
              'stop_call_returned': not worker.is_alive(), 'began': began})


def wait_stop_calls(probe, *, timeout=150):
    """Retain both ownership layers; an outer stop can register its child late."""
    for field in ('pending_native_stop', 'pending_native_command_stop'):
        pending = getattr(probe, field, None)
        if pending is not None and pending.is_alive():
            pending.join(timeout=timeout)
            if pending.is_alive():
                probe.save('native-service-cleanup', {'errors': [{'step': 'wait-' + field,
                    'error': 'native stop still running; no concurrent cleanup was issued'}]})
                raise RuntimeError('Owned native stop did not finish; cleanup deferred without a second disable')
