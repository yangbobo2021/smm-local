import hashlib, json, sys, zlib
from pathlib import Path
from pdfminer.pdftypes import PDFStream
from pdfminer.psparser import LIT
class LimitExceeded(Exception):pass
class Counter:
 def __init__(self,page_limit,total_limit):self.page_limit=page_limit;self.total_limit=total_limit;self.total=0;self.peak_retained=0
 def flate(self,raw):
  decoder=zlib.decompressobj();out=bytearray();source=raw
  while source:
   remaining=min(self.page_limit-len(out),self.total_limit-self.total)
   piece=decoder.decompress(source,min(65536,remaining+1));source=decoder.unconsumed_tail
   if len(piece)>remaining:raise LimitExceeded('decoded quota before retaining overflow')
   out.extend(piece);self.total+=len(piece);self.peak_retained=max(self.peak_retained,len(out))
   if not source:break
  if not decoder.eof:raise ValueError('truncated compressed stream')
  return bytes(out)
class Guarded(PDFStream):
 def __init__(self,*args,counter,**kwargs):super().__init__(*args,**kwargs);self.counter=counter
 def decode(self):
  filters=self.get_filters()
  if len(filters)!=1 or filters[0][0]!=LIT('FlateDecode'):raise ValueError('prototype covers Flate only; no unsafe fallback')
  self.data=self.counter.flate(self.rawdata);self.rawdata=None
M=1024*1024;rows=[]
for size in [32*M,32*M+1]:
 counter=Counter(32*M,128*M);stream=Guarded({'Filter':LIT('FlateDecode')},zlib.compress(b'x'*size),counter=counter)
 try:value=stream.get_data();state='allowed';assert len(value)==size
 except LimitExceeded:state='rejected'
 assert state==('allowed' if size==32*M else 'rejected')
 rows.append({'decoded_bytes':size,'result':state,'peak_retained_bytes':counter.peak_retained,'limit_bytes':32*M})
counter=Counter(32*M,128*M)
for i in range(4):assert len(Guarded({'Filter':LIT('FlateDecode')},zlib.compress(b'x'*(32*M)),counter=counter).get_data())==32*M
try:Guarded({'Filter':LIT('FlateDecode')},zlib.compress(b'x'),counter=counter).get_data();raise AssertionError('global overflow allowed')
except LimitExceeded:pass
report={'purpose':'bounded Flate adapter feasibility, not SMM acceptance','pdfminer_version':'20260107','page_boundary_cases':rows,'global_equal_bytes':counter.total,'global_plus_one_rejected':True,'non_flate_filters_verified':False,'pdfium_safe_input_verified':False}
Path(sys.argv[1]).write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
