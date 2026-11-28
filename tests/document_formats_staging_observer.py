"""Observe actual raw/result writes and worker launches without blocking them."""
import builtins,io,os,subprocess
from pathlib import Path


def observe_capacity_writes(monkeypatch,root):
    root=Path(root).resolve();events=[];descriptors={}
    def relevant(file):
        if not isinstance(file,(str,bytes,os.PathLike)):return None
        path=Path(os.fsdecode(file)).resolve()
        try:relative=path.relative_to(root)
        except ValueError:return None
        if relative.parts and (relative.parts[0] in {'raw','results','pending','transfers'} or relative.parts[0].startswith('.pending-')):return str(path)
        return None
    def record(path,kind,count):
        if path and count>0:events.append({'kind':kind,'path':path,'bytes':count})
    class Stream:
        def __init__(self,stream,path):self.stream=stream;self.path=path
        def __getattr__(self,name):return getattr(self.stream,name)
        def __enter__(self):self.stream.__enter__();return self
        def __exit__(self,*args):
            descriptors.pop(self.stream.fileno(),None);return self.stream.__exit__(*args)
        def close(self):
            if not self.stream.closed:descriptors.pop(self.stream.fileno(),None)
            return self.stream.close()
        def write(self,data):
            result=self.stream.write(data)
            record(self.path,'stream.write',len(data.encode('utf-8') if isinstance(data,str) else data))
            return result
        def writelines(self,lines):
            for line in lines:self.write(line)
        def truncate(self,size=None):
            before=os.fstat(self.stream.fileno()).st_size;result=self.stream.truncate(size)
            record(self.path,'stream.truncate',max(0,os.fstat(self.stream.fileno()).st_size-before));return result
    def wrap_open(original):
        def opened(file,mode='r',*args,**kwargs):
            path=descriptors.get(file) if isinstance(file,int) else relevant(file)
            value=original(file,mode,*args,**kwargs)
            if not isinstance(file,int):descriptors.pop(value.fileno(),None)
            if path and any(flag in mode for flag in 'wax+'):
                descriptors[value.fileno()]=path;return Stream(value,path)
            return value
        return opened
    monkeypatch.setattr(builtins,'open',wrap_open(builtins.open));monkeypatch.setattr(io,'open',wrap_open(io.open))
    original_open=os.open
    def fd_open(file,flags,*args,**kwargs):
        value=original_open(file,flags,*args,**kwargs);descriptors.pop(value,None);path=relevant(file)
        if path and flags&(os.O_WRONLY|os.O_RDWR):descriptors[value]=path
        return value
    monkeypatch.setattr(os,'open',fd_open)
    original_close=os.close
    def close(fd):
        descriptors.pop(fd,None);return original_close(fd)
    monkeypatch.setattr(os,'close',close)
    original_fdopen=os.fdopen
    def fdopen(file,mode='r',*args,**kwargs):
        path=descriptors.get(file);stream=original_fdopen(file,mode,*args,**kwargs)
        return Stream(stream,path) if path and any(flag in mode for flag in 'wax+') and not isinstance(stream,Stream) else stream
    monkeypatch.setattr(os,'fdopen',fdopen)
    original_write=os.write
    def write(fd,data):
        count=original_write(fd,data);record(descriptors.get(fd),'os.write',count);return count
    monkeypatch.setattr(os,'write',write)
    def wrap_move(original):
        def moved(source,target,*args,**kwargs):
            value=original(source,target,*args,**kwargs);path=relevant(target)
            if path and Path(path).is_file():record(path,'move',Path(path).stat().st_size)
            return value
        return moved
    monkeypatch.setattr(os,'rename',wrap_move(os.rename));monkeypatch.setattr(os,'replace',wrap_move(os.replace))
    original_popen=subprocess.Popen
    def popen(*args,**kwargs):
        child=original_popen(*args,**kwargs);events.append({'kind':'worker-launch','pid':child.pid});return child
    monkeypatch.setattr(subprocess,'Popen',popen)
    return events
