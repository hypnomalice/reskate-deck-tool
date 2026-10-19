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
              deck['background'],deck['placement'][index],size=size,
              alpha=mode=='layers' and index==0,depth=mode=='depth' and index==1)
              for index,source in enumerate(sources)]
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

    bands = float(linear(round(settings.get('bands',1)*255)))
    position = np.clip((angle+1)*3.5-phase*.4*bands,0,7)
    strength = settings.get('strength',.04)
    convergence = settings.get('convergence',.5)
    if mode=='layers':
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
