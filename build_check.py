import json
from pathlib import Path
from PIL import Image, ImageDraw
import creator_engine as engine
import onnxruntime
from app_version import APP_VERSION
from effect_preview import AtlasPreview
import preview_depth
from updates import newer_release
from ebx_tools import Ebx


def check(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    try:
        images = []
        for index, colour in enumerate(['#276fbc','#e08e34']):
            path = folder/f'image-{index}.png'
            image = Image.new('RGB',(512,2048),colour)
            ImageDraw.Draw(image).rectangle((128,400,384,1600),fill='white')
            image.save(path)
            images.append(str(path.resolve()))
        depth = folder/'depth.png'
        Image.linear_gradient('L').resize((512,2048)).save(depth)
        projects = [dict(name='Studio Export Test',mode='classic',images=images,wood_tint='#ba3045',wood_intensity=.8,
                         placement=[dict(zoom=1.2,x=.1,y=0),dict(zoom=1,x=0,y=0)]),
                    dict(name='Studio Depth Test',mode='depth',images=[images[0],str(depth.resolve())],
                         depth=dict(strength=.04,convergence=.5,bands=.65))]
        gif = folder/'animation.gif'
        Image.new('RGB',(80,40),'red').save(gif,save_all=True,
            append_images=[Image.new('RGB',(80,40),'blue')],duration=[80,120],loop=0)
        projects.append(dict(name='Studio Animation Test',mode='gif',images=[str(gif.resolve()),None],animation=dict(quality=2)))
        from qt_check import check as check_interface
        interface = check_interface(folder, projects)
        records = []
        original = engine.deck_archive.resource
        def record(template,index,name,raw,cas,**kwargs):
            records.append((name,raw,kwargs.get('rid')))
            return original(template,index,name,raw,cas,**kwargs)
        engine.deck_archive.resource = record
        output = engine.export_pack(projects,folder/'Studio Testing Pack.fbmod')
        engine.deck_archive.resource = original
        header,blobs = engine.split_mod(output.read_bytes())
        assert len(blobs) == 61
        from fbmod_compat import Archive, compatible, unpack
        exported = output.read_bytes()
        assert compatible(exported)[0] == exported
        archive = Archive(exported)
        import struct
        count_at = archive.prefix.index(b'\0\xff\xff\xff\xffIcon') - 4
        assert struct.unpack_from('<I',archive.prefix,count_at)[0] == len(blobs)+5
        assert archive.find(2,'characters/lua/luaskateboardcompositor') is not None
        empty = archive.descriptors[archive.find(1,'characters/customization/reskate/board_bottomart/lenticular_black_rgb')]
        lua = archive.descriptors[archive.find(2,'characters/lua/luaskateboardcompositor')]
        def global_bundles(descriptor):
            _, end, _ = engine.deck_archive.descriptor_parts(descriptor)
            count = struct.unpack_from('<I',descriptor,end+1)[0]
            return struct.unpack_from('<'+str(count)+'I',descriptor,end+5)
        assert len(global_bundles(empty)) == 6
        assert global_bundles(empty) == global_bundles(lua)
        import json as _json
        assets=engine.ROOT/'assets/sticker-compat'
        for record in _json.loads((assets/'manifest.json').read_text())[:6]:
            index=archive.find(record['kind'],record['name'])
            shader=unpack(archive.blobs[index])
            _,_,tail=engine.deck_archive.descriptor_parts(archive.descriptors[index])
            assert struct.unpack_from('<I',archive.descriptors[index],tail+16)[0]==struct.unpack_from('<I',shader,16)[0]
        for i in range(len(archive.blobs)):
            kind,name = archive.key(i)
            if kind == 2 and name.endswith('_color'):
                import struct
                raw = unpack(archive.blobs[i])
                assert raw[30:34] == bytes((1,0,0,1))
                assert struct.unpack_from('<H',raw,20)[0] == 1
        assert b'items/cust_board_stickers/skateboardstickercompositetextureset\0' in header
        assert b'characters/customization/board/loaders/cas_skateboard_sticker_compositor_prefab\0' in header
        compositor=Ebx(next(raw for name,raw,rid in records if name=='items/cust_board_stickers/skateboardstickercompositetextureset'))
        import struct
        assert struct.unpack_from('<4I',compositor.data,72)==(2048,)*4
        assert struct.unpack_from('<4I',compositor.data,56)==(16384,)*4
        prefab=Ebx(next(raw for name,raw,rid in records if name=='characters/customization/board/loaders/cas_skateboard_sticker_compositor_prefab'))
        t=next(t for t in prefab.types if t['name']=='TextureCompositorEntityData')
        off=next(off for off in prefab.inst if (prefab.tg[struct.unpack_from('<H',prefab.data,off)[0]],prefab.ts[struct.unpack_from('<H',prefab.data,off)[0]])==t['id'])
        for name in ('ForceUncompressed','GenerateMipMaps'):
            f=next(f for f in prefab.fields[t['first']:t['first']+t['count']] if f['name']==name)
            assert prefab.data[off+f['off']]==0
        assert b'reskate-cosmetic-shader:v1' not in header
        assert b'reskate-cosmetic-shader-lookup:v1' not in header
        assert header.count(b'reskate-cosmetic-dependency:v1') == 5
        textures = [(name,rid) for name,raw,rid in records if rid is not None and name.startswith(('thumbnail/tool/','characters/customization/reskate/board_bottomart/'))]
        assert len(textures) == 10 and len(set(rid for _,rid in textures)) == 10
        assert all(rid&3 != 2 for _,rid in textures)
        import struct
        headers=[raw for name,raw,rid in records if len(raw)==180 and raw[:8]==bytes(8)]
        wood=next(raw for name,raw,rid in records if name.endswith('_wood') and len(raw)==180)
        assert struct.unpack_from('<H',wood,20)[0]==1
        assert struct.unpack_from('<HH',wood,22)==(1024,2048) and wood[30:34]==bytes((12,0,0,12))
        assert sum(struct.unpack_from('<15I',wood,56))==2796240
        assert any(struct.unpack_from('<HH',raw,22)==(1024,8192) and raw[30:34]==bytes((1,0,0,1)) and struct.unpack_from('<H',raw,20)[0]&8 for raw in headers)
        for name,rid in textures:
            raw = next(raw for other,raw,resource_id in records if other==name and resource_id is None and raw.startswith(b'RIFF'))
            ebx = Ebx(raw)
            assert rid in [engine.deck_archive.u64(ebx.data,offset) for offset in ebx.res]
        preview=AtlasPreview(engine.atlas(*images),'classic').render(.5,(40,160))
        assert preview.size==(40,160)
        quick_views=preview_depth.views(Image.open(images[0]),Image.open(depth),.04,.5)
        assert len(quick_views)==8 and quick_views[0].size==(252,1004)
        detail=AtlasPreview(engine.depth_views.pack(quick_views,1,balanced=True),'depth')
        assert detail.render(0,(80,80),(.375,.46875,.625,.53125)).size==(80,80)
        assert newer_release([],APP_VERSION) is None
        report = dict(ok=True,version=APP_VERSION,resources=len(blobs),unique_textures=len(textures),onnxruntime=onnxruntime.__version__,output=str(output))
        report['interface'] = interface
        smooth_projects=[dict(name=f'Packaged {mode}',mode=mode,lenticular=False,
                              images=[images[0],str(depth.resolve())],
                              depth=dict(strength=.075,convergence=.5,bands=0))
                         for mode in ('ghost','depth')]
        new_output=engine.export_pack(smooth_projects,folder/'Ghost and Smooth Pack.fbmod')
        new_archive=Archive(new_output.read_bytes())
        assert compatible(new_output.read_bytes())[0]==new_output.read_bytes()
        assert global_bundles(new_archive.descriptors[new_archive.find(1,'characters/customization/reskate/board_bottomart/lenticular_black_rgb')])==global_bundles(lua)
        report['new_modes_output']=str(new_output)
        report['new_modes_resources']=len(new_archive.blobs)
    except Exception:
        import traceback
        report = dict(ok=False,error=traceback.format_exc())
    (folder/'build-check.json').write_text(json.dumps(report,indent=2),encoding='utf8')
