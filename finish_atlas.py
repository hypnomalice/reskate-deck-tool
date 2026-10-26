"""Image layouts for the tested metallic, ink and recessed-window finishes."""
import numpy as np
from PIL import Image, ImageDraw
from layer_atlas import encode_linear

MODES = ('metal', 'ink', 'window')

def pack(mode, graphic, second=None, object_image=None):
    if mode not in MODES:
        raise ValueError('Choose Metallic Flakes, Ink Flow or Impossible Window.')
    atlas=Image.new('RGB',(512,4096))
    def paste(image,y,height):
        atlas.paste(image.convert('RGB').resize((512,height),Image.Resampling.LANCZOS),(0,y))
    if mode=='window':
        if second is None:raise ValueError('Choose a background for the window.')
        frame=graphic.convert('RGBA')
        obj=object_image.convert('RGBA') if object_image is not None else Image.new('RGBA',graphic.size)
        paste(frame,64,960);paste(second,1024,1024);paste(obj,2048,1024)
        lut=[encode_linear(i/255) for i in range(256)]
        masks=[im.getchannel('A').resize((512,1024),Image.Resampling.LANCZOS).point(lut) for im in (frame,obj)]
        atlas.paste(Image.merge('RGB',(*masks,Image.new('L',(512,1024)))),(0,3072))
    else:
        paste(graphic,64,1984)
        y,x=np.indices((2048,512),dtype=np.uint32)
        n=x*np.uint32(0x9e3779b9)+y*np.uint32(0x85ebca6b)+np.uint32(0x2468ace1)
        n^=n>>16;n*=np.uint32(0x7feb352d);n^=n>>15;n*=np.uint32(0x846ca68b);n^=n>>16
        data=np.empty((2048,512,3),dtype=np.uint8)
        if mode=='ink':
            if second is None:raise ValueError('Choose a reveal mask for Ink Flow.')
            mask=second.convert('L').resize((512,2048),Image.Resampling.LANCZOS)
            data[:,:,0]=np.asarray(mask.point([encode_linear(i/255) for i in range(256)]))
        else:data[:,:,0]=np.where(n%10000<400,255,0)
        data[:,:,1]=188
        # Store noise in sRGB so the game's linear texture reads recover it.
        values=((n>>8)&65535).astype(np.float32)/65535
        data[:,:,2]=np.rint(np.where(values<=.0031308,12.92*values,1.055*values**(1/2.4)-.055)*255).astype(np.uint8)
        atlas.paste(Image.fromarray(data),(0,2048))
    draw=ImageDraw.Draw(atlas)
    for i,c in enumerate(((255,0,255),(0,255,255),(255,255,0),(0,255,0))):
        draw.rectangle((i*128,0,i*128+127,63),fill=c)
    draw.rectangle((0,48,127,63),fill=({'metal':32,'ink':64,'window':180}[mode],128,255))
    draw.rectangle((128,48,255,63),fill=(0,188,0))
    return atlas

def render(renderer,angle,u,v,view_pose=None):
    """Illustrative material preview; game lighting remains game-controlled."""
    from effect_preview import display
    from material_view import view_vector, cavity
    view=view_vector(angle,view_pose)
    slope=float(np.clip(view[0]/max(abs(view[2]),.0001),-1,1))
    mode=renderer.mode
    if mode in ('metal','ink'):
        rgb=renderer.sample(u,(64+v*1984)/4096)
        data=renderer.sample(u,.5+v*.5)
        if mode=='metal':
            align=np.clip(1-np.abs(data[:,:,2]-(.5+slope*.42))*8,0,1)
            sparkle=data[:,:,0]*align**4
            return display(rgb*.82+sparkle[:,:,None]*np.array([2.2,2.5,2.9]))
        incidence=float(np.linalg.norm(view[:2])/max(np.linalg.norm(view),1e-6))
        progress=np.clip((.6691306063588582-incidence)/.42720871075919054,0,1)
        progress=progress*progress*(3-2*progress)
        field=.5+.18*np.sin(u*11+v*5)+.14*np.sin(u*7-v*13)
        reveal=np.clip((progress-field+.16)/.32,0,1)
        reveal=reveal*reveal*(3-2*reveal)*data[:,:,0]
        return display(np.array([.018,.025,.055])+reveal[:,:,None]*np.array([.23,.5,.6]))
    # Port of the accepted authored shader's .7-deep corridor, not a fitted
    # background shift. The front, interior faces and object use distinct UVs.
    u,v=np.broadcast_arrays(u,v)
    inside,hit=cavity(renderer,u,v,view)
    rx,ry,z,_,_,_=hit
    ou=.5+((u-.5)+rx*.35)/.70
    ov=.5+((v-.5)*4+ry*.35)/1.40
    valid=(ou>0)&(ou<1)&(ov>0)&(ov<1)&(z>.35)
    ou,ov=np.clip(ou,.001,.999),np.clip(ov,.001,.999)
    obj=renderer.sample(ou,.5+ov*.25)
    alpha=renderer.sample(ou,.75+ov*.25)[...,1]*valid
    inside=inside*(1-alpha[...,None])+obj*alpha[...,None]
    front=renderer.sample(np.clip(u,.001,.999),(64+v*960)/4096)
    opacity=renderer.sample(np.clip(u,.001,.999),.75+v*.25)[...,0]
    return display(front*opacity[...,None]+inside*(1-opacity[...,None]))
