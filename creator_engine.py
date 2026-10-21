from pathlib import Path
import sys
import struct
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageStat, ImageColor
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'engine'))
import ispc_texcomp as tc
import deck_archive
import depth_views
import layer_atlas
import animation
import animation_texture

def artwork(path, fit="Stretch", background="#ffffff"):
    if isinstance(path,Image.Image):return path.convert('RGB').resize((512,2048),Image.Resampling.LANCZOS)
    with Image.open(path) as source:
        im=ImageOps.exif_transpose(source).convert('RGBA')
        bg=Image.new('RGBA',im.size,background);bg.alpha_composite(im)
        im=bg.convert('RGB')
        if fit=='Crop to fill':return ImageOps.fit(im,(512,2048),Image.Resampling.LANCZOS)
        if fit=='Fit entire image':return ImageOps.pad(im,(512,2048),Image.Resampling.LANCZOS,color=background)
        return im.resize((512,2048),Image.Resampling.LANCZOS)

def atlas(a,b,fit="Stretch",background="#ffffff"):
    im=Image.new('RGB',(512,4096))
    im.paste(artwork(a,fit,background).resize((512,1984),Image.Resampling.LANCZOS),(0,64))
    im.paste(artwork(b,fit,background),(0,2048))
    # The shader reads this strip to recognise our decks, then hides it.
    for x,color in enumerate([(255,0,255),(0,255,255),(255,255,0),(0,255,0)]):
        ImageDraw.Draw(im).rectangle((x*128,0,x*128+127,63),fill=color)
    return im

def thumbnail(a,b,custom=None,fit="Stretch",background="#ffffff",size=768,label="LENTICULAR",shape=None):
    if custom:
        with Image.open(custom) as source:
            im=ImageOps.exif_transpose(source).convert('RGBA')
            return ImageOps.pad(im,(size,size),Image.Resampling.LANCZOS,color=(0,0,0,0))
    out=Image.new('RGBA',(size,size),(0,0,0,0))
    height=round(size*.79);width=height//4;top=round(size*.035);gap=round(size*.055)
    left=(size-width*2-gap)//2
    if shape is not None:mask=shape.mask_at((width,height))
    else:mask=Image.new('L',(width,height));ImageDraw.Draw(mask).rounded_rectangle((0,0,width-1,height-1),radius=width//2,fill=255)
    for i,path in enumerate([a,b]):
        graphic=artwork(path,fit,background).resize((width,height),Image.Resampling.LANCZOS).convert('RGBA')
        graphic.putalpha(mask);out.alpha_composite(graphic,(left+i*(width+gap),top))
    font_size=max(6,round(size*.061))
    try:font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',font_size)
    except OSError:font=ImageFont.load_default(size=font_size)
    ImageDraw.Draw(out).text((size//2,round(size*.915)),label,font=font,anchor='mm',fill=(255,255,255,255),stroke_width=max(1,round(size/384)),stroke_fill=(20,20,20,230))
    return out

def encode_thumbnail(im):
    im=im.convert('RGBA')
    return tc.compress_blocks_bc7(tc.RGBASurface(im.tobytes(),im.width,im.height,im.width*4),tc.BC7EncSettings.from_profile('alpha_basic'))

def encode(im,progress=lambda message:None,*,profile='slow',mipmaps=True):
    im=im.convert('RGBA');parts=[]
    settings=tc.BC7EncSettings.from_profile(profile)
    width,height=im.size
    if (width,height) not in [(512,4096),(1024,8192),(2048,16384)]:
        raise ValueError('Unsupported deck atlas dimensions.')
    levels=max(width,height).bit_length()-1 if mipmaps else 1
    total=sum(max(1,((width>>n)+3)//4)*max(1,((height>>n)+3)//4)*16 for n in range(levels))
    completed=0
    for level in range(levels):
        progress(f'Preparing texture detail {level+1} of {levels}…')
        w=max(1,width>>level);h=max(1,height>>level)
        mip=im.resize((w,h),Image.Resampling.LANCZOS) if level else im
        if w<4 or h<4:
            pad=Image.new('RGBA',(max(4,w),max(4,h)))
            for y in range(pad.height):
                for x in range(pad.width):pad.putpixel((x,y),mip.getpixel((min(x,w-1),min(y,h-1))))
            mip=pad
        strips=[]
        for y in range(0,mip.height,256):
            strip=mip.crop((0,y,mip.width,min(y+256,mip.height)))
            compressed=tc.compress_blocks_bc7(tc.RGBASurface(strip.tobytes(),strip.width,strip.height,strip.width*4),settings)
            strips.append(compressed)
            completed+=len(compressed)
            progress(f'Compressing texture: {completed/total:.0%} (detail {level+1}/{levels})')
        data=b''.join(strips)
        assert len(data)==max(1,(w+3)//4)*max(1,(h+3)//4)*16
        parts.append(data)
    result=b''.join(parts)
    assert len(result)==sum(max(1,((width>>n)+3)//4)*max(1,((height>>n)+3)//4)*16 for n in range(levels))
    return result

def split_mod(b):
    table,count=struct.unpack_from('<QI',b,12)
    assert table>=24 and table+count*16<=len(b)
    head=bytearray(b[:table]);payload=b[table+count*16:]
    blobs=[payload[o:o+n] for i in range(count) for o,n in [struct.unpack_from('<QQ',b,table+i*16)]]
    return head,blobs

def raw_cas(data):
    return b''.join(struct.pack('>IHH',len(c),0,len(c))+c for o in range(0,len(data),32768) for c in [data[o:o+32768]])

def validate_name(name):
    name=' '.join(str(name).split())
    if not name or len(name)>48:raise ValueError('Deck name must contain 1-48 characters.')
    if any(ch in name for ch in '/\\|\0'):raise ValueError('Deck name cannot contain /, \\, or |.')
    return name

def rename_item(raw,name):
    token=('Own_'+name.replace(' ','_')).encode('utf8')+b'\0'
    old=b'Own_Lenticular_Input3_Probe\0'
    at=12;chunks=[];changes=0
    assert raw[:4]==b'RIFF' and raw[8:12]==b'EBX\0'
    while at<len(raw):
        key=raw[at:at+4];n=struct.unpack_from('<I',raw,at+4)[0];data=bytearray(raw[at+8:at+8+n]);at+=8+n+(n&1)
        if key==b'EBXD':
            target=data.index(old)
            fields=[o for o in range(0,target-7,4) if o+struct.unpack_from('<q',data,o)[0]==target]
            assert len(fields)==1,('Unexpected title string references',fields)
            def key_hash(value):
                result=5381
                for byte in value:result=((result*33)^byte)&0xffffffff
                return result
            hash_at=fields[0]+16
            assert struct.unpack_from('<I',data,hash_at)[0]==key_hash(old[:-1]),'Item key/hash mismatch'
            if len(token)<=len(old):
                data[target:target+len(old)]=token+bytes(len(old)-len(token))
            else:
                while len(data)%8:data.append(0)
                new=len(data);data.extend(token)
                struct.pack_into('<q',data,fields[0],new-fields[0])
            struct.pack_into('<I',data,hash_at,key_hash(token[:-1]));changes+=1
        chunks.append(key+struct.pack('<I',len(data))+data+bytes(len(data)&1))
    assert changes==1 and at==len(raw)
    body=b'EBX\0'+b''.join(chunks)
    return b'RIFF'+struct.pack('<I',len(body))+body

def export(a,b,dest,progress=lambda message:None,*,name="My Lenticular Deck",author="",fit="Stretch",background="#ffffff",thumbnail_path=None):
    return export_pack([dict(images=[str(a),str(b)],name=name,author=author,fit=fit,background=background,thumbnail=thumbnail_path)],dest,progress,title=name,author=author)

def export_pack(projects,dest,progress=lambda message:None,*,title="Lenticular Deck Pack",author="",shared_runtime=False):
    import copy
    import tempfile
    import image_placement
    import deck_shape
    projects = copy.deepcopy(projects)
    with tempfile.TemporaryDirectory(prefix='lenticular-framing-') as scratch:
        for number, project in enumerate(projects):
            originals = project['images']
            if Path(dest).resolve() in [Path(path).resolve() for path in originals if path]:
                raise ValueError('Choose a separate output file.')
            if project.get('mode') == 'gif':
                continue
            placements = project.get('placement')
            background_fit = project.get('background_fit') if project.get('mode')=='layers' else None
            shaped = deck_shape.placement(project)['region'] is not None
            if not background_fit and not shaped and (not placements or all(all(float(p.get(k,d)) == d for k,d in [('zoom',1),('x',0),('y',0)]) for p in placements)):
                continue
            placements = placements or [dict(zoom=1,x=0,y=0)]*2
            if len(placements) != 2:
                raise ValueError('Two image placements are required.')
            for index, path in enumerate(originals):
                fit = background_fit if background_fit and index==1 else project.get('fit','Stretch')
                image = image_placement.frame(path, fit, project.get('background','#ffffff'),
                    placements[index], alpha=project.get('mode')=='layers' and index==0,
                    depth=project.get('mode') in ('depth','ghost') and index==1,
                    **deck_shape.placement(project, index))
                target = Path(scratch)/f'{number}-{index}.png'
                image.save(target)
                project['images'][index] = str(target)
            project['fit'] = 'Stretch'
        return _export_pack(projects,dest,progress,title=title,author=author,shared_runtime=shared_runtime)


def _export_pack(projects,dest,progress=lambda message:None,*,title="Lenticular Deck Pack",author="",shared_runtime=False):
    dest=Path(dest).resolve()
    if dest.suffix.lower()!='.fbmod':raise ValueError('Choose an .fbmod output file.')
    if not projects:raise ValueError('Add at least one deck to the pack.')
    title=validate_name(title)
    if '\0' in author:raise ValueError('Author cannot contain a null character.')
    names=set();decks=[]
    for number,project in enumerate(projects,1):
        name=validate_name(project['name'])
        if name.casefold() in names:raise ValueError('Every deck in a pack needs a different name.')
        names.add(name.casefold())
        a,b=project['images'];fit=project.get('fit','Stretch');background=project.get('background','#ffffff');custom=project.get('thumbnail')
        mode=project.get('mode','classic')
        import deck_shape
        shape=deck_shape.for_deck(project)
        region=deck_shape.placement(project)['region'] if mode=='gif' else None
        if mode not in ['classic','depth','layers','gif','ghost']:raise ValueError('Unsupported deck mode.')
        if fit not in ['Stretch','Crop to fill','Fit entire image']:raise ValueError('Choose a supported image sizing option.')
        if dest in [Path(p).resolve() for p in [a,b,custom] if p]+[(ROOT/'engine/template.fbmod').resolve()]:raise ValueError('Choose a separate output file.')
        progress(f'Deck {number} of {len(projects)}: {name}')
        if mode == 'gif':
            clip=animation.load(a)
            packed,metadata=animation_texture.atlas(clip,background=background,placement=(project.get('placement') or [{}])[0],quality=project.get('animation',{}).get('quality',1),region=region)
            texture=encode(packed,progress,profile='fast',mipmaps=False)
            first=animation_texture.preview_frame(clip,0,background,(project.get('placement') or [{}])[0],region)
            thumb=thumbnail(first,first,custom,background=background,label='ANIMATED',shape=shape)
        elif mode in ['depth','layers','ghost']:
            settings=project.get('depth',{})
            if mode=='layers':
                front=depth_views.layer_image(a,fit)
                back=artwork(b,fit,background)
                strength=settings.get('strength',.08)
                motion=settings.get('convergence',.5)
                reverse=settings.get('invert',False)
                texture=encode(layer_atlas.pack(front,back,strength,motion,settings.get('bands',.25) if project.get('lenticular',True) else 0,reverse),progress)
                views=depth_views.layer_views(front,back,strength,motion,reverse,progress,view_count=2)
            else:
                image=artwork(a,fit,background)
                depth=depth_views.depth_image(b,fit,invert=settings.get('invert',False))
                if mode=='ghost' or not project.get('lenticular',True):
                    import smooth_effect
                    packed=smooth_effect.pack(image,depth,settings.get('strength',.075),settings.get('convergence',.5),mode=='ghost')
                    texture=encode(packed,progress,mipmaps=False)
                    views=[image,image]
                else:
                    views=depth_views.views(image,depth,settings.get('strength',.04),settings.get('convergence',.5),progress)
                    texture=encode(depth_views.pack(views,settings.get('bands',1),balanced=True),progress)
            thumb=thumbnail(views[0],views[-1],custom,fit,background,shape=shape)
        else:
            texture=encode(atlas(a,b,fit,background),progress)
            thumb=thumbnail(a,b,custom,fit,background,shape=shape)
        wood=None
        if project.get('wood_tint'):
            import math
            colour=ImageColor.getrgb(project['wood_tint'])
            intensity=float(project.get('wood_intensity',1))
            if len(colour)!=3 or not math.isfinite(intensity) or not 0<=intensity<=2:
                raise ValueError('Wood intensity must be between 0 and 200%.')
            grain=Image.open(deck_archive.ROOT.parent/'assets/board-wood.png').convert('L')
            average=max(1,ImageStat.Stat(grain).mean[0])
            tinted=Image.merge('RGB',tuple(grain.point([min(255,round(value/average*channel*intensity)) for value in range(256)]) for channel in colour))
            progress('Preparing wood colour texture…')
            wood=b''.join(encode_thumbnail(tinted.resize((max(4,1024>>level),max(4,2048>>level)),Image.Resampling.LANCZOS)) for level in range(12))
        continuous=mode=='ghost' or (mode=='depth' and not project.get('lenticular',True))
        decks.append(dict(name=name,mode='depth' if mode=='layers' else 'classic' if mode in ('gif','ghost') else mode,texture=texture,texture_size=packed.size if mode=='gif' else (512,4096),texture_mips=1 if mode=='gif' or continuous else None,resident=mode=='gif' or continuous,wood_texture=wood,thumb_small=encode_thumbnail(thumb.resize((256,256),Image.Resampling.LANCZOS)),thumb_large=encode_thumbnail(thumb)))
    result=deck_archive.build(decks,raw_cas,title,author.strip(),independent_shader=True)
    check_head,check_blobs=split_mod(result)
    assert len(check_blobs)==14*len(projects)+13+2*int(any(d.get('resident') for d in decks))+3*sum(bool(p.get('wood_tint')) for p in projects)
    from fbmod_compat import compatible
    progress('Applying sticker compatibility…')
    result, _ = compatible(result)
    dest.parent.mkdir(parents=True,exist_ok=True)
    if shared_runtime:
        from effects_runtime import write_runtime_export
        progress('Separating artwork from the shared effects runtime…')
        write_runtime_export(result,dest,overwrite=True)
        progress('Export complete.');return dest
    temp=dest.with_name(dest.name+'.partial');temp.write_bytes(result);temp.replace(dest)
    progress('Export complete.');return dest

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('image_a');p.add_argument('image_b');p.add_argument('output')
    p.add_argument('--name',default='Lenticular Input3 Probe');p.add_argument('--author',default='');p.add_argument('--fit',default='Stretch',choices=['Stretch','Crop to fill','Fit entire image'])
    a=p.parse_args();print(export(a.image_a,a.image_b,a.output,print,name=a.name,author=a.author,fit=a.fit))
