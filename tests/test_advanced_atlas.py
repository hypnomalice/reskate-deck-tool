import tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
import advanced_atlas
from effect_preview import AtlasPreview

class AdvancedTests(unittest.TestCase):
    def test_mask_preserves_black_and_scales_linear_colour(self):
        art=Image.new('RGB',(3,1),(0,200,255))
        mask=Image.new('RGBA',(3,1));mask.putdata([(255,255,255,255),(255,255,255,0),(128,128,128,255)])
        glow=np.array(advanced_atlas.glow_image(art,mask))
        self.assertTrue(np.array_equal(glow[0,0],np.array(art)[0,0]))
        self.assertEqual(glow[0,1].sum(),0)
        self.assertTrue(0<glow[0,2,2]<glow[0,0,2])
    def test_colour_selection_excludes_unrelated_pixels(self):
        art=Image.new('RGB',(2,1));art.putdata([(0,223,255),(255,0,0)])
        glow=np.array(advanced_atlas.glow_image(art,settings=dict(selection='colour',colour='#00dfff',tolerance=.02)))
        self.assertEqual(glow[0,1].sum(),0);self.assertGreater(glow[0,0].sum(),0)
    def test_neon_brightness_header_and_colour_preview(self):
        art=Image.new('RGB',(512,2048),'cyan');mask=Image.new('L',art.size,255)
        atlas=advanced_atlas.neon_pack(art,mask,dict(brightness=1))
        self.assertEqual(atlas.getpixel((12,56)),(96,32,224))
        self.assertEqual(atlas.getpixel((160,56)),(255,0,0))
        self.assertEqual(AtlasPreview(atlas,'neon').render(0,(40,160)).size,(40,160))
    def test_all_multi_picture_counts_and_limits(self):
        images=[Image.new('RGB',(512,2048),(i*30,255-i*30,40)) for i in range(8)]
        for n in range(2,9):
            atlas=advanced_atlas.multi_pack(images[:n]);preview=AtlasPreview(atlas,'multi')
            self.assertAlmostEqual(float(preview.motion[0])*8,n,delta=.04)
            self.assertEqual(preview.render(-1,(20,80)).size,(20,80))
            self.assertFalse(np.array_equal(preview.render(-1,(20,80)),preview.render(1,(20,80))))
        with self.assertRaises(ValueError):advanced_atlas.multi_pack(images[:1])
        with self.assertRaises(ValueError):advanced_atlas.multi_pack(images+[images[0]])
    def test_invalid_neon_and_missing_mask(self):
        art=Image.new('RGB',(10,10))
        with self.assertRaises(ValueError):advanced_atlas.neon_pack(art)
        with self.assertRaises(ValueError):advanced_atlas.neon_pack(art,art,dict(brightness=float('nan')))
