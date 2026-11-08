"""Static atlases for tilt-refreshed e-paper and native-clock glitch effects."""
import numpy as np
from PIL import Image,ImageDraw,ImageColor
import layer_atlas
PRESETS={'tearing':'Scanline tearing','rgb':'RGB breakup','dropout':'Signal dropouts'}
def settings(mode,cfg=None):
 c=cfg or {}
 if mode=='eink':return dict(span=max(.2,min(2,float(c.get('span',1.55)))),ghosting=max(0,min(.3,float(c.get('ghosting',.03)))))
 colour_mode=c.get('colour_mode','rgb')
 if colour_mode not in ('rgb','one','two'):raise ValueError('Unknown glitch colour mode')
 colours=[c.get('colour1','#ff1744'),c.get('colour2','#00e5ff')]
 for colour in colours:ImageColor.getrgb(colour)
 return dict(preset=c.get('preset','tearing') if c.get('preset','tearing') in PRESETS else 'tearing',strength=max(0,min(1,float(c.get('strength',.7)))),density=max(20,min(240,int(c.get('density',180)))),speed=max(1,min(30,float(c.get('speed',15)))),colour_mode=colour_mode,colour1=colours[0],colour2=colours[1])
def paper(im):
 x=np.asarray(im.convert('L'),dtype=np.float32)/255
 x=np.round(x*3)/3
 # Neutral pigment, with an off-white paper substrate. No original colour leaks.
 return Image.fromarray(np.uint8(np.rint((.08+x*.82)*255))).convert('RGB')
def pack(mode,a,b=None,cfg=None):
 from creator_engine import atlas
 c=settings(mode,cfg)
 if mode=='eink':
  import cd_finish
  a=paper(a);b=paper(b or a)
  out=cd_finish.pack(a,Image.new('L',a.size,128),dict(enabled=True,layout='corner',clear_layer=False,depth_strength=0,sheen_strength=0))
  out.paste(b.resize((512,2048),Image.Resampling.LANCZOS),(0,2048))
 else:out=atlas(a,b or a).convert('RGBA')
 draw=ImageDraw.Draw(out)
 def strip(y,rgb):draw.rectangle((384,y,511,y+3),fill=tuple(layer_atlas.encode_linear(x) for x in rgb)+(255,))
 strip(24,(.21,.43,.65) if mode=='eink' else (.71,.13,.39))
 strip(16 if mode=='eink' else 28,((c['span']-.2)/1.8,c['ghosting']/.3,0) if mode=='eink' else (c['strength'],c['density']/240,c['speed']/30))
 if mode=='glitch':
  strip(32,(list(PRESETS).index(c['preset'])/2,('rgb','one','two').index(c['colour_mode'])/2,0))
  for y,key in ((40,'colour1'),(44,'colour2')):
   rgb=np.asarray(ImageColor.getrgb(c[key]),dtype=float)/255
   strip(y,np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4))
 return out

def preview(p,mode,angle,u,v):
 from effect_preview import AtlasPreview,display
 if mode=='eink':
  span=.2+float(p.sample(.875,19/4096)[0])*1.8
  t=np.clip((float(angle)+span*.5)/span,0,1)
  def smooth(a,b,x):
   t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
  wipe=smooth(-.12,.12,smooth(.25,.80,t)-v)[...,None]
  a=p.sample(u,64/4096+v*1984/4096);b=p.sample(u,.5+v*.5)
  x=b+(a-b)*wipe;flash=smooth(.12,.28,t)*(1-smooth(.30,.46,t));x=x+(1-2*x)*flash
  return display(x)
 c=p.sample(.875,31/4096);row=np.floor(v*(20+c[1]*220));tick=np.floor(getattr(p,'clock_seconds',0)*max(1,float(c[2])*30));noise=np.mod(np.sin(row*78.233+tick*37.719)*43758.5453,1)
 shift=np.where(noise>.65,(noise-.5)*.08*c[0],0)
 x=p.sample(np.clip(u+shift,0,1),64/4096+v*1984/4096)
 rgb=np.stack((noise>.7,(noise>.45)&(noise<.7),noise<.3),axis=-1)
 palette=p.sample(.875,35/4096)[1]
 if palette>.25:
  first=p.sample(.875,43/4096);second=p.sample(.875,47/4096)
  rgb=np.where((noise>.8)[...,None],first,second) if palette>.75 else first
 return display(np.where((noise>.82)[...,None],rgb,x))
