"""Legal image PDF with exact physical length; budget limits are never patched."""
from io import BytesIO
from PIL import Image,ImageDraw,ImageFont


def image_pdf(key,total=None):
    image=Image.new('RGB',(640,160),'white');draw=ImageDraw.Draw(image)
    draw.text((20,30),'STAGING '+key,fill='black',font=ImageFont.load_default(size=30))
    jpeg=BytesIO();image.save(jpeg,format='JPEG',quality=90);body=jpeg.getvalue()
    def assemble(padding):
        stream=b'q\n640 0 0 160 0 0 cm\n/I Do\nQ\n%'+b'x'*padding+b'\n'
        objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Count 1 /Kids [3 0 R] >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 640 160] /Resources << /XObject << /I 5 0 R >> >> /Contents 4 0 R >>',
            b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'endstream',
            b'<< /Type /XObject /Subtype /Image /Width 640 /Height 160 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length '+str(len(body)).encode()+b' >>\nstream\n'+body+b'\nendstream']
        raw=b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n';offsets=[0]
        for number,obj in enumerate(objects,1):
            offsets.append(len(raw));raw+=str(number).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
        xref=len(raw);raw+=b'xref\n0 6\n0000000000 65535 f \n'
        raw+=b''.join(('%010d 00000 n \n'%offset).encode() for offset in offsets[1:])
        raw+=b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'+str(xref).encode()+b'\n%%EOF\n'
        return raw
    raw=assemble(0)
    if total is None:return raw
    padding=total-len(raw)
    if padding<0:raise ValueError('fixture total too small for its real image')
    for _ in range(5):
        raw=assemble(padding)
        if len(raw)==total:return raw
        padding+=total-len(raw)
    raise AssertionError('exact PDF size did not converge')
