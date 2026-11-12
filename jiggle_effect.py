"""Mask, anchor and depth protocol shared by authoring and SDEC jiggle shaders."""
import math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
import layer_atlas

MATERIAL_KEY=5989339533134839651
MARKER=(.31,.83,.47)


def settings(value=None):
    c=value or {};out=dict(mask=c.get('mask'),amount=float(c.get('amount',65)),stiffness=float(c.get('stiffness',50)),
        depth_strength=float(c.get('depth_strength',.12)),reverse=bool(c.get('reverse',True)),
        attachment=c.get('attachment','top'),top_pin=c.get('top_pin'),bottom_pin=c.get('bottom_pin'),
        pin_radius=float(c.get('pin_radius',28)))
    for k,lo,hi in [('amount',0,100),('stiffness',0,100),('depth_strength',0,.3),('pin_radius',8,128)]:
        if not math.isfinite(out[k]) or not lo<=out[k]<=hi:raise ValueError(f'Invalid jiggle {k.replace("_"," ")}.')
    if out['attachment'] not in ('top','both'):raise ValueError('Choose top or top and bottom attachment.')
    for k in ('top_pin','bottom_pin'):
        if out[k] is not None:
            p=out[k]
            if len(p)!=2 or not all(math.isfinite(float(v)) and 0<=float(v)<=1 for v in p):raise ValueError('Attachment points must be on the artwork.')
            out[k]=[float(v) for v in p]
    return out


def mask_image(config,fit='Stretch',placement=None):
    import image_placement
    c=settings(config)
    if not c['mask']:raise ValueError('Choose a jiggle mask: white moves, black stays fixed.')
    im=image_placement.frame(c['mask'],fit,'#000000',placement or {},depth=True).convert('L')
    if not np.any(np.asarray(im)>0):raise ValueError('The jiggle mask has no moving area.')
    return im


def resolved_pins(c,mask):
    y,x=np.where(np.asarray(mask)>127)
    if not len(x):raise ValueError('The jiggle mask needs a white selection.')
    top=c['top_pin'] or [float(x.mean())/512,float(y.min())/2048]
    bottom=c['bottom_pin'] or [float(x.mean())/512,float(y.max())/2048]
    if top[1]>=bottom[1]:raise ValueError('The top attachment must be above the bottom attachment.')
    return top,bottom,float(x.mean())/512


def pack(image,depth,config,*,mask=None):
    from creator_engine import atlas
    c=settings(config);mask=mask or mask_image(c)
    depth=depth.convert('L').resize((512,2048),Image.Resampling.LANCZOS) if depth is not None else Image.new('L',(512,2048))
    # Feather inward: zero mask pixels never gain movement.
    original=np.asarray(mask,dtype=float)/255
    moving=np.asarray(mask.filter(ImageFilter.GaussianBlur(3)),dtype=float)/255*(original>0)
    def encoded(a):return np.uint8(np.rint(np.clip(np.where(a<=.0031308,a*12.92,1.055*a**(1/2.4)-.055),0,1)*255))
    data=np.stack((encoded(moving),encoded(np.asarray(depth)/255.),np.full_like(np.asarray(depth),255)),axis=-1)
    out=atlas(image,Image.fromarray(data),background='#000000');draw=ImageDraw.Draw(out)
    top,bottom,split=resolved_pins(c,mask)
    def row(box,values):draw.rectangle(box,fill=tuple(layer_atlas.encode_linear(v) for v in values))
    row((0,32,127,39),(*top,c['pin_radius']/512))
    row((128,32,255,39),(*bottom,split))
    draw.rectangle((0,48,127,63),fill=(64,0,255))
    row((128,48,255,63),(c['depth_strength'],0,1 if c['reverse'] else 0))
    row((256,32,383,39),MARKER)
    return out


def smooth(t):
    t=np.clip(t,0,1);return t*t*(3-2*t)


def warp(renderer,u,v,particles,attachment):
    """The same eight relaxed inverse steps as the pixel shader, in source pixels."""
    top=renderer.sample(.125,36/4096);bottom=renderer.sample(.375,36/4096)
    tx,ty=np.broadcast_arrays(np.asarray(u)*512,np.asarray(v)*2048);x=tx.copy();y=ty.copy()
    masses=np.asarray(particles)[:,:2]*32
    radius=max(float(top[2])*512,1)
    for _ in range(8):
        mask=renderer.sample_channel(x/512,.5+y/4096,0)
        a=smooth(np.hypot(x-top[0]*512,y-top[1]*2048)/radius)
        a*=smooth((y-top[1]*2048)/70)
        if attachment=='both':
            a*=smooth(np.hypot(x-bottom[0]*512,y-bottom[1]*2048)/radius)
            a*=smooth((bottom[1]*2048-y)/60)
        mask*=a;blend=smooth((x-(bottom[2]*512-20))/40)
        dx=mask*(masses[0,0]+blend*(masses[1,0]-masses[0,0]))
        dy=mask*(masses[0,1]+blend*(masses[1,1]-masses[0,1]))
        x+=(tx-(x+dx))*.7;y+=(ty-(y+dy))*.7
    return x/512,y/2048


def render(renderer,angle,u,v,view_pose=None):
    from effect_preview import display
    particles=getattr(renderer,'jiggle_particles',np.zeros((2,4)))
    # Native TEXCOORD16 is camera-to-surface projected into the board basis.
    yaw,pitch=view_pose if view_pose is not None else (math.degrees(math.asin(np.clip(angle,-1,1))),0)
    driver=-math.sin(math.radians(yaw))*math.cos(math.radians(pitch))
    movement=driver*float(renderer.motion[0])*(1 if renderer.motion[2]>.5 else -1)
    from jiggle_preview import render as fast_render
    fast=fast_render(renderer,u,v,particles,getattr(renderer,'jiggle_attachment','top'),movement)
    if fast is not None:return fast
    u,v=warp(renderer,u,v,particles,getattr(renderer,'jiggle_attachment','top'))
    source=np.array(u,copy=True)
    for _ in range(6):
        height=renderer.sample_channel(source,.5+v*.5,1)
        source=(source+u+height*movement)*.5
    return display(renderer.sample(source,64/4096+v*1984/4096))
