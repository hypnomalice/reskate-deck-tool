import unittest
import numpy as np
from PIL import Image
import cd_finish
from effect_preview import AtlasPreview

class CDControlsTests(unittest.TestCase):
    def test_new_controls_preserve_recognition_and_artwork(self):
        art=Image.new('RGB',(512,1984),(83,124,197));depth=Image.new('L',art.size,120)
        baseline=cd_finish.pack(art,depth,{})
        cfg=dict(optics='combined',clear_layer=True,sheen_strength=2,rim_strength=4,boundary_strength=4,scratch_strength=4,scratch_amount=4,stronger_backing=True)
        atlas=cd_finish.pack(art,depth,cfg)
        a,b=np.asarray(atlas),np.asarray(baseline)
        np.testing.assert_array_equal(a[24:48],b[24:48])
        np.testing.assert_array_equal(a[64:2048],b[64:2048])
        np.testing.assert_array_equal(a[64:2048,:,:3],np.asarray(art))
        preview=AtlasPreview(atlas,'cd')
        self.assertAlmostEqual(preview.sample(.125,4/4096)[0],.17,delta=.006)
        self.assertAlmostEqual(preview.sample(.125,16/4096)[0],.38,delta=.006)
        self.assertEqual(cd_finish.settings(cfg)['scratch_amount'],4)
    def test_limits_and_defaults(self):
        cfg=cd_finish.settings()
        self.assertEqual(cfg['finish'],'cd_mirror')
        self.assertEqual(cfg['rim_strength'],0)
        for key,value in [('optics','unknown'),('depth_strength',3),('scratch_amount',5),('rim_strength',float('nan'))]:
            with self.assertRaises(ValueError):cd_finish.settings({key:value})
