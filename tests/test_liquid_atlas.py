import unittest
import numpy as np
from PIL import Image
import liquid_atlas
from effect_preview import AtlasPreview


class LiquidAtlasTests(unittest.TestCase):
    def setUp(self):
        self.front=Image.new('RGBA',(64,256),(255,255,255,0))
        self.back=Image.new('RGB',(64,256),'white')

    def test_alpha_settings_roundtrip(self):
        self.front.paste((255,0,0,128),(20,90,40,160))
        atlas=liquid_atlas.pack(self.front,self.back,dict(amount=.8,cloudiness=.4,depth=.12,thickness=.7))
        view=AtlasPreview(atlas,'liquid')
        cfg=view.sample(.625,56/4096)
        np.testing.assert_allclose(cfg,[.4,(.12-.025)/.155,.8],atol=.006)
        self.assertAlmostEqual(float(view.sample(.875,56/4096)[0]),.7,delta=.006)
        self.assertAlmostEqual(float(view.sample(.5,.75+.5*.25)[0]),128/255,delta=.006)
        self.assertEqual(float(view.sample(.01,.75+.5*.25)[0]),0)

    def test_empty_full_and_colour_differ(self):
        a=AtlasPreview(liquid_atlas.pack(self.front,self.back,dict(amount=0)),'liquid').render(.5,(48,192))
        b=AtlasPreview(liquid_atlas.pack(self.front,self.back,dict(amount=1)),'liquid').render(.5,(48,192))
        self.assertGreater(np.abs(np.asarray(a,dtype=float)-np.asarray(b,dtype=float)).mean(),20)

    def test_front_stays_opaque(self):
        self.front.paste((255,20,20,255),(0,0,64,256))
        a=AtlasPreview(liquid_atlas.pack(self.front,self.back,dict(amount=0)),'liquid').render(-.8,(48,192))
        b=AtlasPreview(liquid_atlas.pack(self.front,self.back,dict(amount=1,colour='#00ff00',cloudiness=1)),'liquid').render(.8,(48,192))
        np.testing.assert_array_equal(a,b)

    def test_amount_fills_upwards_at_every_camera_angle(self):
        for amount in (.25,.5,.75):
            view=AtlasPreview(liquid_atlas.pack(self.front,self.back,dict(amount=amount,cloudiness=0)),'liquid')
            for angle in (-1,0,1):
                pixels=np.asarray(view.render(angle,(64,256)),dtype=float)
                top=pixels[int((1-amount)*256)-12,32]
                bottom=pixels[min(255,int((1-amount)*256)+12),32]
                self.assertLess(max(top)-min(top),5)
                self.assertGreater(bottom[2]-bottom[1],20)

    def test_depth_has_a_visible_cap(self):
        small=AtlasPreview(liquid_atlas.pack(self.front,self.back,dict(depth=.025)),'liquid').render(.8,(96,384))
        deep=AtlasPreview(liquid_atlas.pack(self.front,self.back,dict(depth=.18)),'liquid').render(.8,(96,384))
        delta=np.abs(np.asarray(small,dtype=float)-np.asarray(deep,dtype=float))
        self.assertGreater(delta[175:193,20:76].mean(),3)

    def test_reject_invalid_settings(self):
        for key,value in [('amount',-1),('cloudiness',2),('depth',0),('thickness',float('nan'))]:
            with self.assertRaises(ValueError):liquid_atlas.settings({key:value})


if __name__=='__main__':unittest.main()
