import math,tempfile,unittest
from pathlib import Path
from PIL import Image
import numpy as np
import image_placement,animation,animation_texture

class ArtworkTransformTests(unittest.TestCase):
    def test_rotation_is_clockwise_and_source_is_unchanged(self):
        image=Image.new('RGB',(100,100),'black');image.paste('red',(65,40,85,60));original=image.tobytes()
        result=image_placement.frame(image,'Stretch','#000000',{'rotation':90},size=(100,100))
        self.assertGreater(result.getpixel((50,75))[0],200)
        self.assertEqual(image.tobytes(),original)

    def test_art_and_depth_geometry_stays_aligned(self):
        source=Image.new('L',(100,160),0);source.paste(255,(25,40,70,110))
        settings=dict(zoom=1.45,x=.2,y=-.15,rotation=-37)
        art=image_placement.frame(source.convert('RGB'),'Fit entire image','#000000',settings,size=(100,400))
        depth=image_placement.frame(source,'Fit entire image','#000000',settings,depth=True,size=(100,400))
        a=np.asarray(art)[:,:,0]>200;b=np.asarray(depth)>200
        self.assertGreater(np.count_nonzero(a&b)/np.count_nonzero(a|b),.98)

    def test_extreme_transform_stays_output_sized(self):
        image=Image.new('RGB',(64,256),'red')
        for cfg in [dict(zoom=.01,x=5,y=-5,rotation=360),dict(zoom=20,rotation=137)]:
            self.assertEqual(image_placement.frame(image,placement=cfg,size=(80,320)).size,(80,320))
        for cfg in [dict(zoom=21),dict(rotation=361),dict(x=6),dict(rotation=float('nan'))]:
            with self.assertRaises(ValueError):image_placement.frame(image,placement=cfg)

    def test_rotated_animation_export_and_preview_match_placement(self):
        frame=Image.new('RGBA',(64,128),'red');clip=animation.Animation((frame,),(100,),0)
        settings=dict(zoom=2,x=.1,y=-.1,rotation=90)
        preview=clip.board_frame(0,placement=settings)
        atlas,meta=animation_texture.atlas(clip,placement=settings,background='#000000')
        self.assertGreater(meta['board_w'],meta['board_h'])
        self.assertEqual(preview.size,(512,2048))
        self.assertLessEqual(atlas.width,2048)

    def test_preview_memory_budget_preserves_logical_size_and_original(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'sample.gif'
            a=Image.new('RGB',(800,1600),'red');b=Image.new('RGB',a.size,'blue')
            a.save(path,save_all=True,append_images=[b],duration=100,loop=0)
            original=path.read_bytes()
            full=animation.load(path);small=animation.load(path,preview_max_pixels=40_000)
            self.assertEqual(full.source_size,None);self.assertEqual(small.source_size,(800,1600))
            self.assertLessEqual(sum(f.width*f.height for f in small.frames),41_000)
            expected=animation_texture.preview_frame(full,0,'#000000',{},size=(100,400))
            actual=animation_texture.preview_frame(small,0,'#000000',{},size=(100,400))
            self.assertLess(np.abs(np.asarray(expected).astype(float)-np.asarray(actual)).mean(),1)
            self.assertEqual(path.read_bytes(),original)
