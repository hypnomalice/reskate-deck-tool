import math
from PIL import Image, ImageOps


def frame(path, fit='Stretch', background='#ffffff', placement=None, *, alpha=False, depth=False, size=(512,2048)):
    if isinstance(path,Image.Image):
        image = ImageOps.exif_transpose(path).convert('L' if depth else 'RGBA')
    else:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert('L' if depth else 'RGBA')
    original = image
    target_w,target_h = size
    fill = 128 if depth else (0, 0, 0, 0) if alpha else background
    sampling = Image.Resampling.BILINEAR if depth else Image.Resampling.LANCZOS
    settings = placement or {}
    zoom, x, y, rotation = [float(settings.get(key, default)) for key, default in [('zoom', 1), ('x', 0), ('y', 0), ('rotation',0)]]
    if not all(math.isfinite(v) for v in (zoom, x, y, rotation)) or not .01 <= zoom <= 20 or abs(x) > 5 or abs(y) > 5 or abs(rotation)>360:
        raise ValueError('Placement supports 1–2000% size, ±500% position and ±360° rotation.')
    if (zoom, x, y, rotation) != (1, 0, 0, 0):
        width,height = original.size
        if fit=='Stretch':
            scale_x,scale_y = target_w/width*zoom,target_h/height*zoom
        else:
            scale = (max if fit=='Crop to fill' else min)(target_w/width,target_h/height)*zoom
            scale_x = scale_y = scale
        # Pan the original, not the cropped preview, or zooming out loses the edges.
        # Inverse-map directly into the output; even extreme zoom never allocates
        # a giant intermediate image. Positive rotation is clockwise in board space.
        angle=math.radians(rotation);c,s=math.cos(angle),math.sin(angle)
        cx,cy=target_w*(.5+x),target_h*(.5+y)
        affine=(c/scale_x,s/scale_x,width/2-(c*cx+s*cy)/scale_x,
                -s/scale_y,c/scale_y,height/2+(s*cx-c*cy)/scale_y)
        image = original.transform(size, Image.Transform.AFFINE, affine,
                                Image.Resampling.BILINEAR if depth else Image.Resampling.BICUBIC, fillcolor=fill)
    elif fit == 'Crop to fill':
        image = ImageOps.fit(image, size, sampling)
    elif fit == 'Fit entire image':
        image = ImageOps.pad(image, size, sampling, color=fill)
    else:
        image = image.resize(size, sampling)
    if depth or alpha:
        return image
    canvas = Image.new('RGBA', size, background)
    canvas.alpha_composite(image)
    return canvas.convert('RGB')
