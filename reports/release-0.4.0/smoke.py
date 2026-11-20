import argparse,asyncio,hashlib,importlib.util,importlib.metadata as meta,json,os,subprocess,sys,tempfile,zipfile,tomllib
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
parser=argparse.ArgumentParser(description="Check the independently installed SMM 0.4.0 wheels and release Skill ZIPs using synthetic data only.")
parser.add_argument('--checkout',type=Path,required=True)
parser.add_argument('--hub-python',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
ROOT=args.checkout.resolve()
LOCAL=Path(sys.executable);HUB=Path(os.path.abspath(args.hub_python))
report={'version':'0.4.0','python':sys.version,'checks':{},'commands':[]}
def call(args,env=None):
 p=subprocess.run(list(map(str,args)),env=env,text=True,capture_output=True,timeout=60,cwd=tempfile.gettempdir())
 report['commands'].append({'argv':list(map(str,args)),'exit_code':p.returncode})
 assert p.returncode==0,p.stderr
 return p.stdout
for name,py,missing in [('smm-local',LOCAL,'smm_hub'),('smm-hub',HUB,'smm_local')]:
 data=json.loads(call([py,'-I','-c',f'import importlib.metadata as m,importlib.util as u,json;print(json.dumps({{"version":m.version("{name}"),"other_absent":u.find_spec("{missing}") is None}}))']))
 assert data=={'version':'0.4.0','other_absent':True};report['checks'][name]=data
assert '--state-dir' in call([HUB,'-I','-m','smm_hub.cli','serve-hub','--help'])
call([HUB,'-I','-m','smm_hub.cli','hub','vibeinsight','configure','--help'])
assert '--before' in call([LOCAL,'-I','-m','smm_local.cli','source','batches','--help'])
call([LOCAL,'-I','-m','smm_local.mcp_server','--help'])
report['checks']['public_help']=True
for name in ['smm-search','smm-source-adapter']:
 with zipfile.ZipFile(ROOT/'dist'/f'{name}-0.4.0.zip') as z:
  assert all(p.startswith(name+'/') and '..' not in Path(p).parts for p in z.namelist())
  assert name+'/SKILL.md' in z.namelist()
  if name=='smm-search':assert 'PACKAGE = "smm-local==0.4.0"' in z.read(name+'/scripts/first_use.py').decode()
 report['checks'][name+'-zip']=True
with tempfile.TemporaryDirectory(prefix='smm040-smoke-') as d:
 home=Path(d);src=home/'source';src.mkdir();db=home/'archive.sqlite3'
 env={**os.environ,'HOME':str(home),'USERPROFILE':str(home),'CLAUDE_CONFIG_DIR':str(home/'.claude'),'CODEX_HOME':str(home/'.codex')}
 expected='releaseproof040 '+('长对话原文检查。'*120)+' preserve exact original'
 records=[{'type':'session_meta','payload':{'id':'release-smoke-040','cwd':str(home/'project')}},
 {'type':'response_item','ordinal':2,'payload':{'type':'message','role':'user','content':[{'type':'input_text','text':'releaseproof040 question'}]}},
 {'type':'response_item','ordinal':3,'payload':{'type':'message','role':'assistant','content':[{'type':'output_text','text':expected}]}}]
 (src/'sample.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in records))
 got=json.loads(call([LOCAL,'-I','-m','smm_local.cli','--db',db,'sync','--source','codex','--root',src],env));assert got['messages_new']==2,got
 hit=json.loads(call([LOCAL,'-I','-m','smm_local.cli','--db',db,'search','releaseproof040','--local'],env))['results'][0]
 read=json.loads(call([LOCAL,'-I','-m','smm_local.cli','--db',db,'read',hit['id']],env))
 assert [m['text'] for m in read['messages']]==['releaseproof040 question',expected]
 async def check():
  params=StdioServerParameters(command=str(LOCAL),args=['-I','-m','smm_local.mcp_server','--db',str(db)],env=env)
  async with stdio_client(params) as (r,w):
   async with ClientSession(r,w) as client:
    await client.initialize();tools=await client.list_tools();schemas={x.name:x.inputSchema for x in tools.tools}
    assert 'local' in schemas['search_conversations']['properties'] and 'hub_message_id' in schemas['read_conversation']['properties']
    result=await client.call_tool('search_conversations',{'query':'releaseproof040','local':True});assert not result.isError
    data=json.loads(result.content[0].text);h=next(x for x in data['results'] if x['source_session_id']=='release-smoke-040')
    msg=next(x for x in h['matched_messages'] if x['position']==3);assert msg['preview_truncated'] and len(msg['preview'])<=600
    full=await client.call_tool('read_conversation',{'conversation_id':h['id'],'start':3,'end':3});assert not full.isError
    assert json.loads(full.content[0].text)['messages'][0]['text']==expected
 asyncio.run(check())
 report['checks']['cli_import_search_original']=True;report['checks']['stdio_mcp_search_original_schema']=True
 report['checks']['original_sha256']=hashlib.sha256(expected.encode()).hexdigest()
report['status']='passed'
args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
