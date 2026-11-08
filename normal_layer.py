"""Optional tangent-space normal placement. Image colours are vector data, not sRGB."""
import math
import numpy as np
from PIL import Image, ImageDraw
import image_placement

MARKER=(.31,.63,.87)

def settings(value=None):
    value=value or {}
    strength=float(value.get('strength',1))
    if not math.isfinite(strength) or not 0 <= strength <= 4:
        raise ValueError('Normal strength must be between 0 and 400%.')
    style=value.get('style','custom' if value.get('path') else 'automatic')
    if style not in ('automatic','custom','none'):raise ValueError('Unknown normal map mode.')
    return dict(path=str(value.get('path') or ''),style=style,strength=strength,
                flip_y=bool(value.get('flip_y',False)),
                linked=bool(value.get('linked',True)),placement=dict(value.get('placement') or {}))

def frame(value, fit='Stretch', size=(512,1024)):
    value=settings(value)
    # Neutral padding is a flat surface, never a black (diagonal) normal.
    placed=image_placement.frame(value['path'],fit,'#8080ff',value['placement'],size=size)
    vector=np.asarray(placed,dtype=np.float32)/127.5-1
    if value['flip_y']:vector[...,1]*=-1
    angle=math.radians(float(value['placement'].get('rotation',0)))
    c,s=math.cos(angle),math.sin(angle)
    x,y=vector[...,0].copy(),vector[...,1].copy()
    vector[...,0]=(c*x-s*y)*value['strength']
    vector[...,1]=(s*x+c*y)*value['strength']
    vector[...,2]=np.maximum(vector[...,2],1/255)
    vector/=np.maximum(np.linalg.norm(vector,axis=-1,keepdims=True),1.e-8)
    return vector

def disc_frame(layout='corner',strength=1,size=(512,1024)):
    """Accepted corner slopes; continuous single-start spiral for full discs."""
    yy,xx=np.mgrid[0:size[1],0:size[0]]
    u=(xx+.5)/size[0];v=(yy+.5)/size[1]
    if layout=='corner':
        x=u-1.18;y=(v+.18)*4
        r=np.sqrt(x*x+y*y)
        slope=(np.sin(r*430+.12*np.sin(r*71))*.040+np.sin(r*773+.3)*.014)*strength
        nx=slope*x/r;ny=slope*y/r
    else:
        x=u-.4805;y=(v-.5434)*(.794/.205)
        r=np.sqrt(x*x+y*y);safe=np.maximum(r,.01)
        phase=r*430+np.arctan2(y,x)
        slope=(np.sin(phase+.12*np.sin(r*71))*.040+np.sin(r*773+np.arctan2(y,x)+.3)*.014)*strength
        # Spiral gradient includes its small tangential component. Flatten hub.
        fade=np.clip((r-.23)/.04,0,1)
        nx=slope*(x/safe-y/(430*safe*safe))*fade
        ny=slope*(y/safe+x/(430*safe*safe))*fade
    z=np.sqrt(np.maximum(1-nx*nx-ny*ny,0))
    return np.stack((nx,ny,z),axis=-1).astype(np.float32)

def embed(atlas,value,layout='corner'):
    value=settings(value)
    if value['style']=='none' or value['strength']==0:return atlas
    if value['style']=='custom' and not value['path']:return atlas
    vector=disc_frame(layout,value['strength']) if value['style']=='automatic' else frame(value)
    linear=vector*.5+.5
    # Existing atlas mip generation is sRGB-aware: encode data once so the shader
    # receives the original linear vector components after texture sampling.
    encoded=np.where(linear<=.0031308,linear*12.92,1.055*np.maximum(linear,0)**(1/2.4)-.055)
    atlas.paste(Image.fromarray(np.uint8(np.rint(np.clip(encoded,0,1)*255))),(0,3072))
    def srgb(x):return round(255*(12.92*x if x<=.0031308 else 1.055*x**(1/2.4)-.055))
    # Recognition rows 31/32 and effect/control strips must remain untouched.
    ImageDraw.Draw(atlas).rectangle((384,24,511,27),fill=tuple(srgb(x) for x in MARKER)+(255,))
    return atlas


def lenticular_frame(strength=.55,size=(512,8)):
    """One rounded cylindrical lens period, repeated across the deck in shader."""
    x=(np.arange(size[0],dtype=np.float32)+.5)/size[0]
    nx=np.sin(x*2*np.pi)*float(strength)
    nz=np.sqrt(np.maximum(1-nx*nx,0))
    row=np.stack((nx,np.zeros_like(nx),nz),axis=-1)
    return np.repeat(row[None,:,:],size[1],axis=0)

def embed_lenticular(atlas,strength=.55):
    vector=lenticular_frame(strength)
    linear=vector*.5+.5
    encoded=np.where(linear<=.0031308,linear*12.92,1.055*np.maximum(linear,0)**(1/2.4)-.055)
    out=atlas.convert('RGBA')
    recognition=out.crop((0,31,512,34)).tobytes()
    out.paste(Image.fromarray(np.uint8(np.rint(np.clip(encoded,0,1)*255))),(0,40))
    from layer_atlas import encode_linear
    ImageDraw.Draw(out).rectangle((384,24,511,27),fill=tuple(encode_linear(x) for x in (.44,.72,.16))+(255,))
    assert out.crop((0,31,512,34)).tobytes()==recognition, 'Lenticular recognition header changed'
    return out
