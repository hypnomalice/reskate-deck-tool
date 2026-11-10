"""Opt-in shared white sheen; lossless smooth-depth transport is separate."""
import math
from PIL import ImageDraw
import numpy as np

def settings(value=None):
    value=value or {}
    if not isinstance(value,dict):raise ValueError('Surface finish settings must be an object.')
    shimmer=value.get('shimmer',False);strength=float(value.get('strength',.35));banding=value.get('smooth_depth',True)
    if type(shimmer) is not bool or type(banding) is not bool:raise ValueError('Finish switches must be true or false.')
    if not math.isfinite(strength) or not 0<=strength<=1:raise ValueError('Shimmer strength must be between 0 and 1.')
    holographic=value.get('holographic',False)
    holo_strength=float(value.get('holo_strength',.35))
    if type(holographic) is not bool or not math.isfinite(holo_strength) or not 0<=holo_strength<=1:
        raise ValueError('Holographic strength must be between 0 and 1.')
    return dict(shimmer=shimmer,strength=strength,smooth_depth=banding,holographic=holographic,holo_strength=holo_strength)

def smooth_depth(project):
    mode=project.get('mode')
    return settings(project.get('surface_finish'))['smooth_depth'] and (mode=='ghost' or mode in ('depth','layers') and not project.get('lenticular',True))

def mark(atlas,value,*,mode=None):
    cfg=settings(value)
    if not cfg['shimmer'] and not cfg['holographic']:return atlas
    from layer_atlas import encode_linear
    out=atlas.copy();w,h=out.size
    colour=tuple(encode_linear(v) for v in (.79,.02,cfg['strength']))
    if out.mode=='RGBA':colour+=(255,)
    # A reserved part of the hidden recognition strip; all existing control rows
    # (48/4096..64/4096) and animation timing tables are untouched.
    digital=mode in ('case','eink')
    if cfg['shimmer']:
        first,last=(36,40) if digital else (8,24)
        ImageDraw.Draw(out).rectangle((w*3//4,h*first//4096,w-1,h*last//4096-1),fill=colour)
    if cfg['holographic']:
        colour=tuple(encode_linear(v) for v in (.83,.17,cfg['holo_strength']))
        if out.mode=='RGBA':colour+=(255,)
        first,last=(44,48) if digital else (36,40)
        ImageDraw.Draw(out).rectangle((w*3//4,h*first//4096,w-1,h*last//4096-1),fill=colour)
    return out

def preview(image,angle,u,v,marker,holo=None):
    shimmer=.78<marker[0]<.80 and marker[1]<.04
    rainbow=holo is not None and .82<holo[0]<.84 and .16<holo[1]<.18
    if not shimmer and not rainbow:return image
    from effect_preview import linear,display
    vx=math.sin(float(angle)*.8);vy=0
    q=(vx*.30+vy*.1+(u-.5)*.16+(v-.5)*.8)/.10
    sheen=np.exp(-q*q)*.08*float(marker[2]) if shimmer else 0
    rgb=linear(image)
    if rainbow:
        phase=u*1.6+v*.45+float(angle)*.7
        tint=.5+.5*np.cos(phase[...,None]*math.tau+np.array([0,2.094,4.189]))
        rgb=rgb+tint*float(holo[2])*.24
    return display(rgb+np.asarray(sheen)[...,None]*(1-rgb))
