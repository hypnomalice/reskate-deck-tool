import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
import normal_layer, cd_finish

class NormalLayerTests(unittest.TestCase):
    def test_rotation_rotates_vectors_and_flat_padding_stays_flat(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'normal.png'
            Image.new('RGB',(16,16),(204,128,230)).save(path)
            vec=normal_layer.frame(dict(path=str(path),placement=dict(rotation=90,zoom=.5)),size=(32,32))
            self.assertGreater(vec[16,16,1],.5)
            self.assertLess(abs(vec[16,16,0]),.02)
            self.assertGreater(vec[0,0,2],.999)

    def test_optional_layer_preserves_recognition_art_and_depth(self):
        art=Image.new('RGB',(32,128),(40,70,90));depth=Image.new('L',art.size,177)
        base=cd_finish.pack(art,depth,dict(normal=dict(style='none')))
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'normal.png';Image.new('RGB',(16,16),(128,128,255)).save(path)
            mapped=cd_finish.pack(art,depth,dict(normal=dict(path=str(path))))
            self.assertEqual(base.crop((0,31,512,2048)).tobytes(),mapped.crop((0,31,512,2048)).tobytes())
            self.assertEqual(base.getchannel('A').tobytes(),mapped.getchannel('A').tobytes())
            self.assertNotEqual(base.crop((384,24,512,28)).tobytes(),mapped.crop((384,24,512,28)).tobytes())

    def test_invalid_strength(self):
        for value in (float('nan'),float('inf'),-1,5):
            with self.assertRaises(ValueError):normal_layer.settings(dict(strength=value))

    def test_default_corner_matches_accepted_slopes(self):
        yy,xx=np.mgrid[0:1024,0:512]
        x=(xx+.5)/512-1.18;y=((yy+.5)/1024+.18)*4;r=np.sqrt(x*x+y*y)
        slope=np.sin(r*430+.12*np.sin(r*71))*.040+np.sin(r*773+.3)*.014
        vector=normal_layer.disc_frame('corner')
        np.testing.assert_allclose(vector[...,0],slope*x/r,atol=1e-7)
        np.testing.assert_allclose(vector[...,1],slope*y/r,atol=1e-7)

    def test_full_spiral_is_finite_and_hub_flat(self):
        vector=normal_layer.disc_frame('full')
        self.assertTrue(np.isfinite(vector).all())
        np.testing.assert_allclose(np.linalg.norm(vector,axis=-1),1,atol=1e-6)
        np.testing.assert_allclose(vector[556,246],(0,0,1),atol=1e-6)

if __name__=='__main__':unittest.main()
