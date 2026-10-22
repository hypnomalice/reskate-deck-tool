import unittest
import numpy as np
from PIL import Image
import finish_atlas
from effect_preview import AtlasPreview

class FinishAtlasTests(unittest.TestCase):
    def test_finish_markers_and_linear_mask(self):
        image=Image.new('RGB',(32,128),'white')
        for mode,marker in [('metal',32),('ink',64),('window',180)]:
            a=finish_atlas.pack(mode,image,image)
            self.assertEqual(a.size,(512,4096))
            self.assertEqual(a.getpixel((20,56)),(marker,128,255))
        a=finish_atlas.pack('ink',image,Image.new('L',image.size,128))
        self.assertTrue(187<=a.getpixel((100,3000))[0]<=189)

    def test_window_keeps_front_and_object_masks_separate(self):
        front=Image.new('RGBA',(32,128),(255,0,0,0))
        obj=Image.new('RGBA',front.size,(0,255,0,255))
        a=finish_atlas.pack('window',front,Image.new('RGB',front.size,'blue'),obj)
        self.assertEqual(a.getpixel((100,3500)),(0,255,0))
        result=AtlasPreview(a,'window').render(0,(32,128))
        self.assertEqual(result.getpixel((16,64)),(0,255,0))

    def test_metal_has_sparse_fixed_flakes_and_angle_change(self):
        a=finish_atlas.pack('metal',Image.new('RGB',(32,128),'#303030'))
        density=(np.asarray(a)[2048:,:,0]>0).mean()
        self.assertTrue(.035<density<.045,density)
        p=AtlasPreview(a,'metal')
        self.assertFalse(np.array_equal(p.render(-.5,(128,512)),p.render(.5,(128,512))))

    def test_liquid_is_not_an_authoring_mode(self):
        with self.assertRaises(ValueError):finish_atlas.pack('liquid',Image.new('RGB',(1,1)))
