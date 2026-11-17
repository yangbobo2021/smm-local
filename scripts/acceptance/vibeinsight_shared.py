# SPDX-License-Identifier: Apache-2.0
"""Additional controlled SQL boundaries on an already configured real Hub service."""
import json
from pathlib import Path
import sqlite3

from vibeinsight_fixture import Fixture, literal
from vibeinsight_platform import eventually


def shared(run):
    run.start()
    run.expected_hub_id=run.api("info")["hub_id"]
    original=run.session('turns')[0]
    old=run.read(original)
    assert [(m["role"],m["text"]) for m in old["messages"]]==[("user" if n%2==0 else "assistant",f"platform evidence C turns {n}") for n in range(10)]
    run.save("G5-independent-before",old)
    run.stop()
    # Two projects have different valid committed batch positions after partial work.
    source=run.fixture
    source.rows(200,202,session='base-A',repo='late-A',created_start='2026-09-20T12:00:00')
    source.rows(300,302,session='base-B',repo='late-B',created_start='2026-09-21T12:00:00')
    run.start()
    eventually(lambda:len(run.session('base-A'))==len(run.session('base-B'))==1)
    run.stop()
    with sqlite3.connect(run.state/'smm-hub.sqlite3') as con:
        for key,timestamp,event in [('git.example:0/team/late-A','2026-09-20T12:00:01','E000201'),
                                    ('git.example:0/team/late-B','2026-09-21T12:00:01','E000301')]:
            source_id=json.dumps([run.cfg['host'],run.cfg['port'],run.cfg['database']])
            changed=con.execute('UPDATE hub_vibeinsight_cursors SET timestamp=?,event_id=? WHERE source_id=? AND project=?',
                        (timestamp,event,source_id,key))
            assert changed.rowcount==1
            actual=con.execute('SELECT timestamp,event_id FROM hub_vibeinsight_cursors WHERE source_id=? AND project=?',(source_id,key)).fetchone()
            assert tuple(actual)==(timestamp,event)
    run.save('G3-starting-positions',run.checkpoints())
    rows=[]
    for n,session,repo,created in [
        (400,'boundary-A','late-A','2026-09-19T12:00:01'),
        (402,'inside-A','late-A','2026-09-19T12:00:02'),
        (404,'outside-A','late-A','2026-09-19T12:00:00'),
        (410,'boundary-B','late-B','2026-09-20T12:00:01'),
        (412,'inside-B','late-B','2026-09-20T12:00:02'),
        (414,'outside-B','late-B','2026-09-20T12:00:00'),
        (500,'during-downtime','late-A','2026-09-22T12:00:00'),
        (502,'after-days','late-A','2026-09-25T12:00:00'),
        (600,'new-project-older','gamma','2026-08-01T00:00:00')]:
        rows += source.rows(n,n+1,session=session,repo=repo,created_start=created)
    source.sql("ALTER POLICY visibility ON fact_events USING (repo_path NOT IN ('team/hidden','team/never'))")
    rows += source.rows(700,701,session='later-visible',repo='hidden',created_start='2026-08-01T00:00:00')
    rows += source.rows(702,703,session='never-visible',repo='never',created_start='2026-08-01T00:00:00')
    run.save('G3-independent-source-rows',rows)
    run.start()
    required={'boundary-A','inside-A','boundary-B','inside-B','during-downtime','after-days','new-project-older'}
    eventually(lambda:required <= {h['source_session_id'] for h in run.hits()['results']})
    for name in required:
        hit,=run.session(name)
        record=next(r for r in rows if r['session']==name)
        read=run.read(hit)
        assert [(m['role'],m['text']) for m in read['messages']]==[(record['role'],record['text'])]
        run.save('G3-read-'+name,read)
    assert not run.session('later-visible') and not run.session('never-visible')
    source.sql("ALTER POLICY visibility ON fact_events USING (repo_path <> 'team/never')")
    eventually(lambda:len(run.session('later-visible'))==1)
    assert not run.session('never-visible')
    later=run.read(run.session('later-visible')[0])
    assert [(m['role'],m['text']) for m in later['messages']]==[('user','platform evidence hidden later-visible 700')]
    run.save('G1-later-visible-original',later)
    run.snapshot('G3-after')
    # A body edit without a new event is outside the supported increment type.
    run.stop()
    source.sql("UPDATE fact_events SET message='in place edit without a new event' WHERE id='E000000'")
    appended=source.rows(10,12,session='turns',repo='C',created_start='2026-09-26T12:00:00')
    run.start()
    eventually(lambda:len(run.read(original)['messages'])==12)
    read=run.read(original)
    assert [(m['role'],m['text']) for m in read['messages'][:10]]==[('user' if n%2==0 else 'assistant',f'platform evidence C turns {n}') for n in range(10)]
    assert [m['text'] for m in read['messages'][10:]]==[r['text'] for r in appended]
    run.save('G5-original-edit-boundary',read)
    # Identical created_at values exercise the production COPY ordering.
    run.stop()
    same=source.rows(800,804,session='same-time',repo='C',created_start='2026-09-27T12:00:00')
    source.sql("UPDATE fact_events SET created_at='2026-09-27T12:00:00' WHERE id IN ('E000800','E000801','E000802','E000803')")
    run.start()
    eventually(lambda:len(run.session('same-time'))==1)
    same_hit=run.session('same-time')[0]
    assert [m['text'] for m in run.read(same_hit)['messages']]==[r['text'] for r in same]
    success=run.admin('vibeinsight','status')['last_success']
    eventually(lambda:run.admin('vibeinsight','status')['last_success']!=success)
    assert len(run.read(same_hit)['messages'])==4
    run.save('G2-same-time-and-repeat',run.read(same_hit))
    # Verify actual link CLI, reverse scopes and unlink without loss of old references.
    projects=run.admin('project','list')
    a=next(p for p in projects if p['id']==run.target['device_projects']['mac'])
    b=next(p for p in projects if p['id']==run.target['device_projects']['linux'])
    c=next(p for p in projects if p['source']=='vibeinsight' and p['source_key']=='git.example:0/team/C')
    d=next(p for p in projects if p['source']=='vibeinsight' and p['source_key']=='git.example:0/team/D')
    for one,two in [(a,b),(a,c),(b,d)]:run.admin('project','link',str(one['id']),str(two['id']))
    links=run.admin('project','links')
    run.admin('project','link',str(a['id']),str(b['id']))
    assert run.admin('project','links')==links
    pairs=[tuple(sorted((link['a'],link['b']))) for link in links]
    assert len(pairs)==len(set(pairs))
    assert {tuple(sorted(pair)) for pair in [(a['id'],b['id']),(a['id'],c['id']),(b['id'],d['id'])]} <= set(pairs)
    run.save('G6-links',links)
    def scoped(project):
        return run.api('search',{'query':'platform','limit':50,'device_id':project['owner'],'project_id':project['source_key']})
    for project,ids in [(a,{a['id'],b['id'],c['id']}),(b,{b['id'],a['id'],d['id']})]:
        data=scoped(project)
        assert {p['id'] for p in data['effective_projects']}==ids
        assert {p['id'] for h in data['results'] for p in h['projects']}==ids
        required={(a['id'],'device-mac'),(b['id'],'device-linux'),((c if project['id']==a['id'] else d)['id'],'turns' if project['id']==a['id'] else 'other')}
        for project_id,session in required:
            assert any(h['source_session_id']==session and any(p['id']==project_id for p in h['projects']) for h in data['results'])
        run.save('G6-scope-'+project['device_name'],data)
    run.admin('project','unlink',str(a['id']),str(c['id']))
    unlinked=scoped(a)
    assert {p['id'] for p in unlinked['effective_projects']}=={a['id'],b['id']}
    assert {p['id'] for h in unlinked['results'] for p in h['projects']}=={a['id'],b['id']}
    assert {h['source_session_id'] for h in unlinked['results']}=={'device-mac','device-linux'}
    global_after=run.hits()
    assert any(h['source_session_id']=='turns' and any(p['id']==c['id'] for p in h['projects']) for h in global_after['results'])
    run.save('G6-unlinked-search',unlinked);run.save('G6-unlinked-global',global_after)
    assert run.read(original)['messages']==read['messages']
    run.save('G6-unlinked-old-reference',run.read(original))
    run.admin('project','link',str(a['id']),str(c['id']))
    run.stop()
    newer=source.rows(900,902,session='repository-new',repo='new-C',created_start='2026-09-28T12:00:00')
    run.start()
    eventually(lambda:len(run.session('repository-new'))==1)
    new=next(p for p in run.admin('project','list') if p['source_key']=='git.example:0/team/new-C')
    assert new['id']!=c['id']
    assert all(h['source_session_id']!='repository-new' for h in scoped(a)['results'])
    run.admin('project','link',str(a['id']),str(new['id']))
    assert any(h['source_session_id']=='repository-new' for h in scoped(a)['results'])
    run.save('G7-repository-relink',scoped(a))
    run.admin('project','unlink',str(a['id']),str(new['id']))
    # A genuinely different connection target must not reuse the old target's late cursor.
    run.stop()
    database='smm_other_'+run.cfg['instance'][:8]
    source.sql('CREATE DATABASE '+database)
    other=object.__new__(Fixture);other.config={**source.config,'database':database};other.psql=source.psql
    other.sql("CREATE TABLE smm_fixture_instance(marker text); INSERT INTO smm_fixture_instance VALUES ("+literal(run.cfg['instance'])+"); "
              "CREATE TABLE fact_events (id varchar(26) PRIMARY KEY,user_id varchar(26),platform_code text,session_id text,"
              "trace_id text,event_type text,message text,repo_hostname text,repo_port integer,repo_path text,"
              "event_timestamp timestamp,created_at timestamp); GRANT SELECT ON fact_events TO source_reader,replacement_reader;")
    other.rows(0,2,session='other-target',repo='C',created_start='2026-07-01T00:00:00')
    old_cursors=run.checkpoints()
    run.configure(database=database,interval=1)
    run.start()
    eventually(lambda:len(run.session('other-target'))==1)
    assert run.read(original)['messages']==read['messages']
    cursors=run.checkpoints()
    assert all(row in cursors for row in old_cursors)
    assert {r['source_id'] for r in cursors}=={r['source_id'] for r in old_cursors}|{json.dumps([run.cfg['host'],run.cfg['port'],database])}
    run.save('G4-new-target-original',run.read(run.session('other-target')[0]));run.snapshot('G4-new-target-cursors')
    run.configure(interval=1,user='replacement_reader',password=run.cfg['replacement_password'])
