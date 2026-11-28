"""Content child: wait for supervision gate before importing optional readers."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--task-token',required=True);args=parser.parse_args()
    request=json.loads(sys.stdin.buffer.readline(65537))
    if request.get('task_token')!=args.task_token:raise ValueError('worker任务门身份不符')
    raw=Path(request['raw']).read_bytes()
    if len(raw)>20*1024*1024 or hashlib.sha256(raw).hexdigest()!=request['raw_sha256']:raise ValueError('保存原件损坏或超限')
    if request['format']=='docx':
        from .document_formats.word import parse
    elif request['format']=='xlsx':
        from .document_formats.spreadsheet import parse
    elif request['format']=='pdf':
        from .document_formats.pdf import parse
    else:raise ValueError('创建端尚未实现此格式处理')
    from .document_results import encode
    from importlib.metadata import version
    names=['defusedxml','psutil'] if request['format'] in {'docx','xlsx'} else ['pdfplumber','pdfminer.six','pypdfium2','Pillow','psutil']
    request['profile']={**request['profile'],'components':{name:version(name) for name in names}}
    result=parse(raw,request['raw_sha256'],request['profile'],config=request.get('config',{})) if request['format']=='pdf' else parse(raw,request['raw_sha256'],request['profile'])
    output=Path(request['output']);output.write_bytes(encode(result))


if __name__=='__main__':main()
