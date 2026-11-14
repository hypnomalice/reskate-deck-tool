import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image,ImageDraw
import jiggle_effect,jiggle_layers,jiggle_preview
from effect_preview import AtlasPreview

class LayerTests(unittest.TestCase):
    def test_requires_clean_plate_for_cutout(self):
        with self.assertRaises(ValueError):jiggle_layers.images({'cutout_mask':'unused.png'})
        with self.assertRaises(ValueError):jiggle_layers.images({'foreground_depth':'unused.png'})

    def test_sideways_reversed_and_diagonal_attachments(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'mask.png';Image.new('L',(512,2048),255).save(path)
            art=Image.new('RGB',(512,2048),'red');depth=Image.new('L',art.size)
            for start,end in [([.15,.5],[.85,.5]),([.85,.5],[.15,.5]),([.3,.35],[.7,.65]),([.5,.8],[.5,.2])]:
                cfg=dict(mask=str(path),top_pin=start,bottom_pin=end,amount=80)
                jiggle_effect.resolved_pins(jiggle_effect.settings(cfg),Image.open(path))
                for layered in (False,True):
                    if layered:cfg.update(foreground_mask=str(path))
                    renderer=AtlasPreview(jiggle_effect.pack(art,depth,cfg),'jiggle')
                    renderer.jiggle_particles=np.array([[.6,.3,0,0],[.4,.2,0,0]])
                    for attachment in ('top','both'):
                        renderer.jiggle_attachment=attachment
                        fast=renderer.render(.2,(64,256),view_pose=(15,0))
                        with patch.object(jiggle_preview,'_render',None):slow=renderer.render(.2,(64,256),view_pose=(15,0))
                        np.testing.assert_allclose(np.asarray(fast),np.asarray(slow),atol=2)
                        u,v=jiggle_effect.warp(renderer,.5,.5,renderer.jiggle_particles,attachment)
                        self.assertGreater(abs(float(u)-.5)+abs(float(v)-.5),.001)

    def test_fixed_foreground_and_native_parity(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            art=Image.new('RGB',(512,2048),'green');ImageDraw.Draw(art).ellipse((100,900,410,1300),fill='red');ImageDraw.Draw(art).rectangle((0,1050,511,1120),fill='blue')
            mask=Image.new('L',art.size);ImageDraw.Draw(mask).ellipse((80,870,430,1340),fill=255)
            front=Image.new('L',art.size);ImageDraw.Draw(front).rectangle((0,1050,511,1120),fill=255)
            cfg={'amount':80,'attachment':'both','depth_strength':.2}
            for key,img in [('mask',mask),('cutout_mask',mask),('foreground_mask',front),('background_image',Image.new('RGB',art.size,'green'))]:
                file=root/(key+'.png');img.save(file);cfg[key]=str(file)
            atlas=jiggle_effect.pack(art,Image.new('L',art.size,150),cfg)
            automatic=dict(cfg);automatic.pop('cutout_mask')
            self.assertEqual(atlas.tobytes(),jiggle_effect.pack(art,Image.new('L',art.size,150),automatic).tobytes())
            self.assertEqual(atlas.size,(2048,4096))
            renderer=AtlasPreview(atlas,'jiggle');renderer.jiggle_particles=np.array([[.6,.2,0,0],[-.4,-.2,0,0]])
            for attachment in ('top','both'):
                renderer.jiggle_attachment=attachment
                for pose in ((0,0),(20,5),(-25,-5)):
                    fast=renderer.render(.3,(128,512),view_pose=pose)
                    with patch.object(jiggle_preview,'_render',None):slow=renderer.render(.3,(128,512),view_pose=pose)
                    delta=np.abs(np.asarray(fast).astype(int)-np.asarray(slow).astype(int))
                    self.assertLessEqual(delta.max(),5);self.assertLess(delta.mean(),.1)
            renderer.motion[0]=0
            result=np.asarray(renderer.render(0,(256,1024),view_pose=(0,0)))
            self.assertGreater(result[540,128,2],240)
            self.assertLess(result[540,128,0],5)

if __name__=='__main__':unittest.main()
