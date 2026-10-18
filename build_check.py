import json
from pathlib import Path
from PIL import Image, ImageDraw
import creator_engine as engine
import onnxruntime
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
        projects = [dict(name='Studio Export Test',mode='classic',images=images,
                         placement=[dict(zoom=1.2,x=.1,y=0),dict(zoom=1,x=0,y=0)]),
                    dict(name='Studio Depth Test',mode='depth',images=[images[0],str(depth.resolve())],
                         depth=dict(strength=.04,convergence=.5,bands=.65))]
        records = []
        original = engine.deck_archive.resource
        def record(template,index,name,raw,cas,**kwargs):
            records.append((name,raw,kwargs.get('rid')))
            return original(template,index,name,raw,cas,**kwargs)
        engine.deck_archive.resource = record
        output = engine.export_pack(projects,folder/'Studio Testing Pack.fbmod')
        engine.deck_archive.resource = original
        header,blobs = engine.split_mod(output.read_bytes())
        assert len(blobs) == 41
        assert b'reskate-cosmetic-shader:v1' not in header
        assert b'reskate-cosmetic-shader-lookup:v1' not in header
        assert header.count(b'reskate-cosmetic-dependency:v1') == 4
        textures = [(name,rid) for name,raw,rid in records if rid is not None and name.startswith(('thumbnail/tool/','characters/customization/reskate/board_bottomart/'))]
        assert len(textures) == 6 and len(set(rid for _,rid in textures)) == 6
        assert all(rid&3 != 2 for _,rid in textures)
        for name,rid in textures:
            raw = next(raw for other,raw,resource_id in records if other==name and resource_id is None and raw.startswith(b'RIFF'))
            ebx = Ebx(raw)
            assert rid in [engine.deck_archive.u64(ebx.data,offset) for offset in ebx.res]
        report = dict(ok=True,resources=len(blobs),unique_textures=len(textures),onnxruntime=onnxruntime.__version__,output=str(output))
    except Exception:
        import traceback
        report = dict(ok=False,error=traceback.format_exc())
    (folder/'build-check.json').write_text(json.dumps(report,indent=2),encoding='utf8')
