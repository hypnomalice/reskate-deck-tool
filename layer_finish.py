"""Per-plane donor Pearl finish. RGB masks travel in unused atlas channels."""
import math
import numpy as np
from PIL import Image, ImageDraw

LAYERS=('foreground','middle','background')
MINIMUM_CORE='3.6.0'

def settings(value=None):
    if value is None:value={}
    if not isinstance(value,dict):raise ValueError('Layer finishes must be an object.')
    result={}
    for key in LAYERS:
        item=value.get(key,{})
        if not isinstance(item,dict):raise ValueError('Each layer finish must be an object.')
        finish=item.get('finish','normal');area=item.get('area','light')
        strength=float(item.get('strength',.85))
        if finish not in ('normal','holographic'):raise ValueError('Choose Normal or Holographic for each layer.')
        if area not in ('light','all','mask'):raise ValueError('Choose a supported holographic area.')
        if not math.isfinite(strength) or not 0<=strength<=1:raise ValueError('Layer holographic strength must be between 0 and 1.')
        mask=item.get('mask','') or ''
        if not isinstance(mask,str):raise ValueError('A layer mask must be an image path.')
        result[key]=dict(finish=finish,strength=strength,area=area,mask=mask)
    return result

def enabled(project):
    return project.get('mode')=='layers' and any(v['finish']=='holographic' and v['strength']>0
        for k,v in settings(project.get('layer_finishes')).items() if k!='middle' or project.get('middle_image'))

def prepared_masks(project):
    """Use exactly the same framing as the corresponding artwork, before export."""
    import image_placement
    masks={};positions=project.get('placement') or [{},{}]
    for key,cfg in settings(project.get('layer_finishes')).items():
        if cfg['finish']!='holographic' or cfg['area']!='mask' or not cfg['strength']:continue
        if key=='middle' and not project.get('middle_image'):continue
        if not cfg['mask']:raise ValueError('Choose a mask PNG for the '+key+' holographic finish.')
        index=1 if key=='background' else 0
        fit=project.get('background_fit') if key=='background' else None
        placement=project.get('middle_placement',{}) if key=='middle' else positions[index]
        masks[key]=image_placement.frame(cfg['mask'],fit or project.get('fit','Stretch'),'#000000',placement,alpha=True)
    return masks

def _mask(image,cfg,custom):
    from effect_preview import linear
    rgba=np.asarray(image.convert('RGBA'),dtype=np.float32)/255
    if cfg['finish']=='normal' or cfg['strength']==0:return Image.new('L',image.size)
    if cfg['area']=='mask':
        if custom is None:raise ValueError('Choose the layer mask PNG before exporting.')
        rgba_mask=np.asarray(custom.convert('RGBA').resize(image.size,Image.Resampling.LANCZOS),dtype=np.float32)/255
        amount=(rgba_mask[...,:3]*np.array([.2126,.7152,.0722])).sum(axis=2)*rgba_mask[...,3]
    elif cfg['area']=='all':amount=np.ones(rgba.shape[:2])
    else:amount=np.clip((linear(image.convert('RGB')).max(axis=2)-.004)*20,0,1)
    # Coverage is applied in the shader. This only removes finish outside the PNG.
    amount=amount*(rgba[...,3]>0)
    from layer_atlas import encode_linear
    table=np.array([encode_linear(i/255) for i in range(256)],dtype=np.uint8)
    return Image.fromarray(table[np.rint(np.clip(amount,0,1)*255).astype(np.uint8)])

def mark(atlas,images,value=None,masks=None,*,three=False):
    cfg=settings(value);keys=LAYERS if three else ('foreground','background')
    if not any(cfg[k]['finish']=='holographic' and cfg[k]['strength']>0 for k in keys):return atlas
    from layer_atlas import encode_linear
    out=atlas.copy();masks=masks or {}
    if three:
        alpha=np.asarray(out.crop((0,3072,512,4096))).copy()
        for key,(left,right) in zip(keys,((0,170),(170,341),(341,512))):
            amount=_mask(images[key],cfg[key],masks.get(key)).resize((right-left,1024),Image.Resampling.LANCZOS)
            alpha[:,left:right,2]=np.asarray(amount)
        out.paste(Image.fromarray(alpha),(0,3072))
    else:
        from depth_views import _paste_view_tile
        planes=[]
        for key in keys:
            tile=Image.new('RGB',(512,1344));amount=_mask(images[key],cfg[key],masks.get(key)).convert('RGB')
            _paste_view_tile(tile,amount,(0,0),(512,1344),0);planes.append(tile.getchannel('R'))
        out.paste(Image.merge('RGB',(out.crop((0,2752,512,4096)).getchannel('R'),*planes)),(0,2752))
    draw=ImageDraw.Draw(out)
    for key,row,tag in (('foreground',24,(.87,.21)),('middle',28,(.88,.23)),('background',40,(.86,.19))):
        strength=cfg[key]['strength'] if cfg[key]['finish']=='holographic' and key in keys else 0
        draw.rectangle((384,row,511,row+(2 if key=='middle' else 3)),fill=tuple(encode_linear(v) for v in (*tag,strength)))
    draw.rectangle((384,44,511,47),fill=tuple(encode_linear(v) for v in (.91,.31,.5 if three else .25)))
    validate_atlas(out)
    return out

def validate_atlas(atlas):
    """Recognition is sampled between rows 31/32: both must stay intact."""
    from effect_preview import linear
    expected=((1,0,1),(0,1,1),(1,1,0),(0,1,0))
    for index,reference in enumerate(expected):
        centre=(index+.5)*atlas.width/4-.5;left=math.floor(centre)
        pixels=linear(atlas.crop((left,31,left+2,33)).convert('RGB'))
        sample=pixels.mean(axis=(0,1))
        if not np.all(np.abs(sample-np.asarray(reference))<.01):
            raise ValueError('Layer finish export failed its texture recognition check; the existing export is unchanged.')

def _pearl(angle,u,v):
    """Donor palette and response curve under a fixed preview light; approximate."""
    dot=np.cos(float(angle)*1.15)
    # Two fixed small patterns stand in for the game's globally bound foil noise.
    perturb=.035*np.sin(u*23+v*37)+.02*np.sin(u*61-v*17)
    phase=np.clip((np.sin(dot+perturb)-.8)*8+.8,0,1)
    p=phase*3;first=np.floor(p).astype(int);second=np.minimum(first+1,3);mix=(p-first)[...,None]
    palette=np.array([[1,0,0],[1,.6738595,0],[0,1,.6533925],[.04481,0,1]],dtype=np.float32)
    rgb=palette[first]*(1-mix)+palette[second]*mix
    a=np.clip(phase*5,0,1);b=np.clip((1-phase)*5,0,1)
    strength=(a*b)**2*(3-2*a)*(3-2*b)*.25+.15
    return rgb*strength[...,None]

def preview(atlas,pixels,coverage,key,u,v,angle,*,three=False):
    flag=atlas.sample(.875,46/4096)
    if not (.902<flag[0]<.918 and .302<flag[1]<.318):return pixels
    row={'foreground':26,'middle':30,'background':42}[key]
    cfg=atlas.sample(.875,row/4096);strength=float(cfg[2])
    if strength<=0:return pixels
    if three:
        left,right={'foreground':(0,170),'middle':(170,341),'background':(341,512)}[key]
        mask=atlas.sample((left+.5+u*(right-left-1))/512,.75+v*.25)[...,2:3]
    else:
        channel=1 if key=='foreground' else 2
        mask=atlas.sample(u,2754/4096+v*1340/4096)[...,channel:channel+1]
    rgb=_pearl(angle,u,v);peak=np.max(rgb,axis=2,keepdims=True);tint=rgb/np.maximum(peak,.0001)
    amount=mask*strength*np.clip(peak*3,0,1)
    foil=np.minimum(np.maximum(pixels*(.12+tint*2.2)+rgb*.03*coverage,0),coverage)
    return pixels+(foil-pixels)*amount
