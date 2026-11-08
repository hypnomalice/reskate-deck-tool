"""Opaque layered-plastic approximation: no scene copies or glass pass."""
import math
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageColor
import layer_atlas
MARKER=(.36,.81,.24)
def settings(value=None):
    c=value or {}; finish=c.get('finish','frosted')
    if finish not in ('frosted','glossy'):raise ValueError('Unknown shell finish')
    tint=c.get('tint','#d9e6e7');ImageColor.getrgb(tint)
    out=dict(finish=finish,tint=tint)
    for name,default,hi in (('tint_strength',.35,1),('haze',.42,1),('depth',.018,.06)):
        x=float(c.get(name,default))
        if not math.isfinite(x) or not 0<=x<=hi:raise ValueError('Invalid shell '+name)
        out[name]=x
    return out
def pack(image,cfg=None):
    import cd_finish
    c=settings(cfg);image=image.convert('RGB').resize((512,1984),Image.Resampling.LANCZOS)
    out=cd_finish.pack(image,Image.new('L',image.size,128),dict(enabled=True,depth_strength=0,clear_layer=False))
    out.paste(image.filter(ImageFilter.GaussianBlur(2+c['haze']*10)).resize((512,2048)),(0,2048))
    draw=ImageDraw.Draw(out)
    def strip(y,rgb):draw.rectangle((384,y,511,y+3),fill=tuple(layer_atlas.encode_linear(x) for x in rgb)+(255,))
    strip(24,MARKER)
    strip(16,(1 if c['finish']=='frosted' else 0,c['haze'],c['depth']/.06))
    rgb=ImageColor.getrgb(c['tint']);strip(8,tuple((v/255)**2.2 for v in rgb))
    strip(12,(c['tint_strength'],0,0))
    return out
def preview(p,angle,u,v):
    from effect_preview import display
    cfg=p.sample(.875,19/4096);tint=p.sample(.875,11/4096);strength=p.sample(.875,15/4096)[0]
    x=np.clip((u-.10)/.8+np.sin(float(angle)*.8)*cfg[2]*.06,0,1);y=np.clip((v-.08)/.84,0,1)
    a=p.sample(x,64/4096+y*1984/4096);b=p.sample(x,.5+y*.5)
    art=a+(b-a)*(cfg[0]*cfg[1])
    border=np.minimum(np.minimum(u-.1,.9-u),np.minimum(v-.08,.92-v))
    inside=np.clip(border*180,0,1)[...,None]
    rgb=(.12+art*.65)*inside+(.23+.09*tint)*(1-inside)
    rgb=rgb*(1-strength*.7)+rgb*tint*strength*.7
    q=(u-.5)*.5+(v-.5)*.35+np.sin(float(angle)*.8)*.45
    sheen=np.exp(-(q/(.12+cfg[0]*.16))**2)*(.14-cfg[0]*.09)
    rgb+=sheen[...,None]
    return display(rgb)
