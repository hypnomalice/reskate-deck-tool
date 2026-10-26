"""Authoring for approved multi-image lens and native emission layouts."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageColor, ImageOps
import depth_views

SDEC_URL='https://thunderstore.io/c/reskate/p/IdolRiot/Sofis_Deck_Effect_Core/'

def encoded(value):
    return round(255*(12.92*value if value<=.0031308 else 1.055*value**(1/2.4)-.055))

def multi_pack(images):
    if not 2<=len(images)<=8:
        raise ValueError('Choose between two and eight lenticular pictures.')
    atlas=depth_views.pack([images[min(i,len(images)-1)] for i in range(8)],band_intensity=0,balanced=True)
    d=ImageDraw.Draw(atlas);d.rectangle((0,48,127,63),fill=(72,32,224))
    d.rectangle((128,48,255,63),fill=(encoded(len(images)/8),0,0))
    return atlas

def glow_image(art,mask=None,settings=None):
    cfg=settings or {};mode=cfg.get('selection','mask')
    rgb=np.asarray(art.convert('RGB'),dtype=np.float32)/255
    if mode=='colour':
        colour=np.array(ImageColor.getrgb(cfg.get('colour','#00dfff')),dtype=np.float32)/255
        tolerance=float(cfg.get('tolerance',.15))
        if not math.isfinite(tolerance) or not 0<=tolerance<=1:raise ValueError('Colour tolerance must be between 0 and 100%.')
        distance=np.sqrt(np.mean((rgb-colour)**2,axis=2))
        edge=max(.005,tolerance*.1)
        amount=np.clip((tolerance+edge-distance)/edge,0,1)
    elif mode=='mask':
        if mask is None:raise ValueError('Choose a glow mask PNG, or select Pick a colour.')
        rgba=mask.convert('RGBA').resize(art.size,Image.Resampling.LANCZOS)
        amount=np.asarray(ImageOps.grayscale(rgba),dtype=np.float32)/255*np.asarray(rgba.getchannel('A'),dtype=np.float32)/255
    else:raise ValueError('Choose a supported neon selection method.')
    linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)*amount[...,None]
    display=np.where(linear<=.0031308,linear*12.92,1.055*linear**(1/2.4)-.055)
    return Image.fromarray(np.rint(np.clip(display,0,1)*255).astype('uint8'))

def neon_pack(art,mask=None,settings=None):
    import creator_engine
    cfg=settings or {};brightness=float(cfg.get('brightness',1))
    if not math.isfinite(brightness) or not 0<=brightness<=1:raise ValueError('Neon brightness must be between 0 and 100%.')
    glow=glow_image(art,mask,cfg)
    atlas=creator_engine.atlas(art,glow)
    d=ImageDraw.Draw(atlas);d.rectangle((0,48,127,63),fill=(96,32,224))
    d.rectangle((128,48,255,63),fill=(encoded(brightness),0,0))
    return atlas

def render(preview,angle,u,v,material=False):
    from effect_preview import display
    if preview.mode=='neon':
        base=preview.sample(u,64/4096+v*1984/4096)
        glow=preview.sample(u,.5+v*.5)
        # The native pass routes emission separately, at 32 times the authored
        # gain. Keep it out of albedo and apply exposure only in the lit preview.
        emission=glow*float(preview.motion[0])*32
        image=display(base if material else base+emission*.35)
        if material:image.info['linear_emission']=emission
        return image
    count=int(round(float(preview.motion[0])*8));count=max(2,min(8,count))
    scale=1+(count-2)*(15.909090909-1)/6
    position=np.clip(angle*.22*scale+(count-1)*.5,0,count-1)
    first=np.minimum(count-2,np.floor(position).astype(np.int32));fraction=position-first
    phase=np.mod(u*112,1)-.5
    t=np.clip((fraction-.5-phase*.2)*12.5+.5,0,1)
    weight=(.02+.96*t*t*(3-2*t))[...,None]
    def tile(index):return preview.sample((index%2*256+2.5+u*251)/512,(66.5+index//2*1008+v*1003)/4096)
    return display(tile(first)*(1-weight)+tile(first+1)*weight)
