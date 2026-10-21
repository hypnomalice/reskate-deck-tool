import math
from PIL import Image, ImageOps


def frame(path, fit='Stretch', background='#ffffff', placement=None, *, alpha=False, depth=False, size=(512,2048),
          region=None, bleed=False):
    """Place artwork on the board canvas.

    region (left, top, right, bottom fractions) fits and positions the artwork in
    part of the canvas, such as a custom deck outline's bounding box, instead of
    the whole canvas. bleed then repeats the region's edge pixels to the border.
    """
    if region is not None:
        import deck_shape
        x0, y0, x1, y1 = deck_shape.region_pixels(region, size)
        inner = frame(path, fit, background, placement, alpha=alpha, depth=depth, size=(x1-x0, y1-y0))
        if bleed:
            canvas = Image.new(inner.mode, size)
            canvas.paste(inner, (x0, y0))
            return deck_shape.bleed(canvas, region)
        fill = 128 if depth else (0, 0, 0, 0) if alpha else background
        canvas = Image.new(inner.mode, size, fill)
        canvas.paste(inner, (x0, y0))
        return canvas
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
    zoom, x, y = [float(settings.get(key, default)) for key, default in [('zoom', 1), ('x', 0), ('y', 0)]]
    if not all(math.isfinite(v) for v in (zoom, x, y)) or not .1 <= zoom <= 5 or abs(x) > 1 or abs(y) > 1:
        raise ValueError('Image placement must use 10–500% zoom and positions between -100% and 100%.')
    if (zoom, x, y) != (1, 0, 0):
        width,height = original.size
        if fit=='Stretch':
            scale_x,scale_y = target_w/width*zoom,target_h/height*zoom
        else:
            scale = (max if fit=='Crop to fill' else min)(target_w/width,target_h/height)*zoom
            scale_x = scale_y = scale
        # Pan the original, not the cropped preview, or zooming out loses the edges.
        offset_x = (width-target_w/scale_x)/2-x*target_w/scale_x
        offset_y = (height-target_h/scale_y)/2-y*target_h/scale_y
        image = original.transform(size, Image.Transform.AFFINE, (1/scale_x, 0, offset_x, 0, 1/scale_y, offset_y),
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
