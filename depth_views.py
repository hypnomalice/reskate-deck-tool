from PIL import Image, ImageOps, ImageDraw
import math

VIEW_COUNT = 8
TILE_HEIGHT = 504

def layer_image(path, fit='Stretch', size=(512,2048)):
    with Image.open(path) as source:
        im=ImageOps.exif_transpose(source).convert('RGBA')
        if fit=='Crop to fill':return ImageOps.fit(im,size,Image.Resampling.LANCZOS)
        if fit=='Fit entire image':return ImageOps.pad(im,size,Image.Resampling.LANCZOS,color=(0,0,0,0))
        return im.resize(size,Image.Resampling.LANCZOS)

def _unit_interval(value, label):
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f'{label} must be between 0 and 1.')
    return value


def _extend_background(image, margin):
    width, height = image.size
    padded = Image.new('RGBA', (width + margin * 2, height))
    padded.paste(image, (margin, 0))
    left = image.crop((0, 0, 1, height)).resize((margin, height))
    right = image.crop((width - 1, 0, width, height)).resize((margin, height))
    padded.paste(left, (0, 0))
    padded.paste(right, (margin + width, 0))
    return padded


def layer_views(foreground, background, strength=.08, convergence=.5,
                reverse=False, progress=lambda message: None, *, view_count=VIEW_COUNT):
    strength = _unit_interval(strength, 'Depth strength')
    convergence = _unit_interval(convergence, 'Background motion')
    if not isinstance(view_count, int) or view_count < 2:
        raise ValueError('At least two layer views are required.')
    foreground = foreground.convert('RGBA')
    background = background.convert('RGBA')
    if foreground.size != background.size:
        raise ValueError('Foreground and background must have matching dimensions.')
    if strength == 0:
        still = Image.alpha_composite(background, foreground).convert('RGB')
        return [still.copy() for _ in range(view_count)]

    width, height = background.size
    margin = math.ceil(width * strength * convergence) + 2
    padded = _extend_background(background, margin)
    result = []
    for index in range(view_count):
        progress(f'Generating layered 3D view {index + 1} of {view_count}...')
        angle = (2 * index / (view_count - 1) - 1) * (-1 if reverse else 1)
        front_shift = angle * strength * width * (1 - convergence)
        back_shift = -angle * strength * width * convergence
        back = padded.transform(
            (width, height), Image.Transform.AFFINE,
            (1, 0, margin - back_shift, 0, 1, 0), Image.Resampling.BICUBIC)
        front = foreground.transform(
            (width, height), Image.Transform.AFFINE,
            (1, 0, -front_shift, 0, 1, 0), Image.Resampling.BICUBIC)
        result.append(Image.alpha_composite(back, front).convert('RGB'))
    return result


def layer_at_angle(foreground, background, angle, strength=.08, convergence=.5, reverse=False,
                   band_intensity=0, bands=112):
    width, height = foreground.size
    if strength==0:
        return Image.alpha_composite(background.convert('RGBA'),foreground.convert('RGBA')).convert('RGB')
    if band_intensity:
        intensity = _unit_interval(band_intensity,'Lens texture')
        intensity = intensity/12.92 if intensity<=.04045 else ((intensity+.055)/1.055)**2.4
        front = foreground.convert('RGBa')
        margin = math.ceil(width*strength*convergence)+2
        back = _extend_background(background.convert('RGBA'),margin).convert('RGBa')
        out = Image.new('RGB',(width,height))
        for x in range(width):
            phase = ((x+.5)/width*bands)%1-.5
            local = max(-1,min(1,float(angle)-phase*.4*intensity/3.5)) * (-1 if reverse else 1)
            front_shift = local*strength*width*(1-convergence)
            back_shift = -local*strength*width*convergence
            a = front.transform((1,height),Image.Transform.AFFINE,(1,0,x-front_shift,0,1,0),Image.Resampling.BICUBIC).convert('RGBA')
            b = back.transform((1,height),Image.Transform.AFFINE,(1,0,x+margin-back_shift,0,1,0),Image.Resampling.BICUBIC).convert('RGBA')
            out.paste(Image.alpha_composite(b,a).convert('RGB'),(x,0))
        return out
    angle = max(-1, min(1, float(angle))) * (-1 if reverse else 1)
    front_shift = angle * strength * width * (1-convergence)
    back_shift = -angle * strength * width * convergence
    margin = math.ceil(width*strength*convergence)+2
    padded = _extend_background(background.convert('RGBA'), margin)
    back = padded.transform((width,height), Image.Transform.AFFINE,
                            (1,0,margin-back_shift,0,1,0), Image.Resampling.BICUBIC)
    front = foreground.convert('RGBA').transform((width,height), Image.Transform.AFFINE,
                                                 (1,0,-front_shift,0,1,0), Image.Resampling.BICUBIC)
    return Image.alpha_composite(back,front).convert('RGB')


def depth_image(path, fit='Stretch', size=(512,2048), invert=False):
    with Image.open(path) as source:
        im=ImageOps.exif_transpose(source).convert('L')
        if fit=='Crop to fill':im=ImageOps.fit(im,size,Image.Resampling.BILINEAR)
        elif fit=='Fit entire image':im=ImageOps.pad(im,size,Image.Resampling.BILINEAR,color=128)
        else:im=im.resize(size,Image.Resampling.BILINEAR)
    return ImageOps.invert(im) if invert else im

def _reference_view(image, depth, angle, strength=.04, convergence=.5):
    """Forward splat with a depth buffer, then extend the farther hole boundary.

    A single photograph cannot reveal hidden surfaces. The horizontal fill is
    deliberately conservative; large shifts still expose stretched edges.
    Strength is a fraction of image width at either extreme viewing angle.
    """
    strength=float(strength);convergence=float(convergence);angle=float(angle)
    if not 0<=strength<=1 or not 0<=convergence<=1:raise ValueError('Depth strength or convergence is out of range.')
    image=image.convert('RGB');depth=depth.resize(image.size,Image.Resampling.BILINEAR).convert('L')
    if not strength or not angle:return image.copy()
    w,h=image.size;rgb=image.tobytes();ds=depth.tobytes();out=bytearray(len(rgb))
    shifts=[angle*strength*w*(d/255-convergence) for d in range(256)]
    for y in range(h):
        row=y*w;zbuf=[-1]*w;indices=[-1]*w
        for x in range(w):
            d=ds[row+x];target=round(x+shifts[d])
            # Point samples inside smooth surfaces cause whole-pixel stepping.
            if 0<x<w-1 and abs(d-ds[row+x-1])<=8 and abs(d-ds[row+x+1])<=8:continue
            if 0<=target<w and d>=zbuf[target]:zbuf[target]=d;indices[target]=x
        # Interpolate smooth surfaces, but never bridge a depth discontinuity.
        colors={}
        for x in range(w-1):
            da=ds[row+x];db=ds[row+x+1]
            if abs(da-db)>8:continue
            left=x+shifts[da];right=x+1+shifts[db]
            if right<=left:continue
            first=max(0,math.ceil(left));last=min(w-1,math.floor(right))
            a=(row+x)*3
            for target in range(first,last+1):
                t=(target-left)/(right-left);z=da+(db-da)*t
                if z+0.001<zbuf[target]:continue
                zbuf[target]=z;indices[target]=x
                colors[target]=tuple(round(rgb[a+c]*(1-t)+rgb[a+3+c]*t) for c in range(3))
        valid=[x for x in range(w) if indices[x]>=0]
        if not valid:continue
        # Fill disocclusions from the farther side, rather than smearing foreground.
        previous=valid[0]
        for x in range(previous):indices[x]=indices[previous]
        for right in valid[1:]:
            if right>previous+1:
                source=indices[previous] if zbuf[previous]<=zbuf[right] else indices[right]
                for x in range(previous+1,right):indices[x]=source
            previous=right
        for x in range(previous+1,w):indices[x]=indices[previous]
        for x,source in enumerate(indices):
            a=(row+source)*3;b=(row+x)*3
            out[b:b+3]=bytes(colors[x]) if x in colors else rgb[a:a+3]
    return Image.frombytes('RGB',(w,h),bytes(out))

def view(image, depth, angle, strength=.04, convergence=.5):
    """The same depth-buffer renderer for preview and export, accelerated when available."""
    strength,convergence,angle=map(float,(strength,convergence,angle))
    if not all(map(math.isfinite,(strength,convergence,angle))) or not 0<=strength<=1 or not 0<=convergence<=1:
        raise ValueError('Depth strength, convergence or angle is out of range.')
    image=image.convert('RGB')
    depth=depth.resize(image.size,Image.Resampling.BILINEAR).convert('L')
    if not strength or not angle:return image.copy()
    from depth_native import render
    result=render(image,depth,angle,strength,convergence)
    return result if result is not None else _reference_view(image,depth,angle,strength,convergence)


_view_cache = None


def _view_job(job):
    image, depth, angle, strength, convergence = job
    return view(image, depth, angle, strength, convergence)


def views(image, depth, strength=.04, convergence=.5, progress=lambda message:None):
    from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
    import multiprocessing
    import hashlib
    import os
    global _view_cache
    # Cached images are copied out so callers cannot change a later export.
    key = (image.size, image.mode, depth.size, depth.mode, float(strength), float(convergence),
           hashlib.sha256(image.tobytes()).digest(), hashlib.sha256(depth.tobytes()).digest())
    cached = _view_cache
    if cached is not None and key == cached[0]:
        progress('Reusing unchanged depth views...')
        return [frame.copy() for frame in cached[1]]
    jobs = [(image, depth, i*2/(VIEW_COUNT-1)-1, strength, convergence) for i in range(VIEW_COUNT)]
    result = []
    if image.width * image.height >= 512 * 1024 and strength:
        # The depth renderer is Python-heavy, unlike the native BC7 encoder.
        progress('Preparing depth views...')
        count = max(1, min(4, (os.cpu_count() or 2)-1))
        from depth_native import backend
        native=backend() is not None
        executor=ThreadPoolExecutor if native else ProcessPoolExecutor
        options={} if native else dict(mp_context=multiprocessing.get_context('spawn'))
        with executor(max_workers=count, **options) as pool:
            for i, frame in enumerate(pool.map(_view_job, jobs)):
                progress(f'Generating 3D view {i+1} of {VIEW_COUNT}...')
                result.append(frame)
    else:
        for i, job in enumerate(jobs):
            progress(f'Generating 3D view {i+1} of {VIEW_COUNT}...')
            result.append(_view_job(job))
    if sum(frame.width * frame.height * 3 for frame in result) <= 32 * 1024 * 1024:
        _view_cache = (key, [frame.copy() for frame in result])
    return result


def _paste_view_tile(atlas, image, origin, cell_size, horizontal_gutter):
    x, y = origin
    cell_width, cell_height = cell_size
    vertical_gutter = 2
    width = cell_width - 2 * horizontal_gutter
    height = cell_height - 2 * vertical_gutter
    tile = image.resize((width, height), Image.Resampling.LANCZOS)
    atlas.paste(tile, (x + horizontal_gutter, y + vertical_gutter))
    if horizontal_gutter:
        left = tile.crop((0, 0, 1, height)).resize((horizontal_gutter, height))
        right = tile.crop((width - 1, 0, width, height)).resize((horizontal_gutter, height))
        atlas.paste(left, (x, y + vertical_gutter))
        atlas.paste(right, (x + cell_width - horizontal_gutter, y + vertical_gutter))
    top = atlas.crop((x, y + vertical_gutter, x + cell_width, y + vertical_gutter + 1))
    bottom = atlas.crop((x, y + cell_height - vertical_gutter - 1,
                         x + cell_width, y + cell_height - vertical_gutter))
    atlas.paste(top.resize((cell_width, vertical_gutter)), (x, y))
    atlas.paste(bottom.resize((cell_width, vertical_gutter)),
                (x, y + cell_height - vertical_gutter))


def pack(images, band_intensity=1, balanced=False):
    """Pack eight views using the layouts understood by the shared shader.

    The top 64 pixels identify the deck and carry the mode/lens settings.
    Balanced tiles retain more vertical detail; strips remain readable for
    older exports. Changing this layout also requires changing shader UVs.
    """
    if len(images) != VIEW_COUNT:
        raise ValueError('Eight views are required.')
    atlas = Image.new('RGB', (512, 4096))
    draw = ImageDraw.Draw(atlas)
    markers = [(255, 0, 255), (0, 255, 255), (255, 255, 0), (0, 255, 0)]
    for index, color in enumerate(markers):
        draw.rectangle((index * 128, 0, index * 128 + 127, 63), fill=color)
    lens_strength = round(255 * max(0, min(1, float(band_intensity))))
    draw.rectangle((0, 48, 127, 63),
                   fill=(128 if balanced else 255, 255, lens_strength))

    columns = 2 if balanced else 1
    cell_size = (256, 1008) if balanced else (512, TILE_HEIGHT)
    gutter = 2 if balanced else 0
    for index, image in enumerate(images):
        origin = ((index % columns) * cell_size[0],
                  64 + (index // columns) * cell_size[1])
        _paste_view_tile(atlas, image, origin, cell_size, gutter)
    return atlas


def preview(images, angle, bands=112, band_intensity=1):
    w,h=images[0].size;out=Image.new('RGB',(w,h))
    for x in range(w):
        p=max(0,min(VIEW_COUNT-1,(angle+1)*.5*(VIEW_COUNT-1)-(((x+.5)/w*bands)%1-.5)*.4*band_intensity))
        a=int(p);b=min(VIEW_COUNT-1,a+1);t=p-a
        strip=Image.blend(images[a].crop((x,0,x+1,h)),images[b].crop((x,0,x+1,h)),t)
        out.paste(strip,(x,0))
    return out

def demo(folder):
    folder.mkdir(parents=True,exist_ok=True)
    image=Image.new('RGB',(512,2048),'#152944');depth=Image.new('L',image.size,35)
    d=ImageDraw.Draw(image);z=ImageDraw.Draw(depth)
    for y in range(0,2048,80):d.line((0,y,512,y),fill='#486b85',width=3)
    for x in range(0,512,64):d.line((x,0,x,2048),fill='#486b85',width=3)
    for box,color,value in [((65,300,350,850),'#29bbca',100),((175,750,460,1400),'#ffb83d',180),((70,1250,325,1800),'#e75970',245)]:
        d.rounded_rectangle(box,radius=45,fill=color);z.rounded_rectangle(box,radius=45,fill=value)
    image.save(folder/'Depth demo image.png');depth.save(folder/'Depth demo map.png')
    return folder/'Depth demo image.png',folder/'Depth demo map.png'

def depth_study(folder):
    folder.mkdir(parents=True,exist_ok=True)
    image=Image.new('RGB',(512,2048),'#102335');depth=Image.new('L',image.size,28)
    draw=ImageDraw.Draw(image);zdraw=ImageDraw.Draw(depth)
    for i in range(12):
        inset=12+i*18;top=65+i*69;bottom=1980-i*69
        box=(inset,top,512-inset,bottom)
        draw.rectangle(box,fill=(12+i,25+i,40+i));zdraw.rectangle(box,fill=75-i*5)
        draw.rectangle(box,outline=('#52c8d0' if i%2==0 else '#c69b48'),width=3)
    pixels=image.load();zs=depth.load()
    for cx,cy,rx,ry,color in [(180,580,155,255,(31,175,220)),(320,1430,150,250,(234,76,116))]:
        for y in range(cy-ry,cy+ry+1):
            ny=(y-cy)/ry
            for x in range(max(0,cx-rx),min(512,cx+rx+1)):
                nx=(x-cx)/rx;q=1-nx*nx-ny*ny
                if q<0:continue
                nz=math.sqrt(q)
                diffuse=max(0,-nx*.44-ny*.50+nz*.74)
                spec=max(0,-nx*.25-ny*.30+nz*.92)**36
                shade=.18+.78*diffuse
                pixels[x,y]=tuple(min(255,round(c*shade+spec*120)) for c in color)
                zs[x,y]=round(130+115*nz)
    image.save(folder/'Curved depth study.png');depth.save(folder/'Curved depth study map.png')
    return folder/'Curved depth study.png',folder/'Curved depth study map.png'
