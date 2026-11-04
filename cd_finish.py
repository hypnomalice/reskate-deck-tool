"""Experimental CD finish contract, lossless depth transport and approximate preview.

Requires the separately installed SDEC 2.1.0 or newer.
Finish and layout are independent. Artwork pixels are never regenerated here.
"""
import hashlib
import math
import struct
import uuid
import numpy as np
from PIL import Image,ImageDraw

FINISHES={'mirror':'Mirror silver','dye':'Dyed silver','cd_mirror':'CD mirror'}
LAYOUTS={'full':'Full CD art','corner':'Corner CD art'}
COLOURS={'separate':'Separate artwork colours','shared':'Match disc colours'}
RUNTIME='SDEC 2.1.0+'
OPTICS={'original':'Original','reflection':'Mirror contrast','diffraction':'Stronger diffraction','combined':'Combined'}

def settings(value=None):
    value=value or {}
    if not isinstance(value,dict):raise ValueError('CD settings must be an object.')
    result=dict(enabled=value.get('enabled',False),finish=value.get('finish','cd_mirror'),layout=value.get('layout','full'),colours=value.get('colours','separate'))
    if type(result['enabled']) is not bool:raise ValueError('CD enabled must be true or false.')
    for key,choices in [('finish',FINISHES),('layout',LAYOUTS),('colours',COLOURS)]:
        if result[key] not in choices:raise ValueError('Unknown CD '+key+'.')
    result['optics']=value.get('optics','original')
    if result['optics'] not in OPTICS:raise ValueError('Unknown CD reflection response.')
    for key,default,maximum in [('depth_strength',1,2),('faint_visibility',.175,1),('sheen_strength',1,2),('rim_strength',0,4),('boundary_strength',0,4),('scratch_strength',0,4),('scratch_amount',2,4)]:
        number=float(value.get(key,default))
        if not math.isfinite(number) or not 0<=number<=maximum:raise ValueError('Invalid CD '+key.replace('_',' ')+'.')
        result[key]=number
    result['scratch_amount']=int(result['scratch_amount'])
    result['clear_layer']=value.get('clear_layer',True)
    result['stronger_backing']=value.get('stronger_backing',False)
    if type(result['clear_layer']) is not bool or type(result['stronger_backing']) is not bool:raise ValueError('CD finish switches must be true or false.')
    return result

def enabled(project):
    return project.get('mode')=='cd' or project.get('mode')=='ghost' and settings(project.get('cd'))['enabled']

def marker(value):
    value=settings(value)
    if value['finish']=='cd_mirror':
        return (.775,{('full','shared'):.10,('full','separate'):.30,('corner','shared'):.65,('corner','separate'):.85}[value['layout'],value['colours']],.95)
    green={('full','mirror'):.10,('full','dye'):.30,('corner','mirror'):.65,('corner','dye'):.85}[value['layout'],value['finish']]
    return (.855 if value['colours']=='separate' else .895,green,.95)

def pack(image,depth,value):
    import smooth_effect,layer_atlas
    value=settings(value)
    image=image.convert('RGB').resize((512,1984),Image.Resampling.LANCZOS)
    depth=depth.convert('L').resize((512,1984),Image.Resampling.BILINEAR)
    atlas=smooth_effect.pack(image,depth,0,.5,True).convert('RGBA')
    atlas.paste(image,(0,64))
    # RGB code recognizes a Ghost surface; the CD settings strip selects our renderer.
    atlas.paste(Image.new('RGB',(512,2048),(188,188,0)),(0,2048))
    ImageDraw.Draw(atlas).rectangle((128,48,255,63),fill=tuple(layer_atlas.encode_linear(x) for x in marker(value))+(255,))
    draw=ImageDraw.Draw(atlas)
    def strip(column,row,values):
        draw.rectangle((column*128,row,column*128+127,row+7 if row==0 else row+15),fill=tuple(layer_atlas.encode_linear(x) for x in values)+(255,))
    # Row 32 is the four-part recognition header; never write over it.
    strip(0,0,(.17,.73,.41))
    strip(1,0,(0,value['faint_visibility'],value['sheen_strength']/2))
    strip(2,0,(value['rim_strength']/4,value['boundary_strength']/4,value['scratch_strength']/4))
    strip(3,0,(value['scratch_amount']/4,0,0))
    response={'reflection':.34,'diffraction':.42,'combined':.38}.get(value['optics'])
    if response is not None:strip(0,8,(response,.12,.88))
    if value['stronger_backing']:strip(2,8,(.66,.04,.94))
    if value['clear_layer']:strip(3,8,(.74,.06,.75))
    alpha=Image.new('L',atlas.size,255)
    alpha.paste(depth.point([round(128+96*min(1,x/255*value['depth_strength'])) for x in range(256)]),(0,64));atlas.putalpha(alpha)
    return atlas

def mip_payload(atlas):
    rgba=np.asarray(atlas,dtype=np.float32)/255
    linear=np.where(rgba<=.04045,rgba/12.92,((rgba+.055)/1.055)**2.4);linear[...,3]=rgba[...,3]
    levels=[];sizes=[]
    while True:
        enc=np.where(linear<=.0031308,linear*12.92,1.055*np.maximum(linear,0)**(1/2.4)-.055);enc[...,3]=linear[...,3]
        payload=np.uint8(np.rint(np.clip(enc,0,1)*255)).tobytes();levels.append(payload);sizes.append(len(payload))
        h,w=linear.shape[:2]
        if h==1 and w==1:break
        linear=np.stack([np.asarray(Image.fromarray(linear[...,c]).resize((max(1,w//2),max(1,h//2)),Image.Resampling.BOX)) for c in range(4)],-1)
    return b''.join(levels),sizes

def lossless_archive(data,atlases):
    """Replace only chunks whose exact encoded payload hash belongs to a CD atlas."""
    from fbmod_compat import Archive,unpack,pack as cas_pack
    import deck_archive
    a=Archive(data);found=set()
    for i in range(len(a.blobs)):
        if a.key(i)[0]!=2:continue
        raw=unpack(a.blobs[i])
        if len(raw) not in (144,180) or struct.unpack_from('<HH',raw,22)!=(512,4096):continue
        chunk=a.find(3,str(uuid.UUID(bytes_le=raw[40:56])))
        if chunk is None:continue
        key=hashlib.sha256(unpack(a.blobs[chunk])).hexdigest()
        if key not in atlases:continue
        payload,sizes=mip_payload(atlases[key]);header=bytearray(raw)
        struct.pack_into('<I',header,12,20)
        struct.pack_into('<H',header,20,struct.unpack_from('<H',header,20)[0]&~8)
        header[30]=len(sizes);header[31]=0;header[32]=0;header[33]=len(sizes)
        struct.pack_into('<15I',header,56,*(sizes+[0]*(15-len(sizes))));struct.pack_into('<I',header,116,len(payload))
        a.replace(i,bytes(header))
        desc,blob=deck_archive.resource(dict(descriptor=a.descriptors[chunk].hex()),chunk,a.key(chunk)[1],payload,cas_pack,chunk_sizes=sizes,first_mip=0)
        a.descriptors[chunk]=bytearray(desc);a.blobs[chunk]=blob
        assert unpack(a.blobs[chunk])==payload
        found.add(key)
    if found!=set(atlases):raise ValueError('CD depth transport could not identify every selected artwork texture.')
    return a.bytes()

def render(renderer,angle,u,v):
    """Authored optical preview; scene lighting and mesh remain approximate."""
    x=math.sin(angle*.8);z=math.cos(angle*.8)
    r,g,b=renderer.motion;corner=g>.5;polished=r<.835
    dyed=(.2<g<.4 or g>.8) and not polished
    separate=(.2<g<.4 or g>.8) if polished else r<.875
    controls=renderer.sample(.125,4/4096)
    has_controls=.155<controls[0]<.185 and .715<controls[1]<.745
    params=renderer.sample(.375,4/4096)
    response=renderer.sample(.125,16/4096)
    active=.105<response[1]<.135 and .865<response[2]<.895
    reflection=active and .325<response[0]<.395
    diffraction=active and .365<response[0]<.435
    alpha=renderer.alpha
    def height(a,b):
        ix=np.clip(np.rint(a*512-.5).astype(int),0,511);iy=np.clip(np.rint(b*4096-.5).astype(int),0,4095)
        return alpha[iy,ix]
    av=64/4096+v*1984/4096
    depth=height(u,av)-128/255
    art_u=np.clip(u+x*depth*.035,.5/512,511.5/512)
    rgb=renderer.sample(art_u,av);art=np.sqrt(np.clip(rgb@np.array([.2126,.7152,.0722]),0,1))
    gx=(u+(.85 if corner else -.4805))*.205;gy=(v-(.5 if corner else .5434))*.794
    rad2=gx*gx+gy*gy;inv=1/np.sqrt(np.maximum(rad2,1e-6));nx=gx*inv;ny=gy*inv
    lx=.7*x+.22;ly=-.26;lz=.7*z;ln=math.sqrt(lx*lx+ly*ly+lz*lz);kx=x+lx/ln;ky=ly/ln
    axis=np.array([kx*.35,ky]);axis/=np.linalg.norm(axis)
    along=axis[0]*nx+axis[1]*ny;cross=axis[0]*ny-axis[1]*nx;band=cross*np.where(along<0,-1,1)
    wave=555+ny*350+x*600 if corner else 555+band*650+rad2/.16*80
    visibility=.55+.45*z if corner else math.exp(-((math.hypot(kx,ky)-.38)/.30)**4)
    def spectrum(wave,spread):
        channels=[]
        for mu,width in [(620,60),(535,48),(450,42)]:
            variance=width*width+spread*spread
            gain=.064*math.sqrt(math.pi)*spread*width/(5*math.sqrt(variance))
            channels.append(np.exp(-(wave-mu)**2/variance)*gain*visibility)
        return np.stack(np.broadcast_arrays(*channels),-1)
    base=spectrum(wave,18);image=spectrum(wave-85 if separate else wave,18)
    def scale(a,gain):return a*gain/np.sqrt(1+(np.max(a,axis=-1,keepdims=True)*gain)**2)
    core=np.clip((rad2-.000025)/.0012,0,1);core=core*core*(3-2*core)
    backing_marker=renderer.sample(.625,16/4096)
    stronger=.645<backing_marker[0]<.675 and .025<backing_marker[1]<.055 and backing_marker[2]>.90
    backing_gain=.50 if diffraction else (.33+.27*(1-art))[...,None] if stronger else .33
    image_gain=.55 if diffraction else .28 if stronger else .40
    rainbow=(scale(base,2.5)*backing_gain+scale(image,2.5)*art[...,None]*image_gain)*core[...,None]*.90
    ex=-x+(u-.5)*.205*.70;ey=(v-.5)*.794*1.2
    cool=np.exp(-((ex-.42)/.65)**2-((ey+.12)/.80)**2)
    warm=np.exp(-((ex+.52)/.48)**2-((ey-.25)/.65)**2)
    shadow=np.exp(-((ex+.05)/.18)**2-((ey+.08)/1.2)**2)
    reflected=(.020+.095*cool+.072*warm)*(1-.52*shadow)
    if polished:reflected=((.022 if reflection else .035)+(.38 if reflection else .28)*cool+(.29 if reflection else .23)*warm)*(1-(.91 if reflection else .82)*shadow)
    tint=(cool[...,None]*[.94,1,1.12]+warm[...,None]*[1.08,1.01,.94])/np.maximum(.05,(cool+warm)[...,None])
    if dyed:tint=tint*(np.array([.87,.97,1.09])+shadow[...,None]*[.12,-.03,.06])
    if polished:tint=np.ones_like(tint)
    result=reflected[...,None]*tint+rainbow+art[...,None]*(params[1]*.02 if has_controls else .0035)
    if has_controls:
        coat=renderer.sample(.875,16/4096)
        if .725<coat[0]<.755 and .045<coat[1]<.075:
            phase=x*.28+(u-.4805)*.52+(v-.5434)*.16+.08
            sheen=np.exp(-(phase/.05)**2)*(.5+.5*(1-z)**3)*params[2]*.1125
            result=result+sheen[...,None]*(1-np.clip(result,0,1))
        details=renderer.sample(.625,4/4096);amount=round(float(renderer.sample(.875,4/4096)[0])*4)
        radius=np.sqrt(rad2)
        footprint=max(.00015,.205/max(1,u.shape[-1])+.794/max(1,v.shape[0]))
        rim=np.exp(-((radius-(.49 if corner else .40))/(.0011+footprint*.65))**2)*details[0]*.18*(.1+.9*(1-z)**2)
        boundary=np.clip(.5+(radius-(.405 if corner else .345))/(.004+footprint),0,1);boundary=boundary*boundary*(3-2*boundary)
        result*=1-boundary[...,None]*details[1]*.14
        scratches=np.zeros_like(radius)
        for a,b,du,dv,catch in [(.18,.24,.13,.008,-.35),(.69,.37,-.055,.025,.25),(.27,.73,.09,-.004,.10),(.65,.87,.045,.009,-.15)][:amount]:
            px=(u-a)*.205;py=(v-b)*.794;dx=du*.205;dy=dv*.794
            t=np.clip((px*dx+py*dy)/(dx*dx+dy*dy),0,1)
            distance=np.sqrt((px-t*dx)**2+(py-t*dy)**2)
            scratches+=np.exp(-(distance/footprint)**2)*(.0001/footprint)*math.exp(-((x-catch)/.18)**2)
        light=rim+np.minimum(scratches,1)*details[2]*.14
        result+=light[...,None]*(1-np.clip(result,0,1))
    if not corner:
        radius=np.sqrt(rad2);hub=radius<.046;hole=radius<.017
        ring=.025+.025*z+.018*np.clip((radius-.017)/.023,0,1)
        ring=np.where(radius>.040,.14,ring)
        ring+=.08*np.exp(-((radius-.018)/.0008)**2)
        ring=np.where(hole,.028+.025*z,ring)
        result=np.where(hub[...,None],ring[...,None],result)
    return result
