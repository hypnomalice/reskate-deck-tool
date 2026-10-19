import unittest
import numpy as np
from PIL import Image
from effect_preview import AtlasPreview
import smooth_effect


class SmoothEffectTests(unittest.TestCase):
    def test_metadata_round_trip(self):
        image=Image.new('RGB',(512,2048),'gray')
        depth=Image.new('L',image.size,128)
        for ghost in (False,True):
            renderer=AtlasPreview(smooth_effect.pack(image,depth,.075,.5,ghost),'ghost' if ghost else 'smooth')
            self.assertAlmostEqual(float(renderer.motion[0]),.075,delta=.002)
            self.assertAlmostEqual(float(renderer.motion[1]),.5,delta=.004)
            self.assertAlmostEqual(float(renderer.sample(.5,.75)[1]),128/255,delta=.005)

    def test_small_angle_changes_move_continuously(self):
        pixels=np.broadcast_to(np.linspace(0,255,512,dtype='uint8')[None,:,None],(2048,512,3)).copy()
        image=Image.fromarray(pixels)
        renderer=AtlasPreview(smooth_effect.pack(image,Image.new('L',image.size,255),.1,.5),'smooth')
        frames=[np.asarray(renderer.render(a,(256,128)),dtype=float) for a in (.0,.05,.10)]
        self.assertGreater(np.abs(frames[1]-frames[0]).sum(),0)
        self.assertLess(np.abs(frames[1]-frames[0]).mean(),3)

    def test_new_project_defaults_to_animation(self):
        from qt_ui import default_deck
        deck=default_deck()
        self.assertEqual(deck['mode'],'gif')
        self.assertFalse(deck['lenticular'])
