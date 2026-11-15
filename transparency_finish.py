"""Authoring contract for native transparency finishes.

The clear-case and crystal project keys remain stable. Optical settings describe
shell properties; they do not imply a full-scene blur or a screen-copy renderer.
"""
from copy import deepcopy
import math
from PIL import Image, ImageColor, ImageFilter

MODES = ('glass', 'case', 'crystal')
ARTWORK_REGION = (.031, .07715, .961, .99512)
DEFAULTS = {
    'glass': dict(finish='display', tint='#ffffff', tint_strength=0., haze=0.,
                  roughness=.04, reflection_strength=1., thickness=.010,
                  art_depth=.5, border=.008, grip_tape=False),
    'case': dict(finish='frosted', tint='#d9e6e7', tint_strength=.35, haze=.42,
                roughness=.48, reflection_strength=1., thickness=.010,
                art_depth=.5, border=.008, grip_tape=False, interior='artwork'),
    'crystal': dict(tint='#c5e4fa', tint_strength=.18, haze=0., roughness=.02,
                   reflection_strength=1., thickness=.010, art_depth=.5,
                   border=.008, grip_tape=False, cuts=140),
}
RANGES = dict(tint_strength=(0.,1.), haze=(0.,1.), roughness=(0.,1.),
              reflection_strength=(0.,2.), thickness=(.001,.03),
              art_depth=(.1,.9), border=(.002,.025))


def settings(mode, value=None):
    """Validate a copy, retaining old fields and explicit zero-valued settings."""
    if mode not in MODES:
        raise ValueError('Unknown transparency mode: '+str(mode))
    if value is not None and not isinstance(value, dict):
        raise ValueError('Transparency settings must be an object')
    result=deepcopy(DEFAULTS[mode]);result.update(deepcopy(value or {}))
    if mode=='case' and result.get('finish')=='glossy' and 'roughness' not in (value or {}):
        result['roughness']=.04
    try:
        rgb=ImageColor.getrgb(result['tint'])
        if len(rgb)!=3:raise ValueError('Use an RGB shell tint')
    except (TypeError,ValueError) as error:
        raise ValueError('Invalid shell tint') from error
    result['tint']='#%02x%02x%02x'%rgb
    for name,(low,high) in RANGES.items():
        value=result[name]
        if isinstance(value,bool):raise ValueError('Invalid shell '+name)
        try:value=float(value)
        except (TypeError,ValueError,OverflowError) as error:
            raise ValueError('Invalid shell '+name) from error
        if not math.isfinite(value) or not low<=value<=high:
            raise ValueError('Invalid shell '+name)
        result[name]=value
    if not isinstance(result['grip_tape'],bool):
        raise ValueError('Grip tape must be enabled or disabled')
    if mode=='glass' and result['finish'] not in ('display','water','liquid'):
        raise ValueError('Unknown glass finish')
    if mode=='glass' and result['finish']=='liquid':
        rim=result.get('rim_mm',10)
        if isinstance(rim,bool) or not isinstance(rim,(float,int)) or not 2<=rim<=25:
            raise ValueError('Liquid rim width must be between 2 and 25 mm')
        result['rim_mm']=float(rim)
        for key,default in [('opacity',.53),('viscosity',.26)]:
            val=result.get(key,default)
            if isinstance(val,bool) or not isinstance(val,(int,float)) or not 0<=val<=1:
                raise ValueError('Invalid liquid '+key)
            result[key]=float(val)
    if mode=='case':
        if result['finish'] not in ('frosted','glossy'):
            raise ValueError('Unknown clear-case finish')
        if result['interior'] not in ('artwork','pcb'):
            raise ValueError('Unknown clear-case interior')
    if mode=='crystal':
        count=result['cuts']
        if isinstance(count,bool) or not isinstance(count,(int,float)) or not math.isfinite(count) or int(count)!=count or not 12<=count<=400:
            raise ValueError('Crystal cuts must be a whole number from 12 to 400')
        result['cuts']=int(count)
    return result


def artwork_atlas(image, internal_blur_pixels=0.):
    """Keep the full template canvas; inset and top orientation belong to mesh UVs.

    Native insert shaders sample the upper half of a 512x4096 atlas. Adding the
    old opaque-effect header or trimming the source would shift this mapping.
    Blur here affects only the contained artwork, never background scenery.
    """
    radius=float(internal_blur_pixels)
    if not math.isfinite(radius) or not 0<=radius<=64:
        raise ValueError('Invalid internal artwork blur')
    art=image.convert('RGBA').resize((512,2048),Image.Resampling.LANCZOS)
    if radius:art=art.filter(ImageFilter.GaussianBlur(radius))
    atlas=Image.new('RGBA',(512,4096),(255,255,255,255))
    atlas.paste(art,(0,0))
    return atlas


def source_uv(x,z):
    """Board-space metres to the calibrated, uncropped source canvas."""
    left,top,right,bottom=ARTWORK_REGION
    return (left+(x/.216+.5)*(right-left),
            top+((.415-z)/.818)*(bottom-top))


def internal_blur_pixels(mode,value=None):
    cfg=settings(mode,value)
    if mode=='case' and (cfg['finish']=='glossy' or cfg['interior']=='pcb'):return 0.
    return min(64.,cfg['haze']*18*cfg['thickness']/.010)
