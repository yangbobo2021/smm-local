"""Task-specific query-only service guard, separate from shared restart audit."""
import json
import os
from pathlib import Path
import socket
import sys
from contextlib import contextmanager
import subprocess
from uuid import uuid4
from urllib.parse import urlsplit
from document_formats_platform import internal_socketpair


def install():
    if not os.environ.get('SMM_008_REMOTE_QUERY'):
        return
    from smm_local.core import Archive
    from smm_local import federation
    db = Archive(os.environ['SMM_008_TEST_DB'])
    owner = os.environ['SMM_008_TEST_OWNER']
    log = Path(os.environ['SMM_008_REMOTE_QUERY_LOG'])

    def allowed(host, port):
        if owner != 'local':
            return False
        config = federation.hub_config(db)
        if not config:
            return False
        target = urlsplit(config['address'])
        return host == target.hostname == '127.0.0.1' and str(port) == str(target.port)

    def audit(event, args):
        denied = False
        if event == 'socket.getaddrinfo':
            denied = not allowed(args[0], args[1])
        elif event == 'socket.connect':
            address = args[1]
            denied = not internal_socketpair(sys._getframe(1), args[0], address) and not (isinstance(address, tuple) and allowed(*address[:2]))
        if denied:
            with log.open('a', encoding='utf-8') as out:
                out.write(json.dumps({'event': event, 'pid': os.getpid(), 'owner': owner}) + '\n')
            raise AssertionError('remote query service forbidden network')
    sys.addaudithook(audit)

    def instrument(factory):
        def create(*args, **kwargs):
            app = factory(*args, **kwargs)
            @app.post('/__test_remote_query_probe')
            def probe():
                blocked = []
                protected = json.loads(os.environ['SMM_008_RESTART_DENY'])
                try:
                    Path(protected[0]).read_bytes()
                except RuntimeError as exc:
                    assert 'restart source read denied' in str(exc)
                    blocked.append('source')
                for label, action in (
                    ('resolve', lambda: socket.getaddrinfo('192.0.2.1', 9)),
                    ('connect', lambda: socket.socket().connect(('192.0.2.1', 9))),
                ):
                    try:action()
                    except AssertionError as exc:
                        assert 'remote query service forbidden network' in str(exc)
                        blocked.append(label)
                # Real standard-library internal socketpair is allowed.
                a, b = socket.socketpair()
                try:
                    a.sendall(b'query-control');assert b.recv(13) == b'query-control'
                finally:a.close();b.close()
                if owner == 'local':
                    target = urlsplit(federation.hub_config(db)['address'])
                    with socket.create_connection((target.hostname, target.port), timeout=2):pass
                allowed_path = Path(os.environ['SMM_008_TEST_DB']).parent / 'query-allowed'
                assert allowed_path.read_bytes() == b'allowed query control'
                return {'blocked': blocked, 'positive': ['internal_socketpair', 'allowed_file'] + (['configured_hub'] if owner == 'local' else []), 'pid': os.getpid()}
            return app
        return create
    from smm_local import api
    from smm_hub import hub
    api.create_app = instrument(api.create_app)
    hub.create_hub = instrument(hub.create_hub)


@contextmanager
def controller_queries(world):
    """Guard only direct product calls, not the test's CLI/server launchers."""
    from smm_local import federation, document_processing
    from smm_local.document_snapshots import Snapshots
    events=[];active=True;baseline=None
    protected={os.path.normcase(os.path.abspath(p)) for p in world.protected}
    def deny(event):
        events.append(event)
        raise AssertionError('controller query forbidden: '+event)
    def allowed(address):
        target=urlsplit(federation.hub_config(world.sender_db)['address'])
        return isinstance(address,tuple) and address[:2]==(target.hostname,target.port)
    def audit(event,args):
        if not active:return
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)) and os.path.normcase(os.path.abspath(os.fsdecode(args[0]))) in protected:deny('source-open')
        if event=='subprocess.Popen':deny('spawn')
        if event=='socket.getaddrinfo' and not allowed(args[:2]):deny('network-resolve')
        if event=='socket.connect' and not internal_socketpair(sys._getframe(1),args[0],args[1]) and not allowed(args[1]):deny('network-connect')
    sys.addaudithook(audit)
    def processing(*args,**kwargs):deny('processing')
    try:
        with world.monkeypatch.context() as m:
            m.setattr(Snapshots,'process',processing);m.setattr(document_processing,'process',processing)
            actions=[lambda:world.protected[0].read_bytes(),lambda:subprocess.Popen([sys.executable,'-c','raise SystemExit(0)']),lambda:socket.getaddrinfo('192.0.2.1',9),lambda:socket.socket().connect(('192.0.2.1',9)),lambda:Snapshots.process(None,None,'docx')]
            for action in actions:
                try:action()
                except AssertionError as exc:assert 'controller query forbidden' in str(exc)
                else:raise AssertionError('negative control was not blocked')
            assert events==['source-open','spawn','network-resolve','network-connect','processing']
            target=urlsplit(federation.hub_config(world.sender_db)['address'])
            with socket.create_connection((target.hostname,target.port),timeout=2):pass
            baseline=list(events)
            yield
    finally:
        active=False
        world.save('controller-controls/'+uuid4().hex+'.json',events)
        if baseline is not None:assert events==baseline,'direct product query attempted forbidden work'
