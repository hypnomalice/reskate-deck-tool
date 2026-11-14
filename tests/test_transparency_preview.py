import unittest
from PIL import Image
import numpy as np
import transparency_finish as finish
from transparency_preview import TransparencyPreview,cut_field

class TransparencyPreviewTests(unittest.TestCase):
    def setUp(self):
        self.image=Image.new('RGB',(512,2048),'#957246');self.atlas=finish.artwork_atlas(self.image)
    def test_distinct_materials_and_transparent_border(self):
        images=[TransparencyPreview(self.atlas,mode,cfg).render(.35,(80,320)) for mode,cfg in [('glass',{}),('case',{}),('case',{'interior':'pcb'}),('crystal',{})]]
        self.assertEqual(len({im.tobytes() for im in images}),4)
        for im in images:
            self.assertEqual(im.mode,'RGBA');self.assertLess(im.getchannel('A').getextrema()[0],255)
            self.assertEqual(im.getpixel((40,160))[3],255)
    def test_water_moves_but_display_glass_stays_still(self):
        for preset,moves in [('display',False),('water',True)]:
            preview=TransparencyPreview(self.atlas,'glass',{'finish':preset});a=preview.render(.4,(80,320)).tobytes();preview.clock_seconds=1;b=preview.render(.4,(80,320)).tobytes();self.assertEqual(a!=b,moves)
    def test_controls_change_preview_without_modifying_atlas(self):
        raw=self.atlas.tobytes();plain=TransparencyPreview(self.atlas,'glass').render(.4,(80,320)).tobytes()
        for cfg in [{'tint':'#00ff33','tint_strength':1},{'reflection_strength':0},{'roughness':1},{'haze':1}]:
            self.assertNotEqual(TransparencyPreview(self.atlas,'glass',cfg).render(.4,(80,320)).tobytes(),plain)
        self.assertEqual(raw,self.atlas.tobytes())
    def test_art_blur_is_shared_by_preview_and_export(self):
        self.assertEqual(finish.internal_blur_pixels('glass',{'haze':.5}),9)
        self.assertEqual(finish.internal_blur_pixels('case',{'finish':'glossy','haze':1}),0)
        self.assertEqual(finish.internal_blur_pixels('case',{'interior':'pcb','haze':1}),0)
        self.assertEqual(finish.internal_blur_pixels('crystal',{'haze':.5}),9)
    def test_crystal_field_is_bounded_and_irregular(self):
        u,v=np.meshgrid(np.linspace(.05,.95,80),np.linspace(.05,.95,160));sx,sy=cut_field(u,v)
        self.assertTrue(np.isfinite(sx).all() and np.isfinite(sy).all());self.assertLessEqual(np.max(np.abs(sx)),.68);self.assertGreater(len(np.unique(sx)),30)

if __name__=='__main__':unittest.main()
