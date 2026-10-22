import numpy as np
from PIL import Image, ImageOps

import image_placement
from effect_preview import linear, display
from layer_atlas import encode_linear


def render(sources, deck, angle, size=(180,720)):
    mode = deck['mode']
    settings = deck.get('depth',{})
    images = [image_placement.frame(source,
              deck['background_fit'] if mode=='layers' and index==1 else deck['fit'],
              deck['background'],deck.get('middle_placement',{}) if index==2 else deck['placement'][index],size=size,
              alpha=(mode in ('layers','window','liquid') and index in (0,2)) or (mode=='neon' and index==1),depth=mode in ('depth','ink') and index==1)
              for index,source in enumerate(sources)]
    if mode=='neon' or (mode=='classic' and deck.get('extra_images')):
        from effect_preview import AtlasPreview
        import advanced_atlas
        if mode=='neon':
            atlas=advanced_atlas.neon_pack(images[0],images[1] if len(images)>1 else None,deck.get('neon'))
            return AtlasPreview(atlas,'neon').render(angle,size)
        extra=[image_placement.frame(path,deck['fit'],deck['background'],{},size=size) for path in deck['extra_images']]
        return AtlasPreview(advanced_atlas.multi_pack([*images,*extra]),'multi').render(angle,size)
    if mode=='liquid':
        from effect_preview import AtlasPreview
        import liquid_atlas
        return AtlasPreview(liquid_atlas.pack(images[0],images[1],deck.get('liquid')),'liquid').render(angle,size)
    if mode in ('metal','ink','window'):
        from effect_preview import AtlasPreview
        import finish_atlas
        atlas=finish_atlas.pack(mode,images[0],images[1] if len(images)>1 else None,images[2] if len(images)>2 else None)
        return AtlasPreview(atlas,mode).render(angle,size)
    width,height = size
    x = np.broadcast_to(np.arange(width,dtype=np.float32),(height,width))
    rows = np.arange(height)[:,None]
    u = (np.arange(width,dtype=np.float32)[None,:]+.5)/width
    phase = np.mod(u*112,1)-.5

    def sample(plane,coords):
        coords = np.clip(coords,0,width-1)
        first = coords.astype(np.int32)
        mix = (coords-first).astype(np.float32)
        if plane.ndim==3:
            mix = mix[...,None]
        return plane[rows,first]*(1-mix)+plane[rows,np.minimum(first+1,width-1)]*mix

    if mode=='classic':
        t = np.clip((angle*.22-phase*.2)*12.5+.5,0,1)
        weight = (.02+.96*t*t*(3-2*t))[...,None]
        a,b = (linear(image.convert('RGB')) for image in images)
        return display(b+(a-b)*weight)

    lens=settings.get('bands',1)
    if mode=='layers' and len(images)==3 and not deck.get('lenticular',True):lens=0
    bands = float(linear(round(lens*255)))
    position = np.clip((angle+1)*3.5-phase*.4*bands,0,7)
    strength = settings.get('strength',.04)
    convergence = settings.get('convergence',.5)
    if mode=='layers':
        if len(images)==3:
            # Evaluate the same three premultiplied planes without rebuilding an atlas.
            strength=float(linear(encode_linear(strength)))
            motion=(position/3.5-1)*(-1 if settings.get('invert') else 1)*strength
            combined=None
            for source,depth in zip((images[1],images[2],images[0]),reversed(deck.get('layer_depths',(.1,.45,.9)))):
                depth=float(linear(encode_linear(depth)))
                coords=x+motion*(depth-.5)*width
                rgba=np.asarray(source.convert('RGBA'));alpha=rgba[...,3:4].astype(np.float32)/255
                if combined is None:combined=sample(linear(rgba[...,:3]),coords)
                else:
                    inside=((coords>=-.5)&(coords<=width-.5))[...,None]
                    coverage=sample(alpha,coords)*inside
                    combined=sample(linear(rgba[...,:3])*alpha,coords)*inside+combined*(1-coverage)
            return display(combined)
        strength,convergence = (float(linear(encode_linear(v))) for v in (strength,convergence))
        motion = (position/3.5-1)*(-1 if settings.get('invert') else 1)*strength
        front_x = x-motion*(1-convergence)*width
        back_x = x+motion*convergence*width
        rgba = np.asarray(images[0].convert('RGBA'))
        alpha = rgba[...,3:4].astype(np.float32)/255
        front = linear(rgba[...,:3])*alpha
        inside = ((front_x>=-.5)&(front_x<=width-.5))[...,None]
        foreground = sample(front,front_x)*inside
        coverage = sample(alpha,front_x)*inside
        background = sample(linear(images[1].convert('RGB')),back_x)
        return display(foreground+background*(1-coverage))

    depth = images[1].convert('L')
    if settings.get('invert'):
        depth = ImageOps.invert(depth)
    z = np.asarray(depth,dtype=np.float32)/255
    rgb = np.asarray(images[0].convert('RGB'),dtype=np.float32)
    first = np.floor(position)
    samples = []
    # Only the two visible depth views are needed while positioning the artwork.
    for index in (first,np.minimum(first+1,7)):
        scale = (index*2/7-1)*strength*width
        source = x.copy()
        for _ in range(3):
            source = x-scale*(sample(z,source)-convergence)
        pixels = np.clip(np.rint(sample(rgb,source)),0,255).astype(np.uint8)
        samples.append(linear(pixels))
    return display(samples[0]+(samples[1]-samples[0])*(position-first)[...,None])
