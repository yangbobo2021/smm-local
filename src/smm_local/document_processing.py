"""Explicit creator actions over saved bytes; queries never call this module."""
from __future__ import annotations
import json
from pathlib import Path
from .document_results import validate
from .core import utcnow


def process(snapshots,capture):
    with snapshots.pin([('raw',capture['raw_sha256'])]):
        return _process(snapshots,capture)


def _process(snapshots,capture):
    if capture['reused']:return snapshots.load_result(capture['result_sha256'])
    cid=capture['capture_id'];aid=capture['attempt_id']
    with snapshots.db.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        state=c.execute('SELECT * FROM document_snapshot_state WHERE document_pk=?',(capture['document_pk'],)).fetchone()
        if state is None or state['current_capture']!=cid or state['latest_attempt']!=aid or not snapshots.authorized(c,cid) or snapshots.retired('attempts',aid):raise ValueError('捕获或尝试已失效')
        c.execute("UPDATE document_processing_attempts SET state='processing' WHERE id=?",(aid,))
    directory=snapshots._directory('tasks')/aid;directory.mkdir(mode=0o700,exist_ok=True)
    output=directory/'result.json'
    config=dict(capture['config'])
    with snapshots.db.connect() as c:
        probe=c.execute('SELECT payload FROM document_processing_probe WHERE singleton=1 AND revision=?',(config['revision'],)).fetchone() if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='document_processing_probe'").fetchone() else None
        if probe:config['probe']=json.loads(probe[0])
    request={'task_token':aid,'raw':str(snapshots.blob('raw',capture['raw_sha256'])),'raw_sha256':capture['raw_sha256'],'format':capture['profile']['format'],'profile':capture['profile'],'config':config,'output':str(output)}
    try:
        from .document_supervisor import run
        raw=run(snapshots.db,request,directory);result=json.loads(raw);validate(result)
        if result['raw_sha256']!=capture['raw_sha256']:raise ValueError('处理结果与原件不匹配')
        from .document_results import sha
        with snapshots.pin([('results',sha(raw))]):
            result_sha=snapshots.put('results',raw);capture['result_sha256']=result_sha
            with snapshots.db.connect() as c:
                c.execute('UPDATE document_processing_attempts SET state=?,result_sha256=?,finished_at=? WHERE id=?',(result['status'],result_sha,utcnow(),aid))
        return result
    except Exception as exc:
        with snapshots.db.connect() as c:c.execute("UPDATE document_processing_attempts SET state='failed',error=?,finished_at=? WHERE id=?",(str(exc),utcnow(),aid))
        raise ValueError(str(exc)) from exc
    finally:
        output.unlink(missing_ok=True)


def execution_identity():
    import os,sys
    value={'pid':os.getpid(),'platform':sys.platform}
    if os.name!='nt':return {**value,'uid':os.geteuid(),'gid':os.getegid()}
    import ctypes
    from ctypes import wintypes as w
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);advapi=ctypes.WinDLL('advapi32',use_last_error=True)
    kernel.GetCurrentProcess.restype=w.HANDLE
    advapi.OpenProcessToken.argtypes=[w.HANDLE,w.DWORD,ctypes.POINTER(w.HANDLE)];advapi.OpenProcessToken.restype=w.BOOL
    advapi.GetTokenInformation.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD,ctypes.POINTER(w.DWORD)];advapi.GetTokenInformation.restype=w.BOOL
    advapi.ConvertSidToStringSidW.argtypes=[ctypes.c_void_p,ctypes.POINTER(w.LPWSTR)];advapi.ConvertSidToStringSidW.restype=w.BOOL
    kernel.CloseHandle.argtypes=[w.HANDLE];kernel.LocalFree.argtypes=[ctypes.c_void_p]
    token=w.HANDLE()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(),8,ctypes.byref(token)):raise OSError(ctypes.get_last_error(),'无法读取当前进程token')
    try:
        size=w.DWORD();advapi.GetTokenInformation(token,1,None,0,ctypes.byref(size));buffer=ctypes.create_string_buffer(size.value)
        if not advapi.GetTokenInformation(token,1,buffer,size,ctypes.byref(size)):raise OSError(ctypes.get_last_error(),'无法读取TokenUser')
        sid=ctypes.cast(buffer,ctypes.POINTER(ctypes.c_void_p)).contents.value;text=w.LPWSTR()
        if not advapi.ConvertSidToStringSidW(sid,ctypes.byref(text)):raise OSError(ctypes.get_last_error(),'无法读取实际SID')
        try:value['sid']=text.value
        finally:kernel.LocalFree(ctypes.cast(text,ctypes.c_void_p))
        session=w.DWORD();kernel.ProcessIdToSessionId.argtypes=[w.DWORD,ctypes.POINTER(w.DWORD)];kernel.ProcessIdToSessionId.restype=w.BOOL
        if not kernel.ProcessIdToSessionId(os.getpid(),ctypes.byref(session)):raise OSError(ctypes.get_last_error(),'无法读取实际session')
        value['session_id']=session.value;return value
    finally:kernel.CloseHandle(token)


class Configuration:
    """Persistent creator-only OCR configuration and explicit local probing."""
    def __init__(self,snapshots):
        self.snapshots=snapshots;self.db=snapshots.db
        with self.db.connect() as c:c.execute('CREATE TABLE IF NOT EXISTS document_processing_probe(singleton INTEGER PRIMARY KEY CHECK(singleton=1),revision INTEGER NOT NULL,payload TEXT NOT NULL)')
    @staticmethod
    def _formats():
        from importlib.metadata import version,PackageNotFoundError
        required={'defusedxml':'0.7.1','psutil':'7.2.2','pdfplumber':'0.11.11','pdfminer.six':'20260107','pypdfium2':'5.15.2','Pillow':'13.0.0'}
        actual={}
        for name in required:
            try:actual[name]=version(name)
            except PackageNotFoundError:actual[name]=None
        groups={'docx':['defusedxml','psutil'],'xlsx':['defusedxml','psutil'],'pdf':['pdfplumber','pdfminer.six','pypdfium2','Pillow','psutil']}
        return {format:{'available':all(actual[n]==required[n] for n in names),'components':{n:{'version':actual[n],'required':required[n]} for n in names}} for format,names in groups.items()}
    @staticmethod
    def _file_hash(path):
        import hashlib,os
        digest=hashlib.sha256()
        with Path(path).open('rb') as stream:
            before=os.fstat(stream.fileno())
            for chunk in iter(lambda:stream.read(65536),b''):digest.update(chunk)
            after=os.fstat(stream.fileno())
        if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):raise ValueError('组件文件在探测期间变化')
        return {'sha256':digest.hexdigest(),'bytes':after.st_size}
    @staticmethod
    def _languages(value):
        import re
        if not isinstance(value,str):raise ValueError('languages须为语言名组合')
        names=value.split('+')
        if not {'eng','chi_sim'}.issubset(names) or len(names)!=len(set(names)) or any(not re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*',n) for n in names):raise ValueError('languages须包含eng和chi_sim，且来自已部署语言名单')
        return names
    def _probe(self,config):
        import os,re,subprocess
        result={'identity':execution_identity(),'scope':'current_process','checked_at':utcnow(),'ready':False,'errors':[],'component':{},'language_data':{}}
        try:
            executable=config.get('ocr_executable');directory=config.get('ocr_data_dir');languages=config.get('languages')
            if not executable or not directory or not languages:raise ValueError('OCR尚未配置')
            executable=Path(executable);directory=Path(directory)
            if not executable.is_absolute() or not directory.is_absolute():raise ValueError('OCR程序和语言目录须为绝对路径')
            if not executable.is_file() or not os.access(executable,os.R_OK|os.X_OK):raise ValueError('OCR执行路径不存在或当前身份不可执行')
            if not directory.is_dir() or not os.access(directory,os.R_OK):raise ValueError('OCR语言目录不存在或当前身份不可读')
            names=self._languages(languages)
            result['component']['executable']=self._file_hash(executable)
            for name in names:
                path=directory/(name+'.traineddata')
                if not path.is_file() or not os.access(path,os.R_OK):raise ValueError('OCR语言缺失或当前身份不可读: '+name)
                result['language_data'][name]=self._file_hash(path)
                if not result['language_data'][name]['bytes']:raise ValueError('OCR语言文件为空: '+name)
            version=subprocess.run([str(executable),'--version'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=10)
            info=version.stdout+'\n'+version.stderr
            if version.returncode or not re.search(r'\btesseract\s+v?5(?:\.|\s|$)',info,re.IGNORECASE):raise ValueError('OCR执行路径不是可用的Tesseract5系列: '+info[-1000:])
            result['component']['version']=info.strip()
            listed=subprocess.run([str(executable),'--tessdata-dir',str(directory),'--list-langs'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=10)
            if listed.returncode or not set(names).issubset(set((listed.stdout+'\n'+listed.stderr).splitlines())):raise ValueError('OCR程序未列出所需语言: '+(listed.stdout+listed.stderr)[-1000:])
            result['ready']=True
        except (OSError,ValueError,subprocess.SubprocessError) as exc:result['errors'].append(str(exc))
        return result
    def _view(self,config,probe):
        from .document_results import SCHEMA
        current=execution_identity()
        return {'archive':str(self.db.db_path.resolve()),'identity':current,'config':config,'formats':self._formats(),'receive':{'schema':SCHEMA,'formats':['docx','xlsx','pdf'],'validation':'stdlib'},'ocr':{'configured':all(config.get(k) for k in ('ocr_executable','ocr_data_dir','languages')),'ready':bool(probe and probe.get('ready')),'errors':probe.get('errors',[]) if probe else ['尚未明确运行processing-status --check'],'last_probe':probe},'probe_scope':'当前进程/身份的组件探测；不代表另一服务身份已验证'}
    def status(self,*,check=False):
        with self.db.connect() as c:
            c.execute('BEGIN');config=self.snapshots.config(c);row=c.execute('SELECT * FROM document_processing_probe WHERE singleton=1').fetchone();probe=json.loads(row['payload']) if row and row['revision']==config['revision'] else None
        if check:
            candidate=self._probe(config)
            with self.db.connect() as c:
                c.execute('BEGIN IMMEDIATE')
                if self.snapshots.config(c)['revision']==config['revision']:c.execute('INSERT INTO document_processing_probe VALUES(1,?,?) ON CONFLICT(singleton) DO UPDATE SET revision=excluded.revision,payload=excluded.payload',(config['revision'],json.dumps(candidate,ensure_ascii=False)))
            return self.status()
        return self._view(config,probe)
    def configure(self,*,expected_revision,ocr_executable,ocr_data_dir,languages):
        if type(expected_revision) is not int or expected_revision<0:raise ValueError('配置revision无效')
        if self.snapshots.config()['revision']!=expected_revision:raise ValueError('OCR配置revision已过期，请重新查看processing-status')
        if not Path(ocr_executable).is_absolute() or not Path(ocr_data_dir).is_absolute():raise ValueError('OCR程序和语言目录须为绝对路径')
        candidate={'ocr_executable':str(Path(ocr_executable).resolve()),'ocr_data_dir':str(Path(ocr_data_dir).resolve()),'languages':languages}
        probe=self._probe(candidate)
        if not probe['ready']:raise ValueError('；'.join(probe['errors']))
        with self.db.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if self.snapshots.config(c)['revision']!=expected_revision:raise ValueError('OCR配置revision已过期，请重新查看processing-status')
            revision=expected_revision+1
            c.execute('UPDATE document_processing_config SET revision=?,payload=? WHERE singleton=1',(revision,json.dumps(candidate,ensure_ascii=False)))
            c.execute('INSERT INTO document_processing_probe VALUES(1,?,?) ON CONFLICT(singleton) DO UPDATE SET revision=excluded.revision,payload=excluded.payload',(revision,json.dumps(probe,ensure_ascii=False)))
        return self._view({'revision':revision,**candidate},probe)


def configuration_arguments(actions):
    status=actions.add_parser('processing-status',help='查看创建端格式/接收能力、OCR配置revision与最近探测身份')
    status.add_argument('--check',action='store_true',help='明确探测当前身份下的程序/语言数据，不读文档，不冒称另一服务身份成功')
    configure=actions.add_parser('processing-configure',help='所在创建端持久配置本地OCR；不自动重处理已有资料')
    configure.add_argument('--expected-revision',type=int,required=True,help='原样使用processing-status中config.revision，初始0，过期拒绝')
    configure.add_argument('--ocr-executable',required=True,help='该机器上Tesseract5执行程序的绝对路径')
    configure.add_argument('--ocr-data-dir',required=True,help='预先部署语言数据的绝对目录；处理/查询/启动均不下载')
    configure.add_argument('--languages',required=True,help='可用语言组合，须含eng和chi_sim，保留输入次序，例如chi_sim+eng')
