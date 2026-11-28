"""Actual SCM/LocalService Word worker component, separate standard HTTP actor.

This small capability check precedes complete H1-H5. It deliberately uses the
stock service startup and worker command, without parser/path/observer shims.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(Path(__file__).resolve().parent), str(ROOT / 'tests')]
import hub_documents_scm_platform as scm
from document_formats_installed_protocols import FormatProbe
from document_formats_upload_transport import upload
from document_formats_fixtures import docx_fixture
from hub_documents_platform import now


class WordAdministrator(scm.Administrator):
    def run(self, label, argv, **kwargs):
        if label == 'openssl':
            # Only the controller test CA generation is shared. The service's
            # interpreter, site setup, environment and module launch stay stock.
            return FormatProbe.run(self, label, argv, **kwargs)
        return super().run(label, argv, **kwargs)


class WordClient(scm.OrdinaryScmClient):
    actor = staticmethod(FormatProbe.actor)
    path = FormatProbe.path
    body = FormatProbe.body
    keep = FormatProbe.keep

    def run(self, label, argv, **kwargs):
        if label == 'openssl':
            return FormatProbe.run(self, label, argv, **kwargs)
        return super().run(label, argv, **kwargs)


def ordinary(config, output):
    probe = WordClient(config, output)
    result = None
    try:
        assert probe.actor()['sid'] == config['expected_actor_sid']
        probe.start('hub')
        info = probe.request('hub', '/v1/info')
        probe.hub_context = {key: info[key] for key in ('hub_id', 'document_epoch')}
        project = probe.cli('hub', 'project', 'create', '008 SCM Word component')
        raw, truth = docx_fixture('SCMWORDWORKER')
        probe.keep('inputs/SCMWORDWORKER.docx', raw)
        frozen_truth = {**truth, 'parts': sorted(truth['parts'])}
        probe.keep('truth/SCMWORDWORKER.json', json.dumps(frozen_truth, ensure_ascii=False).encode())
        item = {'role': 'hub', 'project': project, 'label': 'SCMWORDWORKER', 'format': 'docx'}
        entry = upload(probe, item, raw)
        probe.save('actual-word-terminal-state', entry)
        assert entry['latest_attempt']['status'] == 'ready', entry['latest_attempt']
        found = probe.request('hub', '/v1/documents/search', probe.body('hub',
            query='SCMWORDWORKER', scope='project', project_id=project['id'], limit=50))['results']
        assert len(found) == 1 and found[0]['origin']['document_id'] == entry['id']
        value = probe.request('hub', '/v1/documents/read', probe.body('hub',
            reference=found[0]['reference'], start=0, end=found[0]['text_length']))
        assert all(word in value['text'] for word in truth['words'])
        result = {'status': 'passed', 'scope': 'actual SCM Word worker capability component only',
            'actor': probe.actor(), 'finished_at': now(), 'not_covered': ['OCR', 'browser', 'complete H1-H5', 'E', 'X']}
    except BaseException:
        probe.save('failure', {'traceback': traceback.format_exc(), 'at': now()})
        raise
    finally:
        probe.cleanup()
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
        scm.administrator(config, args.output.resolve(), manager_factory=WordAdministrator,
            runner=Path(__file__).resolve(),
            wrapper=Path(__file__).with_name('document_formats_installed_standard_user.ps1'))
