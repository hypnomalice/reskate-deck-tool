"""Inspect exported BC7 pixels; game lighting and native mesh remain separate."""
import io
import struct
from PIL import Image


def decode_bc7(data, size):
    width, height = size
    if width < 1 or height < 1:
        raise ValueError('Texture dimensions must be positive.')
    length = ((width+3)//4)*((height+3)//4)*16
    if len(data) < length:
        raise ValueError('Incomplete BC7 texture.')
    # The colour atlas is sampled as sRGB in game. Pillow returns its encoded
    # pixels; AtlasPreview then performs the same sRGB-to-linear conversion.
    fields = ([124, 0x81007, height, width, length, 0, 1] + [0]*11 +
              [32, 4, int.from_bytes(b'DX10','little'), 0, 0, 0, 0, 0] +
              [0x1000, 0, 0, 0, 0])
    header = b'DDS '+struct.pack('<31I',*fields)+struct.pack('<5I',99,3,0,1,0)
    with Image.open(io.BytesIO(header+data[:length])) as image:
        return image.convert('RGB')


def prepare(project, mode, progress=lambda message: None):
    import creator_engine
    from effect_preview import AtlasPreview
    texture = creator_engine.export_texture(project, progress)
    return AtlasPreview(decode_bc7(texture['texture'], texture['texture_size']), mode)
