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
from board_preview import map_artwork

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

def thumbnail(a,b,custom=None,fit="Stretch",background="#ffffff",size=768,label="LENTICULAR"):
    if custom:
        with Image.open(custom) as source:
            im=ImageOps.exif_transpose(source).convert('RGBA')
            return ImageOps.pad(im,(size,size),Image.Resampling.LANCZOS,color=(0,0,0,0))
    out=Image.new('RGBA',(size,size),(0,0,0,0))
    height=round(size*.79);width=height//4;top=round(size*.035);gap=round(size*.055)
    left=(size-width*2-gap)//2
    mask=Image.new('L',(width,height));ImageDraw.Draw(mask).rounded_rectangle((0,0,width-1,height-1),radius=width//2,fill=255)
    for i,path in enumerate([a,b]):
        graphic=map_artwork(artwork(path,fit,background),(width,height)).convert('RGBA')
        graphic.putalpha(mask);out.alpha_composite(graphic,(left+i*(width+gap),top))
    font_size=max(6,round(size*.061))
    try:font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',font_size)
    except OSError:font=ImageFont.load_default(size=font_size)
    ImageDraw.Draw(out).text((size//2,round(size*.915)),label,font=font,anchor='mm',fill=(255,255,255,255),stroke_width=max(1,round(size/384)),stroke_fill=(20,20,20,230))
    return out

def encode_thumbnail(im):
    import texture_compression
    return texture_compression.thumbnail(im)


def encode(im,progress=lambda message:None,*,profile='slow',mipmaps=True):
    if im.size not in [(512,4096),(1024,8192),(2048,16384)]:
        raise ValueError('Unsupported deck atlas dimensions.')
    import texture_compression
    return texture_compression.encode(im,progress,profile=profile,mipmaps=mipmaps)


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

def export_pack(projects,dest,progress=lambda message:None,*,title="Lenticular Deck Pack",author="",shared_runtime=False,_texture_only=False):
    import copy
    import tempfile
    import image_placement
    projects = copy.deepcopy(projects)
    with tempfile.TemporaryDirectory(prefix='lenticular-framing-') as scratch:
        for number, project in enumerate(projects):
            originals = project['images']
            if project.get('mode','classic')=='classic':
                extra=project.get('extra_images',[])
                if len(extra)>6:raise ValueError('Lenticular supports up to eight pictures.')
                framed=[]
                for i,path in enumerate(extra):
                    if Path(dest).resolve()==Path(path).resolve():raise ValueError('Choose a separate output file.')
                    image=image_placement.frame(path,project.get('fit','Stretch'),project.get('background','#ffffff'),{})
                    target=Path(scratch)/f'{number}-extra-{i}.png';image.save(target);framed.append(str(target))
                project['extra_images']=framed
            middle=project.get('middle_image') if project.get('mode') in ('layers','window') else None
            if Path(dest).resolve() in [Path(path).resolve() for path in [*originals,middle] if path]:
                raise ValueError('Choose a separate output file.')
            if middle:
                image=image_placement.frame(middle,project.get('fit','Stretch'),project.get('background','#ffffff'),project.get('middle_placement',{}),alpha=True)
                target=Path(scratch)/f'{number}-middle.png';image.save(target)
                project['middle_image']=str(target)
            if project.get('mode') == 'gif':
                continue
            if project.get('mode')=='ghost':
                for finish in ('silver','holo'):
                    cfg=project.get('ghost',{}).get(finish,{})
                    if cfg.get('selection')=='mask' and cfg.get('mask'):
                        if Path(dest).resolve()==Path(cfg['mask']).resolve():raise ValueError('Choose a separate output file.')
                        placement=(project.get('placement') or [{}])[0]
                        mask=image_placement.frame(cfg['mask'],project.get('fit','Stretch'),'#000000',placement,alpha=True)
                        target=Path(scratch)/f'{number}-ghost-{finish}.png';mask.save(target);cfg['mask']=str(target)
            placements = project.get('placement')
            background_fit = project.get('background_fit') if project.get('mode')=='layers' else None
            if not background_fit and (not placements or all(all(float(p.get(k,d)) == d for k,d in [('zoom',1),('x',0),('y',0)]) for p in placements)):
                continue
            placements = placements or [dict(zoom=1,x=0,y=0)]*2
            if len(placements) != 2:
                raise ValueError('Two image placements are required.')
            for index, path in enumerate(originals):
                if not path and project.get('mode') in ('metal','neon') and index==1:
                    continue
                fit = background_fit if background_fit and index==1 else project.get('fit','Stretch')
                image = image_placement.frame(path, fit, project.get('background','#ffffff'),
                    placements[index], alpha=(project.get('mode') in ('layers','window','liquid') and index==0) or (project.get('mode')=='neon' and index==1),
                    depth=project.get('mode') in ('depth','ghost','ink') and index==1)
                target = Path(scratch)/f'{number}-{index}.png'
                image.save(target)
                project['images'][index] = str(target)
            project['fit'] = 'Stretch'
        return _export_pack(projects,dest,progress,title=title,author=author,shared_runtime=shared_runtime,_texture_only=_texture_only)


def _export_pack(projects,dest,progress=lambda message:None,*,title="Lenticular Deck Pack",author="",shared_runtime=False,_texture_only=False):
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
        if mode not in ['classic','depth','layers','gif','ghost','metal','ink','window','liquid','neon']:raise ValueError('Unsupported deck mode.')
        if fit not in ['Stretch','Crop to fill','Fit entire image']:raise ValueError('Choose a supported image sizing option.')
        if dest in [Path(p).resolve() for p in [a,b,custom] if p]+[(ROOT/'engine/template.fbmod').resolve()]:raise ValueError('Choose a separate output file.')
        progress(f'Deck {number} of {len(projects)}: {name}')
        if mode=='neon':
            import advanced_atlas
            graphic=artwork(a,fit,background)
            mask=depth_views.layer_image(b,fit) if b else None
            packed=advanced_atlas.neon_pack(graphic,mask,project.get('neon'))
            texture=encode(packed,progress,mipmaps=False)
            thumb=thumbnail(graphic,graphic,custom,background=background,label='NEON')
        elif mode=='classic' and project.get('extra_images'):
            import advanced_atlas
            pictures=[artwork(path,fit,background) for path in [a,b,*project['extra_images']]]
            packed=advanced_atlas.multi_pack(pictures)
            texture=encode(packed,progress,mipmaps=False)
            thumb=thumbnail(pictures[0],pictures[-1],custom,background=background,label=f'{len(pictures)} PICTURES')
        elif mode=='liquid':
            import liquid_atlas
            from effect_preview import AtlasPreview
            packed=liquid_atlas.pack(depth_views.layer_image(a,fit),artwork(b,fit,background),project.get('liquid'))
            texture=encode(packed,progress,mipmaps=False)
            preview=AtlasPreview(packed,'liquid')
            thumb=thumbnail(preview.render(-.4,(256,1024)),preview.render(.4,(256,1024)),custom,background=background,label='LIQUID')
        elif mode in ('metal','ink','window'):
            import finish_atlas
            from effect_preview import AtlasPreview
            graphic=depth_views.layer_image(a,fit) if mode=='window' else artwork(a,fit,background)
            second=(depth_views.depth_image(b,fit) if mode=='ink' else artwork(b,fit,background)) if mode!='metal' else None
            obj=depth_views.layer_image(project['middle_image'],fit) if mode=='window' and project.get('middle_image') else None
            packed=finish_atlas.pack(mode,graphic,second,obj,ink=project.get('ink'))
            texture=encode(packed,progress,mipmaps=False)
            preview=AtlasPreview(packed,mode)
            thumb=thumbnail(preview.render(-.4,(256,1024)),preview.render(.4,(256,1024)),custom,background=background,label={'metal':'METALLIC','ink':'INK FLOW','window':'WINDOW'}[mode])
        elif mode == 'gif':
            clip=animation.load(a)
            packed,metadata=animation_texture.atlas(clip,background=background,placement=(project.get('placement') or [{}])[0],quality=project.get('animation',{}).get('quality',1))
            texture=encode(packed,progress,profile='fast',mipmaps=False)
            first=animation_texture.preview_frame(clip,0,background,(project.get('placement') or [{}])[0])
            thumb=thumbnail(first,first,custom,background=background,label='ANIMATED')
        elif mode in ['depth','layers','ghost']:
            settings=project.get('depth',{})
            if mode=='layers':
                front=depth_views.layer_image(a,fit)
                back=artwork(b,fit,background)
                strength=settings.get('strength',.08)
                motion=settings.get('convergence',.5)
                reverse=settings.get('invert',False)
                lens=settings.get('bands',.25) if project.get('lenticular',True) else 0
                if project.get('middle_image'):
                    middle=depth_views.layer_image(project['middle_image'],fit)
                    packed=layer_atlas.pack_three(front,middle,back,strength,project.get('layer_depths',(.1,.45,.9)),lens,reverse)
                    texture=encode(packed,progress,mipmaps=False)
                    from effect_preview import AtlasPreview
                    preview=AtlasPreview(packed,'layers3');views=[preview.render(a,(256,1024)) for a in (-1,1)]
                else:
                    texture=encode(layer_atlas.pack(front,back,strength,motion,lens,reverse),progress)
                    views=depth_views.layer_views(front,back,strength,motion,reverse,progress,view_count=2)
            else:
                image=artwork(a,fit,background)
                depth=depth_views.depth_image(b,fit,invert=settings.get('invert',False))
                if mode=='ghost' or not project.get('lenticular',True):
                    import smooth_effect
                    packed=smooth_effect.pack(image,depth,settings.get('strength',.075),settings.get('convergence',.5),mode=='ghost',project.get('ghost'))
                    texture=encode(packed,progress,mipmaps=False)
                    if mode=='ghost':
                        from effect_preview import AtlasPreview
                        preview=AtlasPreview(packed,'ghost');views=[preview.render(a,(256,1024)) for a in (-.4,.4)]
                    else:views=[image,image]
                else:
                    views=depth_views.views(image,depth,settings.get('strength',.04),settings.get('convergence',.5),progress)
                    texture=encode(depth_views.pack(views,settings.get('bands',1),balanced=True),progress)
            thumb=thumbnail(views[0],views[-1],custom,fit,background)
        else:
            texture=encode(atlas(a,b,fit,background),progress)
            thumb=thumbnail(a,b,custom,fit,background)
        wood=None
        if project.get('wood_tint') and not _texture_only:
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
        continuous=mode in ('ghost','metal','ink','window','liquid','neon') or (mode=='classic' and bool(project.get('extra_images'))) or (mode=='depth' and not project.get('lenticular',True)) or (mode=='layers' and bool(project.get('middle_image')))
        decks.append(dict(name=name,mode='depth' if mode=='layers' or (mode=='classic' and project.get('extra_images')) else 'classic' if mode in ('gif','ghost','metal','ink','window','liquid','neon') else mode,texture=texture,texture_size=packed.size if mode=='gif' else (512,4096),texture_mips=1 if mode=='gif' or continuous else None,resident=mode=='gif' or continuous,wood_texture=wood,thumb_small=encode_thumbnail(thumb.resize((256,256),Image.Resampling.LANCZOS)),thumb_large=encode_thumbnail(thumb)))
    if _texture_only:
        return decks
    result=deck_archive.build(decks,raw_cas,title,author.strip(),independent_shader=True)
    check_head,check_blobs=split_mod(result)
    assert len(check_blobs)==14*len(projects)+13+2*int(any(d.get('resident') for d in decks))+3*sum(bool(p.get('wood_tint')) for p in projects)
    from fbmod_compat import compatible
    progress('Applying sticker compatibility…')
    result, _ = compatible(result)
    dest.parent.mkdir(parents=True,exist_ok=True)
    if shared_runtime:
        from effects_runtime import write_content_export
        progress('Preparing SDEC deck content…')
        write_content_export(result,dest,overwrite=True)
        progress('Export complete.');return dest
    temp=dest.with_name(dest.name+'.partial');temp.write_bytes(result);temp.replace(dest)
    progress('Export complete.');return dest

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('image_a');p.add_argument('image_b');p.add_argument('output')
    p.add_argument('--name',default='Lenticular Input3 Probe');p.add_argument('--author',default='');p.add_argument('--fit',default='Stretch',choices=['Stretch','Crop to fill','Fit entire image'])
    a=p.parse_args();print(export(a.image_a,a.image_b,a.output,print,name=a.name,author=a.author,fit=a.fit))


def export_texture(project, progress=lambda message: None):
    """Prepare the exact export texture without building or writing a mod.

    Uses export's placement, view generation, packing and BC7 profile, rather
    than the faster approximate preview path. Call from a background worker.
    """
    import tempfile
    return export_pack([project], Path(tempfile.gettempdir())/'deck-preview.fbmod', progress,
                       title=project['name'], _texture_only=True)[0]
