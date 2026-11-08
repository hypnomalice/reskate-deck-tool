import unittest
import numpy as np
from PIL import Image
import digital_finish,case_finish,surface_finish
from effect_preview import AtlasPreview

class ReleaseTests(unittest.TestCase):
    def test_holo_explicit_and_separate_from_sheen(self):
        image=Image.new('RGB',(512,4096),'#345678')
        self.assertIs(surface_finish.mark(image,{}),image)
        atlas=surface_finish.mark(image,dict(holographic=True,holo_strength=.8))
        self.assertEqual(image.crop((0,64,512,4096)).tobytes(),atlas.crop((0,64,512,4096)).tobytes())
        p=AtlasPreview(atlas,'smooth');m=p.sample(.875,39/4096)
        self.assertAlmostEqual(float(m[2]),.8,places=2)
        self.assertGreater(float(m[0]),.82)

    def test_palette_modes_encode_without_changing_art(self):
        image=Image.new('RGB',(512,1984),'#715382')
        values=[]
        for mode in ('rgb','one','two'):
            atlas=digital_finish.pack('glitch',image,cfg=dict(colour_mode=mode,colour1='#ff0000',colour2='#0000ff'))
            p=AtlasPreview(atlas,'glitch');values.append(float(p.sample(.875,35/4096)[1]))
            np.testing.assert_allclose(p.sample(.875,43/4096),(1,0,0),atol=.01)
        np.testing.assert_allclose(values,(0,.5,1),atol=.01)

    def test_shell_finishes_and_tint_render_differently(self):
        image=Image.new('RGB',(512,1984),'#36704a')
        a=AtlasPreview(case_finish.pack(image,dict(finish='frosted',tint='#eeeeee')),'case').render(.3,(32,128))
        b=AtlasPreview(case_finish.pack(image,dict(finish='glossy',tint='#7777ff',tint_strength=.8)),'case').render(.3,(32,128))
        self.assertNotEqual(a.tobytes(),b.tobytes())
