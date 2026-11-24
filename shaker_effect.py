"""One-plane rigid inserts. Authored geometry fits the native 32-input contract."""
from pathlib import Path
import math,uuid
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageOps

PPM=512*.930/.216
MAX_PIECES=3
MAX_VERTICES=31
DEFAULT_RIM_MM=2/PPM*1000
MATERIAL='sdec/shaker/authoring-v1'
CONTROL_GUIDS=tuple((uuid.uuid5(uuid.NAMESPACE_URL,'sdec/rigid-shared-native/control/'+str(i)).bytes_le[:8]+bytes.fromhex('59ff5e8801001713')).hex() for i in range(6))
MARKER_GUID='0a67f618b4d2a93859ff5e8801001713'
DATA_GUIDS=tuple(tuple((uuid.uuid5(uuid.NAMESPACE_URL,f'sdec/shaker/v1/piece/{i}/{j}').bytes_le[:8]+bytes.fromhex('59ff5e8801001713')).hex() for j in range(8)) for i in range(3))

def key(guid):return bytes.fromhex(guid[:16])[::-1].hex()

def settings(value=None):
    if value is not None and not isinstance(value,dict):raise ValueError('Shaker settings must be an object.')
    c=dict(rim=True,blur=0.,pieces=[]);c.update(value or {})
    if not isinstance(c['rim'],bool):raise ValueError('Acrylic rim must be on or off.')
    if isinstance(c['blur'],bool) or not isinstance(c['blur'],(int,float)) or not math.isfinite(c['blur']) or not 0<=c['blur']<=30:raise ValueError('Background blur must be between 0 and 30 pixels.')
    if not isinstance(c['pieces'],list) or not 1<=len(c['pieces'])<=3:raise ValueError('Add one to three PNG pieces.')
    pieces=[]
    for value in c['pieces']:
        if not isinstance(value,dict):raise ValueError('Each piece needs a PNG image, size and weight.')
        p=dict(width_mm=55.,weight=1.,collision='outline',rim_mm=DEFAULT_RIM_MM,rim_strength=1.);p.update(value)
        if not isinstance(p.get('image'),str) or not p['image']:raise ValueError('Choose a PNG image for each piece.')
        if p['collision'] not in ('outline','rectangle','circle'):raise ValueError('Choose Outline, Rectangle or Circle collision.')
        for field,lo,hi in [('width_mm',10.,100.),('weight',.1,10.),('rim_mm',0.,5.),('rim_strength',0.,1.)]:
            x=p[field]
            if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or not lo<=x<=hi:raise ValueError(f'Piece {field.replace("_"," ")} must be between {lo:g} and {hi:g}.')
        pieces.append(p)
    c['pieces']=pieces;return c

def pack_bytes(data):
    data=bytes(data).ljust(63,b'\0')
    if len(data)!=63:raise ValueError('Collision outline exceeds its data budget.')
    return [[int.from_bytes(data[i+j:i+j+3],'big')/16777216 for j in (0,3,6)] for i in range(0,63,9)]

def unpack_bytes(values):
    return b''.join(round(channel*16777216).to_bytes(3,'big') for value in values for channel in value)

def prepare_piece(piece,rim=True):
    from shapely.geometry import Polygon,box,Point
    from shapely.ops import unary_union
    from shapely.geometry.polygon import orient
    with Image.open(piece['image']) as source:
        if source.format!='PNG':raise ValueError('Moving pieces must be PNG images; transparency defines their outline.')
        im=ImageOps.exif_transpose(source).convert('RGBA')
    bbox=im.getchannel('A').getbbox()
    if bbox is None:raise ValueError('The piece PNG is completely transparent.')
    im=im.crop(bbox)
    w=max(2,round(piece['width_mm']*.001*PPM));h=max(2,round(w*im.height/im.width))
    if h>222:raise ValueError('This piece is too tall at that size. Reduce its width until its height is at most 100 mm.')
    im=im.resize((w,h),Image.Resampling.LANCZOS)
    pixels=np.asarray(im.getchannel('A'))
    alpha=pixels>=min(128,int(pixels.max()))
    if not alpha.any():raise ValueError('The piece has no sufficiently opaque collision outline.')
    if piece['collision']=='rectangle':poly=box(0,0,w,h)
    elif piece['collision']=='circle':poly=Point(w/2,h/2).buffer(max(w,h)/2,quad_segs=7)
    else:
        runs=[]
        for y,row in enumerate(alpha):
            edges=np.flatnonzero(np.diff(np.pad(row.astype(np.int8),(1,1))))
            runs.extend(box(int(a),y,int(b),y+1) for a,b in zip(edges[::2],edges[1::2]))
        poly=unary_union(runs)
        if poly.geom_type=='MultiPolygon':
            largest=max(poly.geoms,key=lambda p:p.area)
            if largest.area/poly.area<.98:raise ValueError('This PNG has separate islands. Choose Rectangle collision or use one connected cutout.')
            poly=largest
        poly=Polygon(poly.exterior.coords)
    outline=poly.buffer(piece.get('rim_mm',DEFAULT_RIM_MM)*.001*PPM if rim else 0,join_style='round')
    tolerance=.35
    while True:
        simple=orient(outline.simplify(tolerance,preserve_topology=True),1)
        if len(simple.exterior.coords)-1<=MAX_VERTICES:break
        tolerance+=.15
        if tolerance>12:raise ValueError('This outline is too complicated for shaker physics. Use a simpler cutout or Rectangle collision.')
    lo,top,hi,bottom=simple.bounds
    width,height=hi-lo,bottom-top
    # The same quantized polygon is rendered, exported and used for collisions.
    points=np.asarray(simple.exterior.coords[:-1])
    quant=np.rint((points-[lo,top])/[width,height]*255).astype(np.uint8)
    quant=np.array([p for i,p in enumerate(quant) if not np.array_equal(p,quant[i-1])])
    restored=np.asarray(quant,dtype=float)/255*[width,height]+[lo,top]
    decoded=orient(Polygon(restored),1)
    if not decoded.is_valid or decoded.area<=0:raise ValueError('The outline contains detail too small for a stable collision shape. Use Rectangle collision or simplify the PNG.')
    if decoded.symmetric_difference(outline).area/outline.area>.18:raise ValueError('This outline loses too much detail at the physics limit. Use a simpler image or Rectangle collision.')
    centre=np.asarray(decoded.centroid.coords[0])
    local=(restored-centre)/PPM
    local[:,1]*=-1
    if np.linalg.norm(local,axis=1).max()>=.082:raise ValueError('The piece is too large to rotate inside the deck. Reduce its width.')
    mass=decoded.area/PPM**2/(math.pi*.026**2)*piece['weight']
    data=pack_bytes(bytes([len(quant)])+quant.tobytes())
    metadata=[width/PPM/.2,height/PPM/.2,mass/100]
    sprite=im.transform((512,256),Image.Transform.AFFINE,(1,0,float(centre[0])-256,0,1,float(centre[1])-128),Image.Resampling.BICUBIC)
    outer=Image.new('L',(2048,1024));draw=ImageDraw.Draw(outer)
    draw.polygon([((x-centre[0]+256)*4,(y-centre[1]+128)*4) for x,y in restored],fill=255)
    outer=outer.resize((512,256),Image.Resampling.LANCZOS)
    o=np.asarray(outer,dtype=float)/255;aa=np.asarray(sprite.getchannel('A'),dtype=float)/255
    gy,gx=np.gradient(np.asarray(outer.filter(ImageFilter.GaussianBlur(1.2)),dtype=float)/255)
    length=np.maximum(np.hypot(gx,gy),1e-6)
    masks=np.zeros((256,512,4),dtype=np.uint8)
    masks[:,:,0]=np.asarray(outer.filter(ImageFilter.GaussianBlur(4)))
    masks[:,:,1]=np.uint8(np.clip(o*(1-aa)*255,0,255))
    masks[:,:,2]=np.uint8(np.clip((-.5*gx/length+.5)*255,0,255))
    masks[:,:,3]=np.uint8(np.clip((-.5*gy/length+.5)*255,0,255))
    # The shared atlas is sampled as sRGB. Encode scalar RGB data accordingly:
    # otherwise a neutral bevel normal becomes negative and makes acrylic look
    # like a dark/painted outline. Alpha remains a linear scalar channel.
    linear=masks[:,:,:3].astype(float)/255
    linear[:,:,1]*=piece.get('rim_strength',1.)
    encoded=np.where(linear<=.0031308,linear*12.92,1.055*linear**(1/2.4)-.055)
    masks[:,:,:3]=np.uint8(np.rint(np.clip(encoded,0,1)*255))
    return dict(sprite=sprite,mask=Image.fromarray(masks),metadata=[metadata,*data],vertices=local.tolist(),mass=mass,width_mm=width/PPM*1000,height_mm=height/PPM*1000)

def prepare(project):
    import image_placement
    c=settings(project.get('shaker'))
    background=image_placement.frame(project['images'][0],project.get('fit','Stretch'),project.get('background','#ffffff'),(project.get('placement') or [{}])[0],alpha=False)
    if c['blur']:background=background.filter(ImageFilter.GaussianBlur(c['blur']))
    # Fill the visible native artwork bounds exactly; do not stretch/crop again.
    atlas=Image.new('RGBA',(512,4096))
    rect=(round(.031*512),round(.07715*2048),round(.961*512),round(.99512*2048))
    atlas.paste(background.resize((rect[2]-rect[0],rect[3]-rect[1]),Image.Resampling.LANCZOS),rect[:2])
    pieces=[prepare_piece(p,c['rim']) for p in c['pieces']]
    for i,p in enumerate(pieces):
        atlas.paste(p['sprite'],(0,2048+i*512));atlas.paste(p['mask'],(0,2304+i*512))
    return dict(atlas=atlas,pieces=pieces,config=c,background=background)

def parameters(prepared):
    pieces=prepared['pieces'];cfg=prepared['config']
    out=[dict(guid=g,type='colour',default=[.5,.5,0] if i<5 else [len(pieces)/5,int(cfg['rim']),0]) for i,g in enumerate(CONTROL_GUIDS)]
    out.append(dict(guid=MARKER_GUID,type='colour',default=[len(pieces)/5,int(cfg['rim']),.25]))
    for i,piece in enumerate(pieces):
        out.extend(dict(guid=g,type='colour',default=v) for g,v in zip(DATA_GUIDS[i],piece['metadata']))
    assert len(out)<=32
    return out
