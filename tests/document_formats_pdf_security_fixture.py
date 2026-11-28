"""Independent PDF image/filter samples; no product imports or output truth."""
from io import BytesIO
import struct,zlib
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageStat


def pdf_objects(objects):
    out=bytearray(b'%PDF-1.7\n');offsets=[]
    for number,value in enumerate(objects,1):
        offsets.append(len(out));out.extend(str(number).encode()+b' 0 obj\n'+value+b'\nendobj\n')
    start=len(out);out.extend(('xref\n0 '+str(len(objects)+1)+'\n0000000000 65535 f \n').encode())
    for offset in offsets:out.extend(('%010d 00000 n \n'%offset).encode())
    out.extend(('trailer\n<< /Size '+str(len(objects)+1)+' /Root 1 0 R >>\nstartxref\n'+str(start)+'\n%%EOF\n').encode());return bytes(out)


def stream(attrs,data):return b'<< '+attrs+b' /Length '+str(len(data)).encode()+b' >>\nstream\n'+data+b'\nendstream'


def image_pdf(encoded,width,height,filter_name,*,bits=8,color='DeviceRGB',params=b'',inline=False):
    imageattrs=('/Width %d /Height %d /BitsPerComponent %d /ColorSpace /%s /Filter /%s'%(width,height,bits,color,filter_name)).encode()+params
    if inline:
        content=b'q 240 0 0 120 0 0 cm BI '+imageattrs+b' ID\n'+encoded+b'\nEI Q';resources=b'<< >>'
    else:
        content=b'q 240 0 0 120 0 0 cm /Raster Do Q';resources=b'<< /XObject << /Raster 5 0 R >> >>'
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Count 1 /Kids [3 0 R] >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 240 120] /Resources '+resources+b' /Contents 4 0 R >>',stream(b'',content)]
    if not inline:objects.append(stream(b'/Type /XObject /Subtype /Image '+imageattrs,encoded))
    return pdf_objects(objects)


def raster(font,key,codec):
    im=Image.new('RGB',(1600,800),'white');dr=ImageDraw.Draw(im);font=ImageFont.truetype(str(font),64)
    lines=[key.upper()+' RASTER 12345.67','文档检索 中文英文']
    for n,line in enumerate(lines):dr.text((100,130+n*220),line,font=font,fill='black')
    output=BytesIO();bits=8;color='DeviceRGB';params=b''
    if codec=='DCTDecode':
        im.save(output,format='JPEG',quality=98);raw=output.getvalue()
        with Image.open(BytesIO(raw)) as decoded:
            decoded.load();assert decoded.size==im.size and max(ImageStat.Stat(ImageChops.difference(im,decoded.convert('RGB'))).mean)<2
    elif codec=='JPXDecode':
        im.save(output,format='JPEG2000',irreversible=False);raw=output.getvalue()
        with Image.open(BytesIO(raw)) as decoded:assert decoded.size==im.size and decoded.tobytes()==im.tobytes()
    elif codec=='CCITTFaxDecode':
        mono=im.convert('1');mono.save(output,format='TIFF',compression='group4',tiffinfo={278:800})
        with Image.open(BytesIO(output.getvalue())) as tif:
            assert tif.size==mono.size and tif.tobytes()==mono.tobytes()
            offsets=tif.tag_v2[273];lengths=tif.tag_v2[279];assert len(offsets)==len(lengths)==1
            raw=output.getvalue()[offsets[0]:offsets[0]+lengths[0]]
        bits=1;color='DeviceGray';params=b' /DecodeParms << /K -1 /Columns 1600 /Rows 800 /BlackIs1 false >>'
    elif codec=='FlateDecode':
        raw=zlib.compress(im.tobytes());assert zlib.decompress(raw)==im.tobytes()
    else:raise AssertionError(codec)
    return image_pdf(raw,1600,800,codec,bits=bits,color=color,params=params,inline=codec=='FlateDecode'),{'lines':lines,'text':'\n'.join(lines)}


def content_pdf(streams,page_streams):
    # Independent object numbering: catalog1, pages2, pages3.., content after.
    pages=len(page_streams);first=3+pages
    kids=' '.join(str(i+3)+' 0 R' for i in range(pages))
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',('<< /Type /Pages /Count '+str(pages)+' /Kids ['+kids+'] >>').encode()]
    for indices in page_streams:
        refs=' '.join(str(first+index)+' 0 R' for index in indices)
        objects.append(('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Resources << >> /Contents ['+refs+'] >>').encode())
    for raw in streams:objects.append(stream(b'/Filter /FlateDecode',zlib.compress(raw)))
    return pdf_objects(objects)
