"""Source-authored PDF filters, nested forms and compressed-object fixtures."""
import struct
import zlib
import base64

from document_formats_pdf_security_fixture import image_pdf, pdf_objects, stream

# Independent fixture layout follows ISO32000-1 sections7.4/7.5/8.10:
# https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf


def predictor_image(number, variant):
    first=10 if variant==0 else 70
    truth=bytes([first,first+10,first+20,first+30,first+40,first+50])
    rows={
        2:bytes([first,10,10,first+30,10,10]),
        10:bytes([0,first,first+10,first+20,0,first+30,first+40,first+50]),
        11:bytes([1,first,10,10,1,first+30,10,10]),
        12:bytes([2,first,first+10,first+20,2,30,30,30]),
        13:bytes([3,first,first//2+10,first//2+15,3,first//2+30,20,20]),
        14:bytes([4,first,10,10,4,30,10,10]),
        15:bytes([1,first,10,10,4,30,10,10]),
    }
    params=(' /DecodeParms << /Predictor '+str(number)+' /Columns 3 /Colors 1 /BitsPerComponent 8 >>').encode()
    return image_pdf(zlib.compress(rows[number]),3,2,'FlateDecode',bits=8,color='DeviceGray',params=params),truth


def nested_forms(key):
    words=[key+'HEADER',key+'OUTER',key+'INNER']
    font=b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>'
    def text(value,y):return ('BT /F1 12 Tf 10 '+str(y)+' Td ('+value+') Tj ET\n').encode()
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Count 1 /Kids [3 0 R] >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 150] /Resources << /Font << /F1 5 0 R >> /XObject << /Outer 6 0 R >> >> /Contents 4 0 R >>',
        stream(b'/Filter /FlateDecode',zlib.compress(text(words[0],125)+b'q /Outer Do Q')),font,
        stream(b'/Type /XObject /Subtype /Form /BBox [0 0 300 150] /Resources << /Font << /F1 5 0 R >> /XObject << /Inner 7 0 R >> >> /Filter /FlateDecode',zlib.compress(text(words[1],95)+b'q /Inner Do Q')),
        stream(b'/Type /XObject /Subtype /Form /BBox [0 0 300 150] /Resources << /Font << /F1 5 0 R >> >> /Filter /FlateDecode',zlib.compress(text(words[2],65)))]
    return pdf_objects(objects),words


def compressed_font_object(key):
    """PDF1.5 /W[1 4 2] xref points font5 to slot0 of ObjStm6."""
    text=(f'BT /F1 12 Tf 10 80 Td ({key}) Tj ET').encode()
    objects={1:b'<< /Type /Catalog /Pages 2 0 R >>',2:b'<< /Type /Pages /Count 1 /Kids [3 0 R] >>',
        3:b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 120] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
        4:stream(b'/Filter /FlateDecode',zlib.compress(text))}
    font=b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>'
    header=b'5 0 ';objects[6]=stream(b'/Type /ObjStm /N 1 /First 4 /Filter /FlateDecode',zlib.compress(header+font))
    raw=bytearray(b'%PDF-1.7\n');offsets={}
    for number,value in objects.items():
        offsets[number]=len(raw);raw.extend(str(number).encode()+b' 0 obj\n'+value+b'\nendobj\n')
    offsets[7]=len(raw)
    entries=b'\0'+struct.pack('>IH',0,65535)
    for number in range(1,8):
        entries+=(b'\2'+struct.pack('>IH',6,0)) if number==5 else (b'\1'+struct.pack('>IH',offsets[number],0))
    xref=stream(b'/Type /XRef /Size 8 /Root 1 0 R /W [1 4 2] /Index [0 8] /Filter /FlateDecode',zlib.compress(entries))
    raw.extend(b'7 0 obj\n'+xref+b'\nendobj\nstartxref\n'+str(offsets[7]).encode()+b'\n%%EOF\n')
    return bytes(raw),[key]


def filtered_text(key,kind):
    payload=(f'BT /F1 12 Tf 10 80 Td ({key}) Tj ET').encode()
    assert len(payload)<250
    def literal_lzw(value):
        codes=[256,*value,257]
        bits=''.join(format(code,'09b') for code in codes)
        bits+='0'*((-len(bits))%8)
        return int(bits,2).to_bytes(len(bits)//8,'big')
    def runlength(value):
        return b''.join(bytes([len(value[i:i+128])-1])+value[i:i+128] for i in range(0,len(value),128))+b'\x80'
    encoders={'ASCIIHexDecode':lambda value:value.hex().encode()+b'>',
              'ASCII85Decode':lambda value:base64.a85encode(value)+b'~>',
              'RunLengthDecode':runlength,'LZWDecode':literal_lzw,'FlateDecode':zlib.compress}
    if kind=='ASCII85-LZW':
        encoded=encoders['ASCII85Decode'](literal_lzw(payload));filters=b'[/ASCII85Decode /LZWDecode]'
    elif kind=='ASCIIHex-Flate':
        encoded=encoders['ASCIIHexDecode'](zlib.compress(payload));filters=b'[/ASCIIHexDecode /FlateDecode]'
    else:encoded=encoders[kind](payload);filters=b'/'+kind.encode()
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Count 1 /Kids [3 0 R] >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 120] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
        stream(b'/Filter '+filters,encoded),b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>']
    return pdf_objects(objects),[key]
