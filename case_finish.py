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
    out=dict(finish=finish,tint=tint,grip_tape=bool(c.get('grip_tape',False)),screw_mask=c.get('screw_mask'),detail_mask=c.get('detail_mask'))
    for name,default,hi in (('tint_strength',.35,1),('haze',.42,1),('depth',.018,.06)):
        x=float(c.get(name,default))
        if not math.isfinite(x) or not 0<=x<=hi:raise ValueError('Invalid shell '+name)
        out[name]=x
    return out
def screw_positions(path):
    """Each isolated white spot is one decorative case screw, in full artwork UVs."""
    if not path:return None
    with Image.open(path) as im:
        pixels=np.asarray(im.convert('L').resize((256,992),Image.Resampling.NEAREST))>=128
    points=[]
    for y,x in zip(*np.where(pixels)):
        if not pixels[y,x]:continue
        pixels[y,x]=False;stack=[(int(x),int(y))];xs=[];ys=[]
        while stack:
            xx,yy=stack.pop();xs.append(xx);ys.append(yy)
            for nx,ny in ((xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)):
                if 0<=nx<256 and 0<=ny<992 and pixels[ny,nx]:
                    pixels[ny,nx]=False;stack.append((nx,ny))
        if len(xs)<3:continue
        radius=max((max(xs)-min(xs)+1)/512,(max(ys)-min(ys)+1)*4/1984)
        if radius>.08:raise ValueError('Screw mask spots must be small, separate circles (under 16% of canvas width).')
        points.append(((min(xs)+max(xs)+1)/512,(min(ys)+max(ys)+1)/1984,max(.008,radius)))
        if len(points)>16:raise ValueError('Screw masks support up to 16 separate white spots.')
    return points

def pack(image,cfg=None):
    import cd_finish
    c=settings(cfg);image=image.convert('RGB').resize((512,1984),Image.Resampling.LANCZOS)
    out=cd_finish.pack(image,Image.new('L',image.size,128),dict(enabled=True,depth_strength=0,clear_layer=False))
    out.paste(image.filter(ImageFilter.GaussianBlur(2+c['haze']*26)).resize((512,2048)),(0,2048))
    draw=ImageDraw.Draw(out)
    def strip(y,rgb):draw.rectangle((384,y,511,y+3),fill=tuple(layer_atlas.encode_linear(x) for x in rgb)+(255,))
    strip(24,MARKER)
    strip(16,(1 if c['finish']=='frosted' else 0,c['haze'],c['depth']/.06))
    strip(20,(1 if c['grip_tape'] else 0,0,0))
    rgb=ImageColor.getrgb(c['tint']);strip(8,tuple((v/255)**2.2 for v in rgb))
    strip(12,(c['tint_strength'],0,0))
    if c['screw_mask'] or c['detail_mask']:
        strip(48,(1 if c['screw_mask'] else 0,1 if c['detail_mask'] else 0,.72))
        points=screw_positions(c['screw_mask']) or []
        for i in range(16):
            values=points[i] if i<len(points) else (0,0,0)
            rgb=tuple(layer_atlas.encode_linear(x) for x in (values[0],values[1],values[2]/.08))+(255,)
            draw.rectangle((i*8,40,i*8+7,43),fill=rgb)
        if c['detail_mask']:
            with Image.open(c['detail_mask']) as mask:
                alpha=Image.new('L',out.size,255)
                alpha.paste(mask.convert('L').resize((512,2048),Image.Resampling.BILINEAR),(0,2048))
                out.putalpha(alpha)
    return out
def preview(p,angle,u,v):
    from effect_preview import display
    from board_preview import mounting_ports,board_to_artwork
    cfg=p.sample(.875,19/4096);tint=p.sample(.875,11/4096);strength=p.sample(.875,15/4096)[0]
    bu=(u-.031)/.93;bv=(v-.07715)/.91797
    def outline(inset):
        nose=bv<.5;cap=np.where(nose,.499,.635);along=np.where(nose,bv,1-bv)
        end=np.clip(1-(along-inset/3.77)/(cap-inset/3.77),0,1)
        half=(.5-inset)*np.sqrt(np.maximum(0,1-end**np.where(nose,9.32,10)))
        return np.clip((half-np.abs(bu-.5))*220,0,1)
    cavity=outline(.012)[...,None];inside=outline(.035)[...,None]
    wall=np.clip(outline(.010)-outline(.039),0,1)[...,None]
    lip=np.clip(outline(.034)-outline(.040),0,1)[...,None]
    seam=np.clip(outline(.013)-outline(.018),0,1)[...,None]
    view=np.clip(np.sin(float(angle)*.8),-1,1)
    x=np.clip(u+view*cfg[2]*.06,0,1)
    a=p.sample(x,64/4096+v*1984/4096);b=p.sample(x,.5+v*.5)
    art=a+(b-a)*(cfg[0]*(1-(1-cfg[1])**2))
    cavity_colour=np.array([.047,.080,.084])
    interior=cavity_colour+(art-cavity_colour)*inside
    shell=.22+(.04+tint*.55-.22)*strength
    rgb=shell+(interior-shell)*cavity
    rgb+=(.40+tint*.15-rgb)*(cfg[0]*(.045+cfg[1]*.30))
    rgb*=1-lip*.46
    rgb+=(np.array([.29,.32,.32])-rgb)*wall*.30
    rgb+=wall*(.065+abs(view)*.095)*.48
    rgb*=1-seam*.28
    bosses=np.zeros(np.broadcast_shapes(u.shape,v.shape))
    flags=p.sample(.875,51/4096);masked=abs(flags[2]-.72)<.008
    points=[(*board_to_artwork(*point),.026) for point in mounting_ports()]
    if masked and flags[0]>.5:
        points=[]
        for i in range(16):
            value=p.sample((i*8+4)/512,43/4096)
            if value[2]>.001:points.append((value[0],value[1],value[2]*.08))
    for pu,pv,rad in points:
        radius=np.sqrt((u-pu)**2+((v-pv)*4)**2)
        boss=np.clip((rad-radius)/max(.002,rad*.15),0,1)[...,None]
        bore=np.clip((rad*.38-np.sqrt((u-pu-view*.005)**2+((v-pv)*4)**2))/.003,0,1)[...,None]
        rgb+=(np.array([.27,.29,.285])-rgb)*boss*.72
        rgb+=np.clip(1-np.abs(radius-rad*.73)/max(.002,rad*.15),0,1)[...,None]*.09
        rgb+=(np.array([.025,.030,.029])-rgb)*bore*.91
        bosses+=boss[...,0]
    if masked and flags[1]>.5:
        plane=p.alpha
        ix=np.clip((u*512).astype(int),0,511);iy=np.clip((2048+v*2048).astype(int),2048,4095)
        detail=plane[iy,ix][...,None]
        rgb+=(.30+tint*.12-rgb)*detail*.40
    thickness=.5+wall*1.25+lip*.65+bosses[...,None]*.65
    rgb*=np.exp2(thickness*np.log2(np.maximum(tint,.025))*strength)
    width=.32 if cfg[0]>.5 else .13
    band=np.clip(1-np.abs(u+v*.48-(.70+view*.42))/width,0,1)
    rgb+=band[...,None]**2*(.008 if cfg[0]>.5 else .14)
    return display(rgb)
