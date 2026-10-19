import unittest
import numpy as np
from PIL import Image
import preview_depth
import depth_views
from effect_preview import AtlasPreview


class InteractiveDepthTests(unittest.TestCase):
    def test_zero_strength_preserves_image(self):
        image = Image.new('RGB', (252,1004), (60,120,220))
        result = preview_depth.views(image, Image.new('L',image.size,255),0)
        self.assertEqual(len(result),8)
        for frame in result:
            self.assertEqual(frame.tobytes(),image.tobytes())

    def test_constant_depth_matches_shift_direction(self):
        values = np.zeros((1004,252,3),dtype=np.uint8)
        values[:,100:110] = 255
        image = Image.fromarray(values)
        frames = preview_depth.views(image,Image.new('L',image.size,255),.1,.5)
        centres = [np.where(np.asarray(frame)[500,:,0]>128)[0].mean() for frame in (frames[0],frames[-1])]
        self.assertLess(centres[0],104.5)
        self.assertGreater(centres[1],104.5)

    def test_lens_detail_changes_with_strength(self):
        frames = [Image.new('RGB',(252,1004),(index*32,)*3) for index in range(8)]
        preview = AtlasPreview(depth_views.pack(frames,0,balanced=True),'depth')
        before = np.asarray(preview.render(0,(280,280),(.375,.46875,.625,.53125)))
        preview.set_lens_strength(1)
        after = np.asarray(preview.render(0,(280,280),(.375,.46875,.625,.53125)))
        self.assertGreater(np.count_nonzero(before!=after),280*280)
