import copy
import unittest
from PIL import Image
import transparency_finish as finish


class TransparencyAuthoringTests(unittest.TestCase):
    def test_legacy_fields_survive_without_mutating_project(self):
        old=dict(finish='glossy', tint='#123456', haze=0, depth=.018,
                 screw_mask='custom screws.png', detail_mask='custom detail.png',
                 future={'values':[1,2]})
        original=copy.deepcopy(old)
        new=finish.settings('case',old)
        self.assertEqual(new['haze'],0)
        self.assertEqual(new['depth'],.018)
        self.assertEqual(new['screw_mask'],'custom screws.png')
        self.assertEqual(new['interior'],'artwork')
        new['future']['values'].append(3)
        self.assertEqual(old,original)

    def test_three_modes_have_separate_settings(self):
        for mode in finish.MODES:
            first=finish.settings(mode)
            first['tint']='#123456'
            self.assertNotEqual(finish.settings(mode)['tint'],first['tint'])
        self.assertEqual(finish.settings('glass')['finish'],'display')
        self.assertEqual(finish.settings('crystal')['cuts'],140)

    def test_bad_optics_are_rejected_before_export(self):
        for name,value in [('haze',float('nan')),('thickness',float('inf')),
                           ('reflection_strength',-1),('border',0),
                           ('art_depth',True),('roughness','bad')]:
            with self.subTest(name=name),self.assertRaises(ValueError):
                finish.settings('glass',{name:value})
        for cuts in [12.5,True,float('nan'),401]:
            with self.subTest(cuts=cuts),self.assertRaises(ValueError):
                finish.settings('crystal',{'cuts':cuts})

    def test_atlas_preserves_all_corners_and_no_old_header(self):
        source=Image.new('RGBA',(512,2048),(10,20,30,255))
        corners=[(0,0),(511,0),(0,2047),(511,2047)]
        colours=[(255,0,0,255),(0,255,0,255),(0,0,255,255),(12,34,56,255)]
        for xy,rgba in zip(corners,colours):source.putpixel(xy,rgba)
        atlas=finish.artwork_atlas(source)
        self.assertEqual(atlas.size,(512,4096))
        self.assertEqual(atlas.crop((0,0,512,2048)).tobytes(),source.tobytes())
        self.assertEqual(atlas.getpixel((0,2048)),(255,255,255,255))

    def test_template_centre_and_ends_remain_calibrated(self):
        self.assertEqual(finish.source_uv(-.108,.415),(.031,.07715))
        u,v=finish.source_uv(0,.006)
        self.assertAlmostEqual(u*512,253.952)
        self.assertAlmostEqual(v*2048,1098.00448)
        u,v=finish.source_uv(.108,-.403)
        self.assertAlmostEqual(u,.961)
        self.assertAlmostEqual(v,.99512)

if __name__=='__main__':unittest.main()
