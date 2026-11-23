"""Report hosted-runner capabilities. This is NOT 007 product acceptance."""
import argparse,json,os,platform,subprocess,sys,time,uuid
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    report={'purpose':'environment capability only; no product acceptance','platform':platform.platform(),'python':sys.executable,'commands':[]}
    def run(argv,**kw):
        r=subprocess.run(argv,capture_output=True,text=True,timeout=60,**kw);report['commands'].append({'argv':argv,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr});return r
    if sys.platform=='linux':
        uid=os.getuid();report['uid']=uid;report['ordinary_user']=uid!=0;unit='smm-007-preflight-'+uuid.uuid4().hex+'.service'
        initial=run(['loginctl','show-user',str(uid),'-p','Linger','--value']).stdout.strip();env={**os.environ,'XDG_RUNTIME_DIR':'/run/user/'+str(uid),'DBUS_SESSION_BUS_ADDRESS':'unix:path=/run/user/'+str(uid)+'/bus'}
        try:
            run(['sudo','-n','loginctl','enable-linger',str(uid)]);run(['sudo','-n','systemctl','start','user@'+str(uid)+'.service'])
            result=run(['systemd-run','--user','--unit',unit,'/bin/sleep','60'],env=env)
            status=run(['systemctl','--user','show',unit,'-p','MainPID','-p','ActiveState'],env=env);report['user_systemd']=result.returncode==0 and 'ActiveState=active' in status.stdout
        finally:
            run(['systemctl','--user','stop',unit],env=env);run(['systemctl','--user','reset-failed',unit],env=env)
            if initial!='yes':run(['sudo','-n','loginctl','disable-linger',str(uid)])
    elif sys.platform=='win32':
        script=Path(__file__).with_suffix('.ps1').resolve();result=run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script),'-OutputDirectory',str(a.output.resolve())]);report['powershell_exit']=result.returncode
    else:report['notice']='Local macOS execution is separate from this CI preflight'
    (a.output/'capabilities.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='commands'},ensure_ascii=False))


if __name__=='__main__':main()
