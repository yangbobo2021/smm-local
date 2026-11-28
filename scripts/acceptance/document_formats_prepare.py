"""008 task-owned OCR materials; network is allowed only in explicit prepare."""
from __future__ import annotations
import argparse,hashlib,json,os,platform,shutil,subprocess,sys,urllib.request
from pathlib import Path

MINIFORGE='26.9.4-2'
INSTALLERS={
 ('Linux','x86_64'):('Linux-x86_64.sh','bbaf16b3897da24c4be50315934ba74848f617b4495982841d6a0a60e0edbbdf'),
 ('Darwin','arm64'):('MacOSX-arm64.sh','fb567612b76f4ef46de326f04425dbe381b6afc6a66c545f5043255a5ef34258'),
 ('Darwin','x86_64'):('MacOSX-x86_64.sh','30e82ce68875fc50b917a3a541ea0516272866584187f7ea980ce8eaf715807d'),
 ('Windows','AMD64'):('Windows-x86_64.exe','9d83983669bc5d3b5dd4c631454bf953c3caf4ac78b9c9ada9971e5b021d83c3')}
LANG_COMMIT='65727574dfcd264acbb0c3e07860e4e9e9b22185'
LANGUAGES={'eng':'7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2','chi_sim':'a5fcb6f0db1e1d6d8522f39db4e848f05984669172e584e8d76b6b3141e1f730'}
FONT_COMMIT='523d033d6cb47f4a80c58a35753646f5c3608a78'
FONT_SHA='2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b'
LICENSE_SHA='6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2'


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as src:
        for chunk in iter(lambda:src.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def download(url,target,expected):
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists() or digest(target)!=expected:
        partial=target.with_suffix(target.suffix+'.partial')
        with urllib.request.urlopen(url,timeout=90) as src,partial.open('wb') as dst:shutil.copyfileobj(src,dst,1024*1024)
        if digest(partial)!=expected:raise ValueError('material SHA mismatch: '+url)
        partial.replace(target)
    return {'path':str(target.resolve()),'sha256':digest(target),'bytes':target.stat().st_size,'source':url}


def command(argv,logs,name,timeout=900):
    run=subprocess.run(list(map(str,argv)),capture_output=True,timeout=timeout)
    logs.mkdir(parents=True,exist_ok=True)
    (logs/(name+'.stdout')).write_bytes(run.stdout);(logs/(name+'.stderr')).write_bytes(run.stderr)
    (logs/(name+'.json')).write_text(json.dumps({'argv':list(map(str,argv)),'exit_code':run.returncode},indent=2),encoding='utf-8')
    if run.returncode:raise RuntimeError(name+' failed: '+run.stderr.decode('utf-8','replace')[-4000:])
    return run.stdout.decode('utf-8','replace')


def executable(prefix,name):return prefix/('Library/bin/'+name+'.exe' if os.name=='nt' else 'bin/'+name)


def prepare(work):
    work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True);logs=work/'logs';cache=work/'materials';cache.mkdir(exist_ok=True)
    suffix,checksum=INSTALLERS[(platform.system(),platform.machine())];name='Miniforge3-'+suffix
    installer=download('https://github.com/conda-forge/miniforge/releases/download/'+MINIFORGE+'/'+name,cache/name,checksum)
    base=work/'miniforge'
    if not base.exists():
        argv=[installer['path'],'/InstallationType=JustMe','/RegisterPython=0','/AddToPath=0','/S','/D='+str(base)] if os.name=='nt' else ['/bin/bash',installer['path'],'-b','-p',str(base)]
        command(argv,logs,'install-miniforge')
    conda=base/('Scripts/conda.exe' if os.name=='nt' else 'bin/conda')
    online=work/'resolved-runtime'
    if not online.exists():command([conda,'create','-y','--override-channels','-c','conda-forge','-p',online,'tesseract=5.5.4','leptonica=1.87.0'],logs,'resolve-ocr')
    packages=[];explicit=['@EXPLICIT']
    for metadata in sorted((online/'conda-meta').glob('*.json')):
        info=json.loads(metadata.read_text(encoding='utf-8'));url=info['url'];sha=info['sha256'];package=cache/'packages'/url.rsplit('/',1)[1]
        item=download(url,package,sha);item.update(name=info['name'],version=info['version'],build=info['build']);packages.append(item)
        # Conda explicit-file syntax uses MD5; trust derives from the SHA check above.
        md5=hashlib.md5(package.read_bytes()).hexdigest();explicit.append(package.as_uri()+'#'+md5)
    manifest=work/'offline-explicit.txt';manifest.write_text('\n'.join(explicit)+'\n',encoding='utf-8')
    offline=work/'offline-runtime'
    if not offline.exists():command([conda,'create','-y','--offline','-p',offline,'--file',manifest],logs,'install-offline-ocr')
    data=work/'tessdata';language_files={name:download('https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/'+LANG_COMMIT+'/'+name+'.traineddata',data/(name+'.traineddata'),sha) for name,sha in LANGUAGES.items()}
    font=download('https://raw.githubusercontent.com/notofonts/noto-cjk/'+FONT_COMMIT+'/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf',cache/'font/NotoSansCJKsc-Regular.otf',FONT_SHA)
    license=download('https://raw.githubusercontent.com/notofonts/noto-cjk/'+FONT_COMMIT+'/LICENSE',cache/'font/LICENSE',LICENSE_SHA)
    engine=executable(offline,'tesseract');version=command([engine,'--version'],logs,'offline-ocr-version',30)
    langs=command([engine,'--tessdata-dir',data,'--list-langs'],logs,'offline-ocr-languages',30)
    if 'tesseract 5.5.4' not in version or not set(LANGUAGES).issubset(set(langs.splitlines())):raise ValueError('offline runtime contract mismatch')
    # Versioned .so.N files and extensionless programs are part of the actual
    # installation too; freeze every regular file, plus each private symlink.
    installed={p.relative_to(offline).as_posix():digest(p) for p in offline.rglob('*') if p.is_file() and not p.is_symlink()}
    links={}
    for path in offline.rglob('*'):
        if not path.is_symlink():continue
        target=path.resolve()
        if not target.is_relative_to(offline):raise ValueError('runtime link escapes private prefix: '+str(path))
        links[path.relative_to(offline).as_posix()]={'target':os.readlink(path),'resolved':target.relative_to(offline).as_posix(),'sha256':digest(target) if target.is_file() else None}
    components={name:sha for name,sha in installed.items() if name.lower().endswith(('.exe','.dll','.dylib','.so')) or '.so.' in name.lower() or name.startswith('bin/')}
    if os.name!='nt':components['bin/tesseract']=digest(engine)
    return {'phase':'G0-I materials only','platform':platform.platform(),'machine':platform.machine(),'python':sys.version,'installer':installer,'packages':packages,'offline_components':components,'installed_file_sha256':installed,'installed_links':links,'ocr_executable':str(engine),'ocr_data_dir':str(data),'font':font,'font_license':license,'languages':language_files,'version':version,'list_languages':langs}


def probe():
    from importlib.metadata import version
    from smm_local.document_processing import execution_identity
    import defusedxml,pdfplumber,pdfminer,pypdfium2,PIL,psutil
    return {'phase':'G0-I imports only; no business acceptance','identity':execution_identity(),'python':sys.version,'packages':{n:version(n) for n in ('defusedxml','pdfplumber','pdfminer.six','pypdfium2','Pillow','psutil')}}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=['prepare','probe']);parser.add_argument('--work',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    value=prepare(args.work) if args.phase=='prepare' else probe()
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'phase':value['phase'],'output':str(args.output)},ensure_ascii=False))

if __name__=='__main__':main()
