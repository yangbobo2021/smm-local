"""Private CI evidence envelopes; never handles product data paths by default."""
from __future__ import annotations
import argparse,base64,hashlib,json,os,stat,struct,tempfile,zipfile
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath

MAGIC=b'SMM008E1\n'
BLOCK=1024*1024

def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def sha(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(BLOCK),b''):result.update(block)
    return result.hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def b64(raw):return base64.b64encode(raw).decode('ascii')
def unb64(value):return base64.b64decode(value,validate=True)
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as out:json.dump(value,out,ensure_ascii=False,indent=2);out.write('\n')
def safe_name(name):
    path=PurePosixPath(name)
    if not name or '\\' in name or path.is_absolute() or any(part in ('..','') for part in path.parts) or ':' in name:raise ValueError('unsafe evidence path')
    return path

def derive(private,public,salt):
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes
    return HKDF(algorithm=hashes.SHA256(),length=32,salt=salt,info=MAGIC).derive(private.exchange(public))

def keygen(directory):
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    directory=Path(directory);directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    private=X25519PrivateKey.generate();public=private.public_key()
    secret=private.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
    public_pem=public.public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
    for name,raw in [('private.pem',secret),('public.pem',public_pem)]:
        fd=os.open(directory/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
    # Reload the durable private file, not the in-memory object, for the probe.
    loaded=serialization.load_pem_private_key((directory/'private.pem').read_bytes(),password=None)
    peer=X25519PrivateKey.generate();salt=os.urandom(32);nonce=os.urandom(12);sample=os.urandom(32)
    encrypted=AESGCM(derive(peer,public,salt)).encrypt(nonce,sample,MAGIC)
    if AESGCM(derive(loaded,peer.public_key(),salt)).decrypt(nonce,encrypted,MAGIC)!=sample:raise ValueError('persisted key selfcheck failed')
    receipt={'status':'persisted_verified','public_key_sha256':sha(directory/'public.pem'),'private_file_mode':oct(stat.S_IMODE((directory/'private.pem').stat().st_mode)),'checked_at':now(),'probe':'fresh bytes encrypted with public key, decrypted with reloaded durable private key'}
    save(directory/'key-receipt.json',receipt);return receipt

def pack(source,public_key,context,output):
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey,X25519PublicKey
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
    source=Path(source).resolve();output=Path(output).resolve();public_key=Path(public_key)
    if output.is_relative_to(source):raise ValueError('envelope must be outside source')
    public=serialization.load_pem_public_key(public_key.read_bytes())
    if not isinstance(public,X25519PublicKey):raise ValueError('wrong public key type')
    for field in ('run_id','job_key','commit'):
        if not context.get(field):raise ValueError('missing evidence context: '+field)
    files={}
    for path in sorted(source.rglob('*')):
        if path.is_symlink():raise ValueError('evidence symlinks are not accepted')
        if path.is_dir():continue
        if not path.is_file():raise ValueError('evidence is not a regular file')
        name=path.relative_to(source).as_posix();safe_name(name)
        if name=='evidence-manifest.json':raise ValueError('reserved manifest name')
        files[name]={'sha256':sha(path),'bytes':path.stat().st_size}
    if not files:raise ValueError('empty evidence')
    manifest={'schema':'smm-008-evidence-v1','context':context,'files':files,'created_at':now()};manifest_raw=canonical(manifest)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='smm008-evidence-') as temporary:
        zipped=Path(temporary)/'payload.zip'
        with zipfile.ZipFile(zipped,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
            bundle.writestr('evidence-manifest.json',manifest_raw)
            for name,expected in files.items():
                bundle.write(source/name,name)
                if sha(source/name)!=expected['sha256'] or (source/name).stat().st_size!=expected['bytes']:raise ValueError('evidence changed while packing')
        ephemeral=X25519PrivateKey.generate();salt=os.urandom(32);nonce=os.urandom(12)
        header={'schema':'smm-008-envelope-v1','context':context,'manifest_sha256':hashlib.sha256(manifest_raw).hexdigest(),'public_key_sha256':sha(public_key),'ephemeral_public':b64(ephemeral.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)),'salt':b64(salt),'nonce':b64(nonce)}
        header_raw=canonical(header);aad=MAGIC+struct.pack('>I',len(header_raw))+header_raw
        encryptor=Cipher(algorithms.AES(derive(ephemeral,public,salt)),modes.GCM(nonce)).encryptor();encryptor.authenticate_additional_data(aad)
        with output.open('xb') as out,zipped.open('rb') as payload:
            out.write(aad)
            for chunk in iter(lambda:payload.read(BLOCK),b''):out.write(encryptor.update(chunk))
            out.write(encryptor.finalize());out.write(encryptor.tag);out.flush();os.fsync(out.fileno())
    return {'status':'generated','envelope_sha256':sha(output),'manifest_sha256':header['manifest_sha256'],'context':context,'files':len(files),'generated_at':now()}

def decrypt(envelope,private_key,output,expected_context):
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey,X25519PublicKey
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
    private=serialization.load_pem_private_key(Path(private_key).read_bytes(),password=None)
    if not isinstance(private,X25519PrivateKey):raise ValueError('wrong private key type')
    expected_public=private.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
    with Path(envelope).open('rb') as source:
        if source.read(len(MAGIC))!=MAGIC:raise ValueError('unknown evidence envelope')
        size_raw=source.read(4)
        if len(size_raw)!=4:raise ValueError('truncated envelope header')
        size=struct.unpack('>I',size_raw)[0]
        if not 1<=size<=65536:raise ValueError('invalid envelope header length')
        header_raw=source.read(size);header=json.loads(header_raw)
        if header['schema']!='smm-008-envelope-v1' or header['public_key_sha256']!=hashlib.sha256(expected_public).hexdigest():raise ValueError('wrong evidence key')
        if header['context']!=expected_context:raise ValueError('evidence context mismatch')
        start=source.tell();source.seek(0,2);end=source.tell();remaining=end-start-16
        if remaining<0:raise ValueError('truncated envelope')
        source.seek(end-16);tag=source.read(16);source.seek(start)
        decryptor=Cipher(algorithms.AES(derive(private,X25519PublicKey.from_public_bytes(unb64(header['ephemeral_public'])),unb64(header['salt']))),modes.GCM(unb64(header['nonce']),tag)).decryptor()
        decryptor.authenticate_additional_data(MAGIC+size_raw+header_raw)
        with Path(output).open('xb') as target:
            while remaining:
                block=source.read(min(BLOCK,remaining))
                if not block:raise ValueError('truncated ciphertext')
                remaining-=len(block);target.write(decryptor.update(block))
            target.write(decryptor.finalize());target.flush();os.fsync(target.fileno())
    return header

def open_evidence(path):
    # Actual format readers are independent of the product parser/index.
    path=Path(path);suffix=path.suffix.lower()
    if suffix=='.png':
        from PIL import Image
        with Image.open(path) as image:image.load();return {'reader':'Pillow','size':list(image.size)}
    if suffix=='.pdf':
        import pypdfium2
        with pypdfium2.PdfDocument(path) as doc:
            pages=len(doc)
            if pages<1:raise ValueError('empty PDF evidence')
            page=doc[0];bitmap=page.render(scale=.25);image=bitmap.to_pil();image.load();image.close();bitmap.close();page.close()
            return {'reader':'PDFium','pages':pages}
    if suffix in ('.docx','.xlsx','.zip'):
        with zipfile.ZipFile(path) as bundle:
            if bundle.testzip() is not None:raise ValueError('corrupt inner evidence zip')
            names=bundle.namelist()
            for name in names:safe_name(name)
            if suffix in ('.docx','.xlsx'):
                from defusedxml.ElementTree import fromstring
                if '[Content_Types].xml' not in names:raise ValueError('invalid Office evidence')
                for name in names:
                    if name.endswith('.xml'):fromstring(bundle.read(name))
            traces=[name for name in names if name.endswith('.trace')]
            for name in traces:
                for line in bundle.read(name).splitlines():json.loads(line)
            return {'reader':'zip/XML/trace-JSON','members':len(names),'traces':len(traces)}
    if suffix=='.json':
        with path.open(encoding='utf-8') as stream:value=json.load(stream)
        return {'reader':'JSON','root_type':type(value).__name__}
    # Read every byte even for formats that need later human review.
    with path.open('rb') as stream:
        count=sum(len(chunk) for chunk in iter(lambda:stream.read(BLOCK),b''))
    return {'reader':'binary','bytes':count}

def verify(artifact,metadata,private_key,context,destination,cleanup=None):
    artifact=Path(artifact);destination=Path(destination)
    if metadata.get('workflow_run',{}).get('id')!=int(context['run_id']):raise ValueError('artifact run mismatch')
    if metadata.get('workflow_run',{}).get('head_sha')!=context['commit']:raise ValueError('artifact commit mismatch')
    if metadata.get('name')!=context['artifact_name']:raise ValueError('artifact name mismatch')
    if not metadata.get('id') or metadata.get('digest')!='sha256:'+sha(artifact):raise ValueError('artifact digest mismatch')
    if metadata.get('size_in_bytes')!=artifact.stat().st_size:raise ValueError('artifact size mismatch')
    if destination.exists():raise ValueError('recovery destination already exists')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='smm008-recover-',dir=destination.parent) as temporary:
        temporary=Path(temporary)
        with zipfile.ZipFile(artifact) as outer:
            members=[info for info in outer.infolist() if not info.is_dir()]
            if len(members)!=1 or not members[0].filename.endswith('.smm-evidence'):raise ValueError('expected one encrypted evidence member')
            member=members[0];safe_name(member.filename)
            if stat.S_ISLNK(member.external_attr>>16):raise ValueError('artifact symlink')
            envelope=temporary/'envelope';
            with outer.open(member) as src,envelope.open('xb') as out:
                for chunk in iter(lambda:src.read(BLOCK),b''):out.write(chunk)
        payload=temporary/'payload.zip';header=decrypt(envelope,private_key,payload,context)
        recovered=temporary/'recovered';recovered.mkdir();opened={}
        with zipfile.ZipFile(payload) as inner:
            infos=inner.infolist();names=[info.filename for info in infos]
            if len(names)!=len(set(names)) or any(info.is_dir() or stat.S_ISLNK(info.external_attr>>16) for info in infos):raise ValueError('invalid payload members')
            manifest_raw=inner.read('evidence-manifest.json')
            if hashlib.sha256(manifest_raw).hexdigest()!=header['manifest_sha256']:raise ValueError('manifest digest mismatch')
            manifest=json.loads(manifest_raw)
            if manifest.get('schema')!='smm-008-evidence-v1' or manifest.get('context')!=context:raise ValueError('manifest context mismatch')
            if set(names)!={'evidence-manifest.json',*manifest['files']}:raise ValueError('manifest file set mismatch')
            for name,item in manifest['files'].items():
                relative=safe_name(name);path=recovered.joinpath(*relative.parts);path.parent.mkdir(parents=True,exist_ok=True)
                with inner.open(name) as src,path.open('xb') as out:
                    for chunk in iter(lambda:src.read(BLOCK),b''):out.write(chunk)
                if path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:raise ValueError('evidence file digest mismatch')
                opened[name]=open_evidence(path)
            if cleanup:
                safe_name(cleanup)
                if cleanup not in manifest['files']:raise ValueError('missing cleanup evidence')
                value=json.loads((recovered/cleanup).read_text(encoding='utf-8'))
                if value.get('status')!='verified' or not value.get('checks') or any(c.get('before') is None or c.get('after') is None or c.get('passed') is not True for c in value['checks']):raise ValueError('incomplete cleanup evidence')
            (recovered/'evidence-manifest.json').write_bytes(manifest_raw)
        receipt={'status':'recovered_verified','artifact_id':metadata['id'],'run_id':int(context['run_id']),'artifact_sha256':sha(artifact),'manifest_sha256':header['manifest_sha256'],'context':context,'opened':opened,'cleanup':cleanup,'recovered_at':now(),'artifact_expires_at':metadata.get('expires_at'),'retained_copy_after_expiry':metadata.get('expired',False)}
        save(recovered/'recovered-verified.json',receipt);recovered.rename(destination)
    return receipt

def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    key=commands.add_parser('keygen');key.add_argument('--directory',type=Path,required=True)
    generate=commands.add_parser('pack');generate.add_argument('--source',type=Path,required=True);generate.add_argument('--public-key',type=Path,required=True);generate.add_argument('--context',type=Path,required=True);generate.add_argument('--output',type=Path,required=True);generate.add_argument('--receipt',type=Path,required=True)
    recover=commands.add_parser('verify');recover.add_argument('--artifact',type=Path,required=True);recover.add_argument('--metadata',type=Path,required=True);recover.add_argument('--private-key',type=Path,required=True);recover.add_argument('--context',type=Path,required=True);recover.add_argument('--output',type=Path,required=True);recover.add_argument('--cleanup');recover.add_argument('--receipt',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='keygen':result=keygen(args.directory)
    elif args.command=='pack':result=pack(args.source,args.public_key,json.loads(args.context.read_text(encoding='utf-8')),args.output);save(args.receipt,result)
    else:
        try:result=verify(args.artifact,json.loads(args.metadata.read_text(encoding='utf-8')),args.private_key,json.loads(args.context.read_text(encoding='utf-8')),args.output,args.cleanup)
        except Exception as error:result={'status':'incomplete','error_type':type(error).__name__,'error':str(error),'checked_at':now()}
        save(args.receipt,result)
    print(json.dumps({k:v for k,v in result.items() if k!='opened'},ensure_ascii=False));return 1 if result['status']=='incomplete' else 0
if __name__=='__main__':raise SystemExit(main())
