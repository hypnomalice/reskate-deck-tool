"""Continuous depth atlas and preview shared by depth and Ghost Rare modes."""
import numpy as np
from PIL import Image, ImageDraw
import layer_atlas


def pack(image, depth, strength=.075, convergence=.5, ghost=False):
    from creator_engine import atlas
    values=np.asarray(depth.convert('L'),dtype=np.float32)/255
    encoded=np.rint(np.where(values<=.0031308,values*12.92,1.055*values**(1/2.4)-.055)*255).astype('uint8')
    mask=np.stack((np.full_like(encoded,255),encoded,np.full_like(encoded,255)),axis=-1)
    result=atlas(image,Image.fromarray(mask),background='#000000')
    draw=ImageDraw.Draw(result)
    draw.rectangle((0,48,127,63),fill=(128 if ghost else 64,0,255))
    draw.rectangle((128,48,255,63),fill=(layer_atlas.encode_linear(strength),layer_atlas.encode_linear(convergence),0))
    return result


def render(renderer, angle, u, v):
    sample=renderer.sample
    movement=-angle*renderer.motion[0]
    source=np.broadcast_to(u,np.broadcast_shapes(u.shape,v.shape)).copy()
    for _ in range(7):
        height=sample(source,.5+v*.5)[...,1]
        target=u+(height-renderer.motion[1])*movement
        source=(source+target)*.5
    rgb=sample(source,64/4096+v*1984/4096)
    if renderer.mode!='ghost':return rgb
    luma=rgb@np.array([.2126,.7152,.0722],dtype=np.float32)
    silver=.48+.65*(luma-.5)
    dx=sample(source+.004,.5+v*.5)[...,1]-sample(source-.004,.5+v*.5)[...,1]
    dy=sample(source,.5+v*.5+.001)[...,1]-sample(source,.5+v*.5-.001)[...,1]
    orientation=12*dx+8*dy+angle*2.4
    coverage=np.clip(1-np.abs(orientation)*.65,0,1)**2
    phase=(orientation+height*3)*2.4
    colour=np.sin(phase[...,None]+np.arange(3)*2.0943951)*.1
    return silver[...,None]+coverage[...,None]*(.1+colour)
