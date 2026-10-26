import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
import depth_views


class DepthCacheTests(unittest.TestCase):
    def setUp(self):
        depth_views._view_cache = None
        self.art = Image.fromarray(np.random.default_rng(11).integers(0, 256, (64, 16, 3), dtype=np.uint8))
        self.depth = Image.linear_gradient('L').resize(self.art.size)

    def tearDown(self):
        depth_views._view_cache = None

    def test_cached_frames_are_isolated_from_caller_edits(self):
        frames = depth_views.views(self.art, self.depth)
        original = frames[0].tobytes()
        frames[0].paste('red', (0, 0, 16, 64))
        with patch.object(depth_views, 'view', side_effect=AssertionError('cache miss')):
            cached = depth_views.views(self.art, self.depth)
        self.assertEqual(cached[0].tobytes(), original)

    def test_source_and_motion_changes_invalidate_cache(self):
        depth_views.views(self.art, self.depth)
        changed = self.depth.copy(); changed.putpixel((0, 0), 255)
        with patch.object(depth_views, 'view', wraps=depth_views.view) as render:
            depth_views.views(self.art, changed)
            self.assertEqual(render.call_count, 8)
            depth_views.views(self.art, changed, .08)
            self.assertEqual(render.call_count, 16)
            depth_views.views(self.art, changed, .08, .2)
            self.assertEqual(render.call_count, 24)

    def test_cached_frames_match_existing_depth_renderer(self):
        expected = [depth_views.view(self.art, self.depth, i*2/7-1, .04, .5).tobytes() for i in range(8)]
        self.assertEqual([im.tobytes() for im in depth_views.views(self.art, self.depth)], expected)
