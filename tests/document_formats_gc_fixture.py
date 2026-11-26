"""Independent legal PDF material for physical candidate-capacity checks."""
from io import BytesIO
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


def image_with_unreferenced_stream(key,total):
    def build(length):
        content=b'q\n640 0 0 160 0 0 cm\n/I Do\nQ\n'
        image=b'\x00\x00\x00'
        payload=(key.encode('ascii')+b'\n'+b'x'*length)
        objects=[b'<< /Type /Catalog /Pages 2 0 R >>',
                 b'<< /Type /Pages /Count 1 /Kids [3 0 R] >>',
                 b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 640 160] /Resources << /XObject << /I 5 0 R >> >> /Contents 4 0 R >>',
                 b'<< /Length '+str(len(content)).encode()+b' >>\nstream\n'+content+b'endstream',
                 b'<< /Type /XObject /Subtype /Image /Width 1 /Height 1 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Length 3 >>\nstream\n'+image+b'\nendstream',
                 b'<< /Length '+str(len(payload)).encode()+b' >>\nstream\n'+payload+b'\nendstream']
        raw=b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n';offsets=[]
        for index,obj in enumerate(objects,1):
            offsets.append(len(raw));raw+=str(index).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
        xref=len(raw);raw+=b'xref\n0 7\n0000000000 65535 f \n'+b''.join(('%010d 00000 n \n'%offset).encode() for offset in offsets)
        return raw+b'trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n'+str(xref).encode()+b'\n%%EOF\n'
    padding=total-len(build(0))
    for _ in range(6):
        raw=build(padding)
        if len(raw)==total:return raw
        padding+=total-len(raw)
    raise AssertionError('length convergence failed')


def partial_without_ocr(key):
    """Known native first page plus image-only second page, no OCR configured."""
    output=BytesIO();pdf=canvas.Canvas(output,pagesize=(300,200),invariant=1)
    anchor=key+' PartialSnapshot'
    pdf.setFont('Helvetica',10);pdf.drawString(20,100,anchor);pdf.showPage()
    pdf.drawImage(ImageReader(Image.new('RGB',(1,1),'black')),0,0,width=300,height=200)
    pdf.showPage();pdf.save()
    return output.getvalue(),{'words':[anchor],'excluded':[],'tables':[]}
