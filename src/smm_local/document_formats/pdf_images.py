"""Worker-only raster admission; dimensions and decoded budget precede load."""
from __future__ import annotations
from io import BytesIO
import math,struct,warnings

PIXELS=16000000


def name(value):return getattr(value,'name',value)


def dimensions(attrs,resolve):
    width=resolve(attrs.get('Width'));height=resolve(attrs.get('Height'))
    if type(width) is not int or type(height) is not int or width<1 or height<1 or width*height>PIXELS:raise ValueError('PDF待解码图像超过1600万像素或尺寸无效')
    return width,height


def components(space,resolve):
    space=resolve(space);kind=name(space)
    if isinstance(space,list):
        if not space:raise ValueError('PDF图像颜色空间为空')
        kind=name(resolve(space[0]))
        if kind=='ICCBased':
            profile=resolve(space[1]);count=resolve(profile.attrs.get('N'))
            if type(count) is not int or not 1<=count<=32:raise ValueError('PDF ICC通道数无效')
            return count
        if kind=='DeviceN':
            channels=resolve(space[1])
            if not isinstance(channels,list) or not 1<=len(channels)<=32:raise ValueError('PDF DeviceN通道数无效')
            return len(channels)
    counts={'DeviceGray':1,'CalGray':1,'DeviceRGB':3,'CalRGB':3,'Lab':3,'DeviceCMYK':4,'Indexed':1,'Separation':1}
    if kind not in counts:raise ValueError('guard_unavailable: 未解析的PDF图像颜色空间 '+str(kind))
    return counts[kind]


def expected_bytes(attrs,resolve):
    width,height=dimensions(attrs,resolve);mask=resolve(attrs.get('ImageMask',False))
    if type(mask) is not bool:raise ValueError('PDF ImageMask无效')
    bits=resolve(attrs.get('BitsPerComponent',1 if mask else None))
    if type(bits) is not int or bits not in (1,2,4,8,16) or (mask and bits!=1):raise ValueError('PDF图像位深无效')
    count=1 if mask else components(attrs.get('ColorSpace'),resolve)
    return ((width*count*bits+7)//8)*height


def tiff_header(width,height,length,params):
    k=params.get('K',0)
    if type(k) is not int:raise ValueError('CCITT K无效')
    if params.get('Columns',1728)!=width or params.get('Rows',0) not in (0,height):raise ValueError('CCITT尺寸与PDF图像不一致')
    compression=4 if k<0 else 3
    entries=[(256,4,width),(257,4,height),(258,3,1),(259,3,compression),(262,3,1),(273,4,0),(278,4,height),(279,4,length)]
    if compression==3:entries.append((292,4,(1 if k>0 else 0)|(4 if params.get('EncodedByteAlign',False) else 0)))
    offset=8+2+len(entries)*12+4
    result=bytearray(b'II'+struct.pack('<HIH',42,8,len(entries)))
    for tag,kind,value in sorted(entries):
        if tag==273:value=offset
        result.extend(struct.pack('<HHI',tag,kind,1));result.extend(struct.pack('<H',value)+b'\0\0' if kind==3 else struct.pack('<I',value))
    result.extend(b'\0'*4);return bytes(result)


def raster(stream,codec,data,params,budget,resolve):
    from PIL import Image
    from pdfminer.psparser import LIT
    from pdfminer.pdftypes import PDFStream
    width,height=dimensions(stream.attrs,resolve)
    ccitt=codec in {'CCITTFaxDecode','CCF'}
    encoded=tiff_header(width,height,len(data),params)+data if ccitt else data
    previous_limit=Image.MAX_IMAGE_PIXELS;Image.MAX_IMAGE_PIXELS=PIXELS
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            image=Image.open(BytesIO(encoded))
    except (Image.DecompressionBombError,Image.DecompressionBombWarning) as exc:raise ValueError('PDF实际图像尺寸超过1600万像素') from exc
    except (OSError,ValueError) as exc:raise ValueError('PDF图像编码损坏: '+str(exc)) from exc
    finally:Image.MAX_IMAGE_PIXELS=previous_limit
    with image:
        if image.size!=(width,height):raise ValueError('PDF声明与实际图像尺寸不一致')
        mode=image.mode;alpha=mode in {'RGBA','LA'}
        if ccitt:bits,count,target=1,1,'DeviceGray'
        elif mode in {'1','L'}:bits,count,target=(1 if mode=='1' else 8),1,'DeviceGray'
        elif mode in {'RGB','RGBA'}:bits,count,target=8,(4 if alpha else 3),'DeviceRGB'
        elif mode in {'LA'}:bits,count,target=8,2,'DeviceGray'
        elif mode=='CMYK':bits,count,target=8,4,'DeviceCMYK'
        elif mode.startswith('I;16'):bits,count,target=16,1,'DeviceGray'
        elif mode=='P':bits,count,target=8,3,'DeviceRGB'
        else:raise ValueError('guard_unavailable: 不支持的PDF图像分量模式 '+mode)
        decoded=((width*count*bits+7)//8)*height
        # Reservation is charged before the image library allocates its bitmap.
        budget.charge(stream,decoded);image.load()
        if mode=='P':image=image.convert('RGB')
        attrs=dict(stream.attrs);attrs.update(ColorSpace=LIT(target),BitsPerComponent=bits)
        if alpha:
            channel=image.getchannel('A');mask=PDFStream({'Type':LIT('XObject'),'Subtype':LIT('Image'),'Width':width,'Height':height,'ColorSpace':LIT('DeviceGray'),'BitsPerComponent':8},b'')
            mask.data=channel.tobytes();mask.rawdata=None;attrs['SMask']=mask
            image=image.convert('L' if mode=='LA' else 'RGB')
        raw=image.tobytes('raw','I;16B') if bits==16 else image.tobytes()
        if ccitt and params.get('BlackIs1',False):raw=bytes(value^255 for value in raw)
        if len(raw)!=((width*(count-1 if alpha else count)*bits+7)//8)*height:raise ValueError('PDF图像实际解码长度不符')
        # A PDF Decode array still applies to the same raw components; retain it.
        return raw,attrs
