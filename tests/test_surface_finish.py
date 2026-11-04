import unittest
import numpy as np
from PIL import Image
import surface_finish
from effect_preview import AtlasPreview

class SurfaceFinishTests(unittest.TestCase):
    def test_depth_fix_scope_preserves_intentional_lenticular_bands(self):
        for mode in ('classic','layers','gif','metal','ink','window','liquid','neon'):
            self.assertFalse(surface_finish.smooth_depth(dict(mode=mode)))
        self.assertTrue(surface_finish.smooth_depth(dict(mode='ghost')))
        self.assertTrue(surface_finish.smooth_depth(dict(mode='depth',lenticular=False)))
        self.assertFalse(surface_finish.smooth_depth(dict(mode='depth',lenticular=True)))
        self.assertFalse(surface_finish.smooth_depth(dict(mode='ghost',surface_finish=dict(smooth_depth=False))))

    def test_disabled_sheen_is_exact_and_header_never_changes_art_or_animation_tables(self):
        for scale in (1,2):
            atlas=Image.new('RGB',(512*scale,4096*scale),(67,124,201))
            self.assertIs(surface_finish.mark(atlas,{}),atlas)
            out=surface_finish.mark(atlas,dict(shimmer=True,strength=.35))
            a=np.asarray(atlas);b=np.asarray(out);delta=np.any(a!=b,axis=-1)
            ys,xs=np.where(delta)
            self.assertEqual((ys.min(),ys.max()),(8*scale,24*scale-1))
            self.assertEqual((xs.min(),xs.max()),(384*scale,512*scale-1))
            np.testing.assert_array_equal(a[48*scale:],b[48*scale:])

    def test_white_sheen_moves_with_view_and_zero_strength_is_exact(self):
        atlas=Image.new('RGB',(512,4096),'#345678')
        p=AtlasPreview(surface_finish.mark(atlas,dict(shimmer=True,strength=1)),'classic')
        a=np.asarray(p.render(-.7,(32,128))).astype(int);b=np.asarray(p.render(.7,(32,128))).astype(int)
        self.assertGreater(np.abs(a-b).mean(),.2)
        plain=AtlasPreview(atlas,'classic').render(.4,(32,128))
        zero=AtlasPreview(surface_finish.mark(atlas,dict(shimmer=True,strength=0)),'classic').render(.4,(32,128))
        self.assertEqual(plain.tobytes(),zero.tobytes())

if __name__=='__main__':unittest.main()
