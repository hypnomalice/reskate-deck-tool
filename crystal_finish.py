"""Deterministic cut-crystal optics shared by preview and native atlas export."""
import math
import numpy as np
from PIL import Image,ImageDraw,ImageColor
import layer_atlas
MARKER=(.73,.19,.57)

def settings(value=None):
 c=value or {};tint=c.get('tint','#c5e4fa');ImageColor.getrgb(tint)
 cuts=float(c.get('cuts',140))
 if not math.isfinite(cuts) or not 12<=cuts<=400:raise ValueError('Crystal cuts must be between 12 and 400')
 if c.get('finish','crystal')!='crystal':raise ValueError('This release supports cut crystal only')
 return dict(tint=tint,cuts=round(cuts),grip_tape=bool(c.get('grip_tape',False)))


def facet_map(cuts,size=(512,2048)):
 nx=max(2,round(math.sqrt(cuts/5.6)));ny=max(3,round(cuts/(nx*2)));w,h=size
 rng=np.random.default_rng(317);out=Image.new('RGB',size);draw=ImageDraw.Draw(out);pts={}
 for y in range(ny+1):
  for x in range(nx+1):pts[x,y]=(round((x+(rng.uniform(-.22,.22) if 0<x<nx else 0))*w/nx),round((y+(rng.uniform(-.22,.22) if 0<y<ny else 0))*h/ny))
 for y in range(ny):
  for x in range(nx):
   a,b,c,d=pts[x,y],pts[x+1,y],pts[x+1,y+1],pts[x,y+1]
   for tri in ((a,b,c),(a,c,d)) if (x+y)%2==0 else ((a,b,d),(b,c,d)):
    slopes=rng.uniform(-.68,.68,2);values=(.5+slopes[0]*.5,.5+slopes[1]*.5,float(rng.uniform(.12,.95)))
    draw.polygon(tri,fill=tuple(layer_atlas.encode_linear(v) for v in values))
 return out

def pack(image,cfg=None):
 import case_finish
 c=settings(cfg)
 # Keep the established native texture layout and closed mesh bindings.
 atlas=case_finish.pack(image,dict(finish='glossy',tint=c['tint'],tint_strength=.35,haze=0,depth=.045,grip_tape=c['grip_tape']))
 optics=facet_map(c['cuts'])
 atlas.paste(optics,(0,2048));draw=ImageDraw.Draw(atlas)
 draw.rectangle((384,24,511,27),fill=tuple(layer_atlas.encode_linear(v) for v in MARKER)+(255,))
 draw.rectangle((384,52,511,55),fill=tuple(layer_atlas.encode_linear(v) for v in (0,0,.91))+(255,))
 draw.rectangle((384,56,511,59),fill=tuple(layer_atlas.encode_linear(v) for v in (0,0,.83))+(255,))
 return atlas

def preview(p,angle,u,v,*,top=False):
 from effect_preview import display
 # Native equipped grip is supplied by the game, not painted by this preview.
 grip=p.sample(.875,23/4096)[0]>.5
 if top:
  shape=np.broadcast_shapes(u.shape,v.shape)
  if grip:return Image.new('RGBA',(shape[1],shape[0]),(0,0,0,0))
  art=p.sample(1-u,64/4096+v*1984/4096)
  tint=p.sample(.875,11/4096)
  return display(art*np.maximum(tint,.025)**.12)
 view=np.clip(np.sin(float(angle)*.8),-1.5,1.5)
 f=p.sample(u,.5+v*.5);fx=f[...,0]*2-1;fy=f[...,1]*2-1;seed=f[...,2]
 ru=np.clip(u+fx*.105+view*(.018+seed*.040),0,1);rv=np.clip(v+fy*.035,0,1)
 a=p.sample(ru,64/4096+rv*1984/4096)
 bu=(1-u+fx*.19-view*.065)%1;bv=(v+fy*.080)%1;b=p.sample(bu,64/4096+bv*1984/4096)
 facing=np.abs(fx*.78+fy*.25+view*.58);ref=np.clip((facing-.28)*2.1,0,1);dark=.28+(1-ref)*.94
 glint=np.exp2(((facing-.42)/.038)**2*-1.442695)*.78
 edge=np.clip((np.maximum(np.abs(u-.5),np.abs(v-.5)*.9)-.38)*8,0,1)
 tint=p.sample(.875,11/4096)
 # Through-body tint grows at the perimeter and in reflected cuts.
 path=.12+edge*.70+ref*.24
 absorption=np.exp2(np.log2(np.maximum(tint,.025))*path[...,None])
 rgb=((a+(b-a)*(ref*.78)[...,None])*dark[...,None]+glint[...,None])*absorption
 return display(rgb)
