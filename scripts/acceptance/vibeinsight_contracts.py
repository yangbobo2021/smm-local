# SPDX-License-Identifier: Apache-2.0
"""Full P/G contracts layered on the reusable installed-package platform actors."""
import argparse
import json
from pathlib import Path

from vibeinsight_fixture import Fixture
from vibeinsight_platform import Run,eventually
from vibeinsight_shared import shared


def old_references(run,records,label):
    observed=[]
    for record in records:
        for message in record['messages']:
            result=run.api('read',{'hub_id':run.expected_hub_id,'conversation_id':record['id'],
                                   'message_id':message['hub_message_id']})
            assert result['messages']==[message]
            observed.append(result)
    run.save(label,observed)


def standalone(run):
    run.setup()
    before_append=run.committed()
    run.lifecycle()
    old_references(run,before_append,'P-pre-append-references-retained')
    expected=run.fixture.rows(140,142,session='p-credential-continuation')
    eventually(lambda:len(run.session('p-credential-continuation'))==1)
    new=run.read(run.session('p-credential-continuation')[0])
    assert [(m['role'],m['text']) for m in new['messages']]==[(r['role'],r['text']) for r in expected]
    run.save('P-persisted-credential-new-original',new)
    before_legacy=run.committed()
    run.standalone_compatibility()
    run.assert_committed(before_legacy)
    old_references(run,before_append,'P-initial-references-after-legacy')
    run.save('P-full-originals-after-legacy',run.committed())


def shared_contract(run):
    shared(run)
    database='smm_other_'+run.cfg['instance'][:8]
    manifest=run.root/('fixture-'+database+'.json')
    manifest.write_text(json.dumps({**run.cfg,'database':database}),encoding='utf-8');manifest.chmod(0o600)
    try:
        other=Fixture(manifest,run.target['psql'])
        run.configure(database=database,interval=1)
        run.start()
        run.expected_hub_id=run.api('info')['hub_id']
        hit,=run.session('other-target')
        original=run.read(hit)
        assert [(m['role'],m['text']) for m in original['messages']]==[
            ('user','platform evidence C other-target 0'),('assistant','platform evidence C other-target 1')]
        run.save('G4-independent-early-target-original',original)
        progress=run.checkpoints();retained=run.committed()
        success=run.admin('vibeinsight','status')['last_success']
        run.configure(database=database,interval=1,user='replacement_reader',password=run.cfg['replacement_password'])
        assert run.checkpoints()==progress
        run.stop();run.start()
        eventually(lambda:run.admin('vibeinsight','status')['last_success']!=success and not run.admin('vibeinsight','status')['last_error'])
        assert run.checkpoints()==progress
        run.assert_committed(retained)
        expected=other.rows(2,4,session='other-target-continuation',created_start='2026-07-01T00:00:02')
        run.save('G4-independent-continuation-input',expected)
        eventually(lambda:len(run.session('other-target-continuation'))==1)
        result=run.read(run.session('other-target-continuation')[0])
        assert [(m['role'],m['text']) for m in result['messages']]==[(r['role'],r['text']) for r in expected]
        assert run.read(hit)['messages']==original['messages']
        source_id=json.dumps([run.cfg['host'],run.cfg['port'],database])
        assert all(row in run.checkpoints() for row in progress if row['source_id']!=source_id)
        run.save('G4-replaced-credential-continuation',result);run.snapshot('G4-replaced-credential-progress')
    finally:
        manifest.unlink(missing_ok=True)
        run.configure(interval=1,user='replacement_reader',password=run.cfg['replacement_password'])


def reference_evidence(directory):
    def read(name):return json.loads((directory/name).read_text(encoding='utf-8'))
    original=read('H1-original.json');appended=read('H6-after-original.json')
    assert original['id']==appended['id']
    assert appended['messages'][:len(original['messages'])]==original['messages']
    anchors={}
    for name in ['H6-after-original.json','H1-other-project-original.json','H2-scheduled-original.json','H6-new.json']:
        record=read(name)
        for message in record['messages']:anchors[(record['id'],message['hub_message_id'])]=message
    assert len(anchors)==16
    checked=[]
    for path in sorted(directory.glob('retained-originals-*.json')):
        if int(path.stem.rsplit('-',1)[1])<7:continue
        exact={}
        for item in read(path.name):
            for result in item['exact_reads']:
                assert len(result['messages'])==1
                message=result['messages'][0];exact[(result['id'],message['hub_message_id'])]=message
        for key,value in anchors.items():assert exact[key]==value
        checked.append(path.name)
    assert len(checked)>=6
    return {'status':'passed','old_before_append':len(original['messages']),'post_append_anchors':len(anchors),
            'phases':checked,'note':'Compared the original message IDs and full objects with actual single-message HTTP reads after restart, credential replacement and faults; not merely body equality.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('contract',choices=['standalone','shared','references']);p.add_argument('--target-config',type=Path)
    p.add_argument('--fixture-manifest',type=Path);p.add_argument('--evidence-dir',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.contract=='references':
        if a.evidence_dir is None:p.error('references requires --evidence-dir')
        if a.output.exists():p.error('output must be new')
        a.output.write_text(json.dumps(reference_evidence(a.evidence_dir),indent=2)+'\n',encoding='utf-8');return
    if a.target_config is None or a.fixture_manifest is None:p.error('target config and fixture manifest are required')
    a.mode='self-managed' if a.contract=='standalone' else 'shared'
    run=Run(a)
    try:
        run.installed_identity()
        (standalone if a.contract=='standalone' else shared_contract)(run)
        run.save('final-service',run.service_identity());run.finish('passed')
    except BaseException as error:
        run.finish('failed',type(error).__name__+': '+str(error));raise
    finally:run.stop()


if __name__=='__main__':main()
