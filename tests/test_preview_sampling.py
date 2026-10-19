import unittest
import numpy as np
from PIL import Image
from effect_preview import AtlasPreview


class PreviewSamplingTests(unittest.TestCase):
    def test_depth_sampling_matches_colour_sampling_at_edges_and_subpixels(self):
        rng=np.random.default_rng(2026)
        renderer=AtlasPreview(Image.fromarray(rng.integers(0,256,(64,32,3),dtype=np.uint8)),'smooth')
        u=np.array([-.1,0,.015625,.12345,.5,.984375,1,1.1],dtype=np.float32)[None,:]
        v=np.linspace(-.1,1.1,27,dtype=np.float32)[:,None]
        expected=renderer.sample(u,v)
        for channel in range(3):
            np.testing.assert_array_equal(renderer.sample_channel(u,v,channel),expected[...,channel])
