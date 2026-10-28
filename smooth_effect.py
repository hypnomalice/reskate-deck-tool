"""Continuous depth atlas and preview shared by depth and Ghost Rare modes."""
import numpy as np
from PIL import Image, ImageDraw
import layer_atlas


def pack(image, depth, strength=.075, convergence=.5, ghost=False, areas=None, mask_fit="Stretch", mask_placement=None):
    from creator_engine import atlas
    values=np.asarray(depth.convert('L'),dtype=np.float32)/255
    encoded=np.rint(np.where(values<=.0031308,values*12.92,1.055*values**(1/2.4)-.055)*255).astype('uint8')
    silver=holo=np.ones_like(values)
    if ghost and areas:
        from ghost_areas import coverage
        silver=coverage(image,areas.get('silver'),mask_fit,mask_placement,label='silver')
        holo=coverage(image,areas.get('holo'),mask_fit,mask_placement,label='holo')
    def encode_area(value):
        return np.rint(np.clip(np.where(value<=.0031308,value*12.92,1.055*value**(1/2.4)-.055),0,1)*255).astype('uint8')
    mask=np.stack((encode_area(silver),encoded,encode_area(holo)),axis=-1)
    result=atlas(image,Image.fromarray(mask),background='#000000')
    draw=ImageDraw.Draw(result)
    draw.rectangle((0,48,127,63),fill=(128 if ghost else 64,0,255))
    draw.rectangle((128,48,255,63),fill=(layer_atlas.encode_linear(strength),layer_atlas.encode_linear(convergence),0))
    return result


def render(renderer, angle, u, v):
    sample=renderer.sample
    depth=renderer.sample_channel
    movement=angle*renderer.motion[0]*(1 if renderer.motion[2]>.5 else -1)
    # Match the native shader: one clamped initial displacement, then six
    # relaxed depth reads. The final pre-update depth drives the foil phase.
    initial=depth(u,.5+v*.5,1)
    source=np.clip(u+(initial-renderer.motion[1])*movement,0,1)
    for _ in range(6):
        height=depth(source,.5+v*.5,1)
        target=u+(height-renderer.motion[1])*movement
        source=(source+target)*.5
    rgb=sample(source,64/4096+v*1984/4096)
    if renderer.mode!='ghost':return rgb
    luma=rgb@np.array([.2126,.7152,.0722],dtype=np.float32)
    silver=.48+.65*(luma-.5)
    dx=depth(source+.004,.5+v*.5,1)-depth(source-.004,.5+v*.5,1)
    dy=depth(source,.5+v*.5+.001,1)-depth(source,.5+v*.5-.001,1)
    orientation=12*dx+8*dy+angle*2.4
    silver_area=depth(source,.5+v*.5,0)
    holo_area=depth(source,.5+v*.5,2)
    coverage=np.clip(1-np.abs(orientation)*.65,0,1)**2*holo_area
    phase=(orientation+height*3)*2.4
    colour=np.sin(phase[...,None]+np.arange(3)*2.0943951)*.1
    base=rgb+(silver[...,None]-rgb)*silver_area[...,None]
    return base+coverage[...,None]*(.1+colour)
