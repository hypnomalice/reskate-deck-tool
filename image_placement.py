import math
from PIL import Image, ImageOps


def frame(path, fit='Stretch', background='#ffffff', placement=None, *, alpha=False, depth=False):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert('L' if depth else 'RGBA')
    original = image
    size = (512, 2048)
    fill = 128 if depth else (0, 0, 0, 0) if alpha else background
    sampling = Image.Resampling.BILINEAR if depth else Image.Resampling.LANCZOS
    if fit == 'Crop to fill':
        image = ImageOps.fit(image, size, sampling)
    elif fit == 'Fit entire image':
        image = ImageOps.pad(image, size, sampling, color=fill)
    else:
        image = image.resize(size, sampling)
    settings = placement or {}
    zoom, x, y = [float(settings.get(key, default)) for key, default in [('zoom', 1), ('x', 0), ('y', 0)]]
    if not all(math.isfinite(v) for v in (zoom, x, y)) or not .1 <= zoom <= 5 or abs(x) > 1 or abs(y) > 1:
        raise ValueError('Image placement must use 10–500% zoom and positions between -100% and 100%.')
    if (zoom, x, y) != (1, 0, 0):
        width,height = original.size
        if fit=='Stretch':
            scale_x,scale_y = 512/width*zoom,2048/height*zoom
        else:
            scale = (max if fit=='Crop to fill' else min)(512/width,2048/height)*zoom
            scale_x = scale_y = scale
        # Pan the original, not the cropped preview, or zooming out loses the edges.
        offset_x = (width-512/scale_x)/2-x*512/scale_x
        offset_y = (height-2048/scale_y)/2-y*2048/scale_y
        image = original.transform(size, Image.Transform.AFFINE, (1/scale_x, 0, offset_x, 0, 1/scale_y, offset_y),
                                Image.Resampling.BILINEAR if depth else Image.Resampling.BICUBIC, fillcolor=fill)
    if depth or alpha:
        return image
    canvas = Image.new('RGBA', size, background)
    canvas.alpha_composite(image)
    return canvas.convert('RGB')
