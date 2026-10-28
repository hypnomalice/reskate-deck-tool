import unittest
import numpy as np
from PIL import Image
import depth_views,depth_native

class DepthParityTests(unittest.TestCase):
    @unittest.skipIf(depth_native.backend() is None,'Optional native backend unavailable')
    def test_native_matches_original_export_on_occlusions_and_edges(self):
        rng=np.random.default_rng(529)
        for width,height in [(1,3),(2,4),(9,7),(64,19)]:
            rgb=Image.fromarray(rng.integers(0,256,(height,width,3),dtype=np.uint8))
            for mask in [rng.integers(0,256,(height,width),dtype=np.uint8),np.tile(np.linspace(0,255,width,dtype=np.uint8),(height,1)),np.tile(np.where(np.arange(width)<width//2,30,230).astype(np.uint8),(height,1))]:
                depth=Image.fromarray(mask)
                for angle in (-1,-.37,0,.5,1):
                    for strength,convergence in [(0,.5),(.08,.5),(.7,.15),(1,1)]:
                        with self.subTest(size=rgb.size,angle=angle,strength=strength):
                            expected=depth_views._reference_view(rgb,depth,angle,strength,convergence)
                            actual=depth_native.render(rgb,depth,angle,strength,convergence)
                            self.assertEqual(actual.tobytes(),expected.tobytes())

    def test_shared_preview_uses_full_export_views(self):
        import preview_depth
        from unittest.mock import patch
        image=Image.new('RGB',(51,103),'red');depth=Image.new('L',image.size,128)
        expected=[image.copy() for _ in range(8)]
        with patch.object(depth_views,'views',return_value=expected) as shared:
            result=preview_depth.views(image,depth,.2,.7)
        self.assertIs(result,expected)
        self.assertEqual(shared.call_args.args[:4],(image,depth,.2,.7))

    def test_fallback_preserves_export_pixels(self):
        from unittest.mock import patch
        rgb=Image.fromarray(np.arange(8*13*3,dtype=np.uint8).reshape(8,13,3))
        depth=Image.fromarray(np.tile(np.arange(13,dtype=np.uint8)*20,(8,1)))
        with patch.object(depth_native,'backend',return_value=None):
            actual=depth_views.view(rgb,depth,.7,.4,.5)
        self.assertEqual(actual.tobytes(),depth_views._reference_view(rgb,depth,.7,.4,.5).tobytes())
