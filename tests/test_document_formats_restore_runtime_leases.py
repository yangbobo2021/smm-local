"""Restore data excludes the live Hub processor registration/lease."""
import json
import shutil
from pathlib import Path

from document_helpers import observe
from test_document_formats_restore_set import covered, invoke
from test_document_formats_upload_restart import Server


def test_restore_manifest_excludes_live_processing_service_lease(tmp_path):
    # TC-008-snapshot-restore-set: service lifetime is not durable archive data.
    server = Server(tmp_path / 'hub', 'hub')
    server.db = server.root / 'smm-hub.sqlite3'
    try:
        server.start()
        services = server.root / '.document-snapshots' / 'services'
        leases = list(services.glob('hub-processing-*.lock'))
        statuses = list(services.glob('hub-processing-*.json'))
        assert len(leases) == len(statuses) == 1
        live = json.loads(statuses[0].read_bytes())
        assert live['status'] == 'running'
        result = invoke(server.root, server.db, 'hub', 'prepare-restore')
        excluded = [Path(p).resolve() for p in result['do_not_restore']]
        included = [Path(p).resolve() for p in result['restore_files']]
        observe('restore-live-processing-lease', {'lease': str(leases[0]), 'status': live,
                'manifest': result, 'services_excluded': covered(services.resolve(), excluded)})
        assert covered(services.resolve(), included)
        destination = tmp_path / 'restored-runtime'
        destination.mkdir()
        copied = []
        for source in sorted(services.iterdir()):
            if not source.is_file() or covered(source.resolve(), excluded):
                continue
            try:
                shutil.copyfile(source, destination / source.name)
            except OSError as error:
                observe('restore-live-lease-copy-failure', {'path': str(source),
                        'error_type': type(error).__name__, 'errno': error.errno,
                        'winerror': getattr(error, 'winerror', None)})
                raise
            copied.append(source.name)
        assert copied == [], 'runtime registration/status must not enter restored data'
        assert covered(services.resolve(), excluded), 'live Hub processing leases must not be restored'
        assert all(covered(p.resolve(), excluded) for p in [*leases, *statuses])
    finally:
        server.stop()
