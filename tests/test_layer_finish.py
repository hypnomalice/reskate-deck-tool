import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import layer_atlas,layer_finish
from effect_preview import AtlasPreview

class LayerFinishTests(unittest.TestCase):
    def setUp(self):
        self.front=Image.new('RGBA',(128,512));ImageDraw.Draw(self.front).rectangle((15,170,110,340),fill='white')
        self.middle=self.front.copy();self.back=Image.new('RGB',self.front.size,'#808080')
        self.cfg={'background':dict(finish='holographic',strength=.85,area='light')}
    def test_finish_controls_preserve_bilinear_shader_recognition(self):
        for three in (False,True):
            for key in layer_finish.LAYERS:
                cfg={key:dict(finish='holographic',strength=.85)}
                if three:atlas=layer_atlas.pack_three(self.front,self.middle,self.back,finishes=cfg)
                else:atlas=layer_atlas.pack(self.front,self.back,finishes=cfg)
                layer_finish.validate_atlas(atlas)
                a=AtlasPreview(atlas,'layers3' if three else 'layers')
                for u,expected in zip((.125,.375,.625,.875),((1,0,1),(0,1,1),(1,1,0),(0,1,0))):
                    np.testing.assert_allclose(a.sample(u,32/4096),expected,atol=.01)
                if three and key=='middle':self.assertGreater(float(a.sample(.875,30/4096)[2]),.84)
        broken=layer_atlas.pack(self.front,self.back,finishes=self.cfg)
        ImageDraw.Draw(broken).rectangle((384,28,511,31),fill=(240,130,0))
        with self.assertRaisesRegex(ValueError,'recognition'):layer_finish.validate_atlas(broken)

    def test_defaults_preserve_every_atlas_pixel(self):
        old=layer_atlas.pack(self.front,self.back)
        self.assertEqual(old.tobytes(),layer_atlas.pack(self.front,self.back,finishes=layer_finish.settings()).tobytes())
    def test_validation_rejects_invalid_settings_and_missing_masks(self):
        for value in ({'foreground':{'strength':float('nan')}},{'background':{'finish':'rainbow'}},{'middle':{'area':'bad'}}):
            with self.assertRaises(ValueError):layer_finish.settings(value)
        with self.assertRaises(ValueError):layer_finish.prepared_masks(dict(mode='layers',layer_finishes={'foreground':dict(finish='holographic',area='mask')}))
    def test_two_plane_alpha_is_preserved_with_independent_masks(self):
        old=layer_atlas.pack(self.front,self.back);new=layer_atlas.pack(self.front,self.back,finishes=self.cfg)
        self.assertEqual(old.crop((0,2752,512,4096)).getchannel('R').tobytes(),new.crop((0,2752,512,4096)).getchannel('R').tobytes())
        a=AtlasPreview(new,'layers');self.assertLess(float(a.sample(.875,26/4096)[2]),.01);self.assertAlmostEqual(float(a.sample(.875,42/4096)[2]),.85,delta=.01)
        self.assertLess(float(a.sample(.5,.8)[1]),.001);self.assertGreater(float(a.sample(.5,.8)[2]),.9)
    def test_three_plane_alpha_is_preserved_and_all_masks_are_independent(self):
        cfg={key:dict(finish='holographic',area='all',strength=(i+1)/3) for i,key in enumerate(layer_finish.LAYERS)}
        old=layer_atlas.pack_three(self.front,self.middle,self.back);new=layer_atlas.pack_three(self.front,self.middle,self.back,finishes=cfg)
        self.assertTrue(np.array_equal(np.asarray(old)[3072:,:,:2],np.asarray(new)[3072:,:,:2]))
        a=AtlasPreview(new,'layers3');self.assertGreater(float(a.sample(.875,46/4096)[2]),.49)
        for row,value in ((26,1/3),(30,2/3),(42,1)):self.assertAlmostEqual(float(a.sample(.875,row/4096)[2]),value,delta=.01)
        self.assertEqual(a.render(.3).size,(210,840))
    def test_png_mask_is_independent_of_artwork_brightness(self):
        mask=Image.new('RGB',self.front.size);ImageDraw.Draw(mask).rectangle((0,0,63,511),fill='white')
        cfg={'background':dict(finish='holographic',area='mask',strength=.85)}
        a=AtlasPreview(layer_atlas.pack(self.front,self.back,finishes=cfg,finish_masks={'background':mask}),'layers')
        self.assertGreater(float(a.sample(.2,.8)[2]),.9);self.assertLess(float(a.sample(.8,.8)[2]),.01)
    def test_normal_foreground_and_zero_strength_remain_unchanged(self):
        old=layer_atlas.pack(self.front,self.back);new=layer_atlas.pack(self.front,self.back,finishes=self.cfg)
        a,b=AtlasPreview(old,'layers'),AtlasPreview(new,'layers')
        first=np.asarray(a.render(0,(128,512)));second=np.asarray(b.render(0,(128,512)))
        self.assertTrue(np.array_equal(first[220:290,35:90],second[220:290,35:90]))
        self.assertGreater(np.abs(first.astype(float)-second).max(),5)
        cfg=copy.deepcopy(self.cfg);cfg['background']['strength']=0
        self.assertEqual(layer_atlas.pack(self.front,self.back,finishes=cfg).tobytes(),old.tobytes())
    def test_masks_follow_their_own_artwork_placement(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'mask.png';im=Image.new('RGB',(64,256));ImageDraw.Draw(im).rectangle((12,70,30,110),fill='white');im.save(p)
            project=dict(mode='layers',images=[str(p),str(p)],fit='Stretch',placement=[dict(x=.2,y=.1),{}],layer_finishes={'foreground':dict(finish='holographic',area='mask',mask=str(p))})
            actual=layer_finish.prepared_masks(project)['foreground']
            import image_placement
            expected=image_placement.frame(str(p),'Stretch','#000000',project['placement'][0],alpha=True)
            self.assertEqual(actual.tobytes(),expected.tobytes())

if __name__=='__main__':unittest.main()
