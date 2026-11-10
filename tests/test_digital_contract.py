import unittest
import numpy as np
from PIL import Image
import digital_finish, case_finish, surface_finish
from effect_preview import AtlasPreview


class DigitalContractTests(unittest.TestCase):
    def test_control_strips_preserve_bilinear_native_signature(self):
        image=Image.new('RGB',(512,1984),'white')
        for mode in ('eink','case'):
            atlas=digital_finish.pack(mode,image,image) if mode=='eink' else case_finish.pack(image)
            for sheen in (False,True):
                with self.subTest(mode=mode,sheen=sheen):
                    marked=surface_finish.mark(atlas,dict(shimmer=sheen,strength=.8),mode=mode)
                    p=AtlasPreview(marked,mode)
                    for x,expected in zip((.125,.375,.625,.875),((1,0,1),(0,1,1),(1,1,0),(0,1,0))):
                        self.assertTrue(np.allclose(p.sample(x,32/4096),expected,atol=.008))
                    for y in (11,15,19,23,27):
                        self.assertEqual(marked.getpixel((448,y)),atlas.getpixel((448,y)))
                    if mode=='eink':
                        self.assertTrue(np.allclose(p.sample(.875,23/4096),(.18,.54,.82),atol=.008))
