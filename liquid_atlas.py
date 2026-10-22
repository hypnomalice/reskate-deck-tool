"""Authored bottle controls and explicit front transparency contract."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageColor
from layer_atlas import encode_linear

DEFAULTS=dict(colour='#9630d8',cloudiness=.15,depth=.09,amount=.5,thickness=.25)


def settings(values=None):
    result=dict(DEFAULTS,**(values or {}))
    ImageColor.getrgb(result['colour'])
    for key,low,high in [('cloudiness',0,1),('depth',.025,.18),('amount',0,1),('thickness',0,1)]:
        value=float(result[key])
        if not math.isfinite(value) or not low<=value<=high:
            raise ValueError(f'Liquid {key} must be between {low} and {high}.')
        result[key]=value
    return result


def pack(front,background,values=None):
    import finish_atlas
    cfg=settings(values)
    atlas=finish_atlas.pack('window',front,background)
    draw=ImageDraw.Draw(atlas)
    draw.rectangle((0,48,127,63),fill=(244,128,255))
    draw.rectangle((128,48,255,63),fill=ImageColor.getrgb(cfg['colour']))
    draw.rectangle((256,48,383,63),fill=tuple(encode_linear(v) for v in
        (cfg['cloudiness'],(cfg['depth']-.025)/.155,cfg['amount'])))
    draw.rectangle((384,48,511,63),fill=(encode_linear(cfg['thickness']),0,0))
    return atlas


def render(renderer,angle,u,v):
    """Illustrative tilted bottle; game motion and lighting are separate."""
    from effect_preview import display
    cfg=renderer.sample(.625,56/4096)
    cloud,depth,amount=map(float,cfg)
    colour=renderer.sample(.375,56/4096)
    depth=.025+.155*depth
    # Upright authoring view: camera angle never reverses gravity.
    tilt=float(angle)
    u,v=np.broadcast_arrays(u,v)
    rx=tilt*.65;ry=.65
    px=u-.5;py=(v-.5)*4
    exit_x=(.5-np.sign(rx)*px)/max(abs(rx),1e-6)
    exit_y=(2-py)/ry
    z=np.maximum(0,np.minimum(depth,np.minimum(exit_x,exit_y)))
    back_face=z>=depth-1e-5
    side_face=exit_x<exit_y
    back_u=np.clip(u+rx*z,0,1);back_v=np.clip(v+ry*z*.25,0,1)
    wall_u=np.where(rx>=0,1-z/depth*.12,z/depth*.12)
    sample_u=np.where(back_face,back_u,np.where(side_face,wall_u,back_u))
    sample_v=np.where(back_face,back_v,np.where(side_face,back_v,1-z/depth*.12))
    level=(v-(1-amount))*4
    end_level=level+ry*z
    pixel=max(.0001,4/max(1,u.shape[0]))
    front_wet=np.clip(level/pixel+.5,0,1)
    rear_wet=np.clip(end_level/pixel+.5,0,1)
    cap=np.maximum(0,rear_wet-front_wet)
    wet_path=np.maximum(0,z-np.clip(-level/ry,0,z))
    wet=np.maximum(front_wet,wet_path/depth)
    if amount<=.00001:wet[:]=0;cap[:]=0
    if amount>=.99999:wet[:]=1;cap[:]=0
    thickness=float(renderer.sample(.875,56/4096)[0])
    ripple=np.sin(u*12+v*12+tilt*(2-1.5*thickness))*depth*.045*wet*(1-.7*thickness)
    back=renderer.sample(np.clip(sample_u+ripple,0,1),.25+np.clip(sample_v+ripple*.25,0,1)*.25)
    if cloud>0:
        blurred=sum(renderer.sample(np.clip(sample_u+ripple+dx*.012*cloud,0,1),.25+np.clip(sample_v+ripple*.25+dy*.003*cloud,0,1)*.25) for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)))*.25
        soften=cloud*wet[:,:,None]
        back=back*(1-soften)+blurred*soften
    back*=np.where(back_face,1,np.where(side_face,.78,.87))[:,:,None]
    transmission=np.exp(-wet[:,:,None]*(.7+4*(1-colour))*.7)
    inside=back*transmission+colour*(1-transmission)
    inside=inside*(1-cloud*wet[:,:,None]*.3)+colour*cloud*wet[:,:,None]*.3
    cap_colour=back*.22+(colour*.8+.035)*.78
    inside=inside*(1-cap[:,:,None]*.72)+cap_colour*cap[:,:,None]*.72
    front=renderer.sample(u,(64+v*960)/4096)
    alpha=renderer.sample(u,.75+v*.25)[:,:,0]
    shadow=renderer.sample(np.clip(u+depth*.35,0,1),.75+np.clip(v+depth*.12,0,1)*.25)[:,:,0]
    inside*=1-shadow[:,:,None]*(.22+.16*wet[:,:,None])
    return display(front*alpha[:,:,None]+inside*(1-alpha[:,:,None]))
