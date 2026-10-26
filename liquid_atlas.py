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


def render(renderer,angle,u,v,view_pose=None):
    """Authored cavity, fixed-world gravity, physical wet path and optical tint.

    Clock/motion inputs are held steady here; game slosh is not reproduced from
    camera movement. The pose changes gravity only when the board actually tilts.
    """
    from effect_preview import display
    from material_view import view_vector,gravity_vector,cavity,volume_offset,wet_path
    cloud,depth_value,amount=map(float,renderer.sample(.625,56/4096))
    colour=renderer.sample(.375,56/4096);depth=.025+.155*depth_value
    thickness=float(renderer.sample(.875,56/4096)[0])
    view=view_vector(angle,view_pose);gravity=gravity_vector(view_pose)
    u,v=np.broadcast_arrays(u,v)
    _,hit=cavity(renderer,u,v,view,liquid=True)
    _,_,_,bu,bv,_=hit
    px=u-.5;py=(v-.5)*4
    level=gravity[0]*px+gravity[1]*py-gravity[2]*depth*.5+volume_offset(gravity,depth,amount)
    fill_rx=float(view[0]*.35);fill_ry=float(view[1]*-.8)
    direction=gravity[0]*fill_rx+gravity[1]*fill_ry+gravity[2]
    wet,crossing=wet_path(level,direction,depth,amount)
    # An exactly upright view has no change along its parallel ray. Preserve
    # a narrow, pixel-sized liquid boundary instead of dividing by zero.
    du=float(np.ptp(u)/max(u.shape[1]-1,1));dv=float(np.ptp(v)/max(v.shape[0]-1,1))
    edge=max(.00008,.35*(abs(gravity[0])*du+abs(gravity[1])*4*dv))
    if abs(direction)<1e-5:
        wet=np.clip(level/edge+.5,0,1)*depth
        if amount<=.00001:wet[:]=0
        if amount>=.99999:wet[:]=depth
    fraction=np.clip(wet/depth,0,1)
    cap=np.abs(np.clip(level/edge+.5,0,1)-np.clip((level+direction*depth)/edge+.5,0,1))
    crossing=np.clip(crossing,0,depth);hx=px+fill_rx*crossing;hy=py+fill_ry*crossing
    amp=.0035*(1-thickness*.7)
    phase_a=hx*12+hy*3;phase_b=hx*-7+hy*9
    slope_x=amp*(np.cos(phase_a)*12+np.cos(phase_b)*-4.2)
    slope_y=amp*(np.cos(phase_a)*3+np.cos(phase_b)*5.4)
    ru=np.clip(bu+slope_x*fraction*.85,.001,.999)
    rv=np.clip(bv+slope_y*fraction*.85*.25,.001,.999)
    dry=renderer.sample(bu,.25+bv*.25)
    refracted=renderer.sample(ru,.25+rv*.25)
    if cloud>0:
        radius=cloud*fraction*.012
        blurred=sum(renderer.sample(np.clip(ru+dx*radius,.001,.999),.25+np.clip(rv+dy*radius,.001,.999)*.25) for dx,dy in ((1,0),(-1,0),(0,.25),(0,-.25)))*.25
        refracted=refracted*(1-cloud)+blurred*cloud
    wet_coverage=np.clip(wet/.001,0,1)
    scene=dry*(1-wet_coverage[...,None])+refracted*wet_coverage[...,None]
    path=wet*np.sqrt(1+fill_rx**2+fill_ry**2)
    transmission=np.exp(-path[...,None]*(.7/depth)*(.7+4*(1-colour)))
    inside=scene*transmission+colour*(1-transmission)
    # Projected front-art shadow remains on the interior, not on the fixed label.
    shadow=renderer.sample(np.clip(.5+hx+crossing*.35,.001,.999),.75+np.clip(.5+hy*.25+crossing*.12,.001,.999)*.25)[...,0]
    cap_colour=scene*.22+(colour*.8+.035)*.78
    inside=inside*(1-cap[...,None]*.72)+cap_colour*cap[...,None]*.72
    inside*=1-shadow[...,None]*(.22+.16*fraction[...,None])
    inside=inside*(1-cloud*fraction[...,None]*.3)+colour*cloud*fraction[...,None]*.3
    front=renderer.sample(np.clip(u,.001,.999),(64+v*960)/4096)
    opacity=renderer.sample(np.clip(u,.001,.999),.75+v*.25)[...,0]
    return display(front*opacity[...,None]+inside*(1-opacity[...,None]))
