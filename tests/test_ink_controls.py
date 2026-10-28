import unittest
from PIL import Image
from finish_atlas import ink_mask, pack

class InkControlsTests(unittest.TestCase):
    def test_default_preserves_every_mask_value(self):
        image=Image.new('L',(256,1));image.putdata(range(256))
        self.assertEqual(ink_mask(image).tobytes(),image.tobytes())
        self.assertEqual(pack('ink',image,image).tobytes(),pack('ink',image,image,ink={}).tobytes())

    def test_inverse_strength_and_contrast_are_baked_into_mask(self):
        image=Image.new('L',(3,1));image.putdata([0,128,255])
        self.assertEqual(list(ink_mask(image,{'invert':True}).getdata()),[255,127,0])
        self.assertEqual(list(ink_mask(image,{'strength':0}).getdata()),[0,0,0])
        self.assertEqual(list(ink_mask(image,{'contrast':0}).getdata()),[128]*3)
        graphic=Image.new('RGB',(8,32),'red')
        original=pack('ink',graphic,Image.new('L',graphic.size,255))
        edited=pack('ink',graphic,Image.new('L',graphic.size,255),ink={'strength':0})
        self.assertEqual(original.crop((0,0,512,2048)).tobytes(),edited.crop((0,0,512,2048)).tobytes())
        self.assertEqual(edited.getpixel((200,3000))[0],0)
        self.assertEqual(original.getpixel((200,3000))[0],255)

    def test_invalid_settings_are_rejected(self):
        for settings in ({'strength':2},{'contrast':-1},{'contrast':float('nan')}):
            with self.assertRaises(ValueError):ink_mask(Image.new('L',(1,1)),settings)


class InkColourTests(unittest.TestCase):
    def test_colours_and_showthrough_match_atlas_preview_endpoints(self):
        import numpy as np
        from effect_preview import AtlasPreview
        art=Image.new('RGB',(16,64),'red');mask=Image.new('L',art.size,255)
        cfg=dict(background_colour='#102030',revealed_colour='#40c080',showthrough=0)
        atlas=pack('ink',art,mask,ink=cfg)
        self.assertEqual(atlas.getpixel((192,56)),(16,32,48))
        self.assertEqual(atlas.getpixel((320,56)),(64,192,128))
        r=AtlasPreview(atlas,'ink')
        for pose,expected in [((65,0),(16,32,48)),((0,0),(64,192,128))]:
            actual=np.asarray(r.render(0,art.size,view_pose=pose))
            np.testing.assert_allclose(actual,np.broadcast_to(expected,actual.shape),atol=1)
        for amount in (0,.5,1):
            cfg['showthrough']=amount
            r=AtlasPreview(pack('ink',art,mask,ink=cfg),'ink')
            image=np.asarray(r.render(0,art.size,view_pose=(0,0)))
            if amount==1:np.testing.assert_allclose(image,np.asarray(art),atol=1)
            elif amount==.5:self.assertGreater(image[0,0,0],64);self.assertLess(image[0,0,1],192)

    def test_colour_options_validate_and_leave_other_finishes_unchanged(self):
        art=Image.new('RGB',(16,64),'red')
        for cfg in ({'showthrough':-1},{'showthrough':float('nan')},{'background_colour':'invalid'}):
            with self.assertRaises(ValueError):pack('ink',art,art,ink=cfg)
        for mode in ('metal','window'):
            self.assertEqual(pack(mode,art,art).tobytes(),pack(mode,art,art,ink={'showthrough':1}).tobytes())
