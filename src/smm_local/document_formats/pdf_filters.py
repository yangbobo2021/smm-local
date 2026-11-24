"""Incremental PDF filter outputs. Never use bulk zlib/PDFStream.decode."""
from __future__ import annotations
import math
import zlib

CHUNK=65536


class Sink:
    def __init__(self,budget,stream):self.budget=budget;self.stream=stream;self.data=bytearray()
    @property
    def remaining(self):return self.budget.remaining(self.stream)
    def write(self,value):
        self.budget.charge(self.stream,len(value));self.data.extend(value)
    def finish(self):return bytes(self.data)


def flate(data,sink):
    decoder=zlib.decompressobj()
    for offset in range(0,len(data),CHUNK):
        pending=data[offset:offset+CHUNK]
        while pending:
            piece=decoder.decompress(pending,min(CHUNK,sink.remaining+1));pending=decoder.unconsumed_tail;sink.write(piece)
    while not decoder.eof:
        piece=decoder.decompress(b'',min(CHUNK,sink.remaining+1))
        if not piece:raise ValueError('损坏/截断的Flate流')
        sink.write(piece)
    if decoder.unused_data.strip(b'\x00\t\n\f\r '):raise ValueError('Flate流尾包含未知载荷')
    return sink.finish()


def ascii_hex(data,sink):
    nibble=None;ended=False
    for char in data:
        if char in b'\x00\t\n\f\r ':continue
        if ended:raise ValueError('ASCIIHex流尾包含载荷')
        if char==62:ended=True;continue
        if 48<=char<=57:value=char-48
        elif 65<=char<=70:value=char-55
        elif 97<=char<=102:value=char-87
        else:raise ValueError('非法ASCIIHex字符')
        if nibble is None:nibble=value
        else:sink.write(bytes([(nibble<<4)|value]));nibble=None
    if nibble is not None:sink.write(bytes([nibble<<4]))
    return sink.finish()


def ascii_85(data,sink):
    group=[];index=0;ended=False
    while index<len(data):
        char=data[index];index+=1
        if char in b'\x00\t\n\f\r ':continue
        if index==1 and data[:2]==b'<~':index=2;continue
        if char==126:
            if data[index:index+1]!=b'>':raise ValueError('ASCII85终止符无效')
            index+=1;ended=True
            if data[index:].strip(b'\x00\t\n\f\r '):raise ValueError('ASCII85流尾包含载荷')
            break
        if char==122:
            if group:raise ValueError('ASCII85 z不在组边界')
            sink.write(b'\0'*4);continue
        if not 33<=char<=117:raise ValueError('非法ASCII85字符')
        group.append(char-33)
        if len(group)==5:
            number=0
            for item in group:number=number*85+item
            if number>0xffffffff:raise ValueError('ASCII85组数值越界')
            sink.write(number.to_bytes(4,'big'));group=[]
    if len(group)==1:raise ValueError('ASCII85末组长度无效')
    if group:
        count=len(group);number=0
        for item in group+[84]*(5-count):number=number*85+item
        if number>0xffffffff:raise ValueError('ASCII85末组越界')
        sink.write(number.to_bytes(4,'big')[:count-1])
    return sink.finish()


def run_length(data,sink):
    index=0
    while index<len(data):
        length=data[index];index+=1
        if length==128:return sink.finish()
        if length<128:
            count=length+1;value=data[index:index+count]
            if len(value)!=count:raise ValueError('截断的RunLength流')
            index+=count;sink.write(value)
        else:
            if index>=len(data):raise ValueError('截断的RunLength重复段')
            sink.write(bytes([data[index]])*(257-length));index+=1
    raise ValueError('RunLength缺少终止符')


def lzw(data,sink,early_change=1):
    if early_change not in (0,1):raise ValueError('LZW EarlyChange无效')
    bit=0;width=9;table={i:bytes([i]) for i in range(256)};next_code=258;previous=None
    while bit+width<=len(data)*8:
        value=0
        for _ in range(width):value=(value<<1)|((data[bit//8]>>(7-bit%8))&1);bit+=1
        if value==256:
            table={i:bytes([i]) for i in range(256)};next_code=258;width=9;previous=None;continue
        if value==257:return sink.finish()
        if value in table:entry=table[value]
        elif value==next_code and previous is not None:entry=previous+previous[:1]
        else:raise ValueError('非法LZW码')
        sink.write(entry)
        if previous is not None and next_code<4096:
            table[next_code]=previous+entry[:1];next_code+=1
            if width<12 and next_code+early_change==(1<<width):width+=1
        previous=entry
    raise ValueError('LZW缺少终止码')


def predictor(data,params,maximum):
    number=int(params.get('Predictor',1))
    if number==1:return data
    columns=int(params.get('Columns',1));colors=int(params.get('Colors',1));bits=int(params.get('BitsPerComponent',8))
    if columns<1 or colors<1 or bits not in (1,2,4,8,16):raise ValueError('预测器尺寸/位深无效')
    rowbytes=(columns*colors*bits+7)//8
    if rowbytes>maximum:raise ValueError('预测器行超过PDF解码预算')
    if number==2:
        if len(data)%rowbytes:raise ValueError('TIFF预测器行截断')
        output=bytearray(data);mask=(1<<bits)-1;samples=columns*colors
        def get(row,sample):
            offset=row*rowbytes*8+sample*bits;value=0
            for i in range(bits):value=(value<<1)|((output[(offset+i)//8]>>(7-(offset+i)%8))&1)
            return value
        def put(row,sample,value):
            offset=row*rowbytes*8+sample*bits
            for i in range(bits):
                shift=7-(offset+i)%8;at=(offset+i)//8
                output[at]=(output[at]&~(1<<shift))|(((value>>(bits-1-i))&1)<<shift)
        for row in range(len(data)//rowbytes):
            for sample in range(colors,samples):put(row,sample,(get(row,sample)+get(row,sample-colors))&mask)
        return bytes(output)
    if not 10<=number<=15:raise ValueError('不支持的PDF预测器')
    encoded_width=rowbytes+1
    if len(data)%encoded_width:raise ValueError('PNG预测器行截断')
    output=bytearray();previous=bytes(rowbytes);pixel=(colors*bits+7)//8
    for offset in range(0,len(data),encoded_width):
        kind=data[offset];row=bytearray(data[offset+1:offset+encoded_width])
        if kind>4:raise ValueError('PNG预测器行类型无效')
        for index in range(rowbytes):
            a=row[index-pixel] if index>=pixel else 0;b=previous[index];c=previous[index-pixel] if index>=pixel else 0
            if kind==1:guess=a
            elif kind==2:guess=b
            elif kind==3:guess=(a+b)//2
            elif kind==4:
                p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c);guess=a if pa<=pb and pa<=pc else b if pb<=pc else c
            else:guess=0
            row[index]=(row[index]+guess)&255
        output.extend(row);previous=row
    return bytes(output)
