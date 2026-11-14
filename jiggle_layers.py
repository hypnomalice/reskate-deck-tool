"""Optional rigid foreground and clean background, in source artwork space."""
import math
import numpy as np
from PIL import Image

FIELDS=('foreground_mask','foreground_image','foreground_depth','moving_image','cutout_mask','background_image','background_depth')

def enabled(config):return any((config or {}).get(k) for k in FIELDS)

def images(config,fit='Stretch',placement=None,background='#ffffff'):
    import image_placement
    c=dict(config or {})
    if c.get('background_image') and not c.get('cutout_mask'):
        c['cutout_mask']=c.get('mask')
        if not c['cutout_mask']:raise ValueError('Choose a jiggle mask to use with the clean background.')
    if c.get('cutout_mask') and not c.get('background_image'):
        raise ValueError('A moving cutout needs a clean background image; choose both to reveal artwork underneath.')
    if c.get('moving_image') and not c.get('cutout_mask'):raise ValueError('A clean moving image needs a cutout mask and background image.')
    if c.get('foreground_image') and not c.get('foreground_mask'):raise ValueError('Choose a foreground mask before its image.')
    if c.get('foreground_depth') and not c.get('foreground_mask'):
        raise ValueError('Choose a fixed foreground mask before its depth map.')
    if c.get('background_depth') and not c.get('background_image'):
        raise ValueError('Choose a background image before its depth map.')
    out={}
    for k in FIELDS:
        if c.get(k):
            is_mask=k in ('foreground_mask','cutout_mask')
            value=image_placement.frame(c[k],fit,background if k=='background_image' else '#000000',placement or {},depth=k.endswith('_depth'),alpha=is_mask or k in ('foreground_image','moving_image'))
            if is_mask:value=Image.fromarray(np.uint8(np.rint(np.asarray(value.convert('L'),dtype=float)*np.asarray(value.getchannel('A'),dtype=float)/255)))
            out[k]=value
    return out

def pack(base,art,depth,config,prepared=None):
    from creator_engine import atlas
    from layer_atlas import encode_linear
    c=config or {};layers=images(c) if prepared is None else prepared
    black=Image.new('L',(512,2048));white=Image.new('L',(512,2048),255)
    foreground_depth=layers.get('foreground_depth',depth)
    base=base.convert('RGB')
    if 'moving_image' in layers:base.paste(layers['moving_image'].convert('RGB').resize((512,1984),Image.Resampling.LANCZOS),(0,64))
    data=np.array(base.crop((0,2048,512,4096)))
    lut=[encode_linear(i/255) for i in range(256)]
    if 'cutout_mask' in layers:
        # Give the inverse warp support across the cutout's maximum spring travel.
        field=data[:,:,0]
        for axis in (1,0):
            padding=[(0,0),(0,0)];padding[axis]=(32,32)
            field=np.lib.stride_tricks.sliding_window_view(np.pad(field,padding),65,axis=axis).max(axis=-1)
        data[:,:,0]=field
    data[:,:,2]=np.asarray(foreground_depth.convert('L').point(lut));base.paste(Image.fromarray(data),(0,2048))
    mask=layers.get('cutout_mask',white).convert('L')
    foreground=layers.get('foreground_mask',black).convert('L')
    if 'moving_image' in layers:
        mask=Image.fromarray(np.uint8(np.rint(np.asarray(mask,dtype=float)*np.asarray(layers['moving_image'].getchannel('A'),dtype=float)/255)))
    if 'foreground_image' in layers:
        foreground=Image.fromarray(np.uint8(np.rint(np.asarray(foreground,dtype=float)*np.asarray(layers['foreground_image'].getchannel('A'),dtype=float)/255)))
    bgdepth=layers.get('background_depth',black).convert('L')
    planes=Image.merge('RGB',tuple(p.point(lut) for p in (bgdepth,mask,foreground)))
    other=atlas(layers.get('background_image',art),planes,background='#000000')
    from PIL import ImageDraw
    ImageDraw.Draw(other).rectangle((0,32,127,39),fill=(255 if 'moving_image' in layers else 0,0,0))
    front=atlas(layers.get('foreground_image',art),Image.new('RGB',(512,2048)),background='#000000')
    out=Image.new('RGB',(2048,4096));out.paste(base,(0,0));out.paste(other,(512,0));out.paste(front,(1024,0))
    return out

def sample(p,page,u,v,channel=None):
    import copy
    view=copy.copy(p);view.pixels=p.layer_pixels[page]
    return view.sample(u,v) if channel is None else view.sample_channel(u,v,channel)

def render(p,u,v,particles,attachment,movement):
    """Inverse the combined depth and spring transform before sampling cutout/colour."""
    from effect_preview import display
    from jiggle_effect import smooth
    top=p.sample(.125,36/4096);bottom=p.sample(.375,36/4096)
    tx,ty=np.broadcast_arrays(np.asarray(u,dtype=float)*512,np.asarray(v,dtype=float)*2048)
    x=tx.copy();y=ty.copy();masses=np.asarray(particles)[:,:2]*32
    radius=max(float(top[2])*512,1)
    ax=(bottom[0]-top[0])*512;ay=(bottom[1]-top[1])*2048
    length=max(float(np.hypot(ax,ay)),1);ax/=length;ay/=length
    centre_y=(top[1]+bottom[1])*1024
    for _ in range(8):
        mask=p.sample_channel(x/512,.5+y/4096,0)
        a=smooth(np.hypot(x-top[0]*512,y-top[1]*2048)/radius)*smooth(((x-top[0]*512)*ax+(y-top[1]*2048)*ay)/70)
        if attachment=='both':a*=smooth(np.hypot(x-bottom[0]*512,y-bottom[1]*2048)/radius)*smooth(((bottom[0]*512-x)*ax+(bottom[1]*2048-y)*ay)/60)
        blend=smooth(((x-bottom[2]*512)*ay-(y-centre_y)*ax+20)/40);mask*=a
        dx=mask*(masses[0,0]+blend*(masses[1,0]-masses[0,0]))
        dy=mask*(masses[0,1]+blend*(masses[1,1]-masses[0,1]))
        height=p.sample_channel(x/512,.5+y/4096,1)
        x+=(tx-(x+dx-height*movement*512))*.7;y+=(ty-(y+dy))*.7
    mu,mv=x/512,y/2048
    def fixed(page,channel):
        q=np.array(u,dtype=float,copy=True)
        for _ in range(6):q=(q+u+sample(p,page,q,.5+v*.5,channel)*movement)*.5
        return q
    bu=fixed(1,0);fu=fixed(0,2)
    def colour(page,cu,cv):return sample(p,page,np.clip(cu,.5/512,1-.5/512),64/4096+np.clip(cv,.5/2048,1-.5/2048)*1984/4096)
    moving=colour(0,mu,mv);bg=colour(1,bu,v);fg=colour(2,fu,v)
    alpha=sample(p,1,mu,.5+mv*.5,1)*((mu>=0)&(mu<=1)&(mv>=0)&(mv<=1))
    if sample(p,1,.125,36/4096,0)<.5:alpha*=1-sample(p,1,mu,.5+mv*.5,2)
    front=sample(p,1,fu,.5+v*.5,2)*((fu>=0)&(fu<=1))
    result=bg+(moving-bg)*alpha[...,None]
    view=getattr(p,'jiggle_layer_view','Combined')
    if view=='Foreground':result=fg*front[...,None]
    elif view=='Moving artwork':result=moving*alpha[...,None]
    elif view=='Background':result=bg
    else:result=result+(fg-result)*front[...,None]
    if getattr(p,'jiggle_mask_overlay',False):
        mask=front if view=='Foreground' else sample(p,1,mu,.5+mv*.5,1) if view=='Moving artwork' else p.sample_channel(mu,.5+mv*.5,0)
        tint=np.array([.03,.7,.65]);result=result*(1-mask[...,None]*.35)+tint*mask[...,None]*.35
    return display(result)
