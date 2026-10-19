import unittest
from PIL import Image, ImageDraw
from effect_preview import AtlasPreview
import depth_views
import layer_atlas


class PreviewTests(unittest.TestCase):
    def test_classic_direction_and_linear_blending(self):
        atlas=Image.new('RGB',(512,4096),'blue')
        ImageDraw.Draw(atlas).rectangle((0,64,511,2047),fill='red')
        preview=AtlasPreview(atlas,'classic')
        positive=preview.render(1,(1,1)).getpixel((0,0))
        negative=preview.render(-1,(1,1)).getpixel((0,0))
        self.assertGreater(positive[0],245)
        self.assertGreater(negative[2],245)
        self.assertTrue(35<positive[2]<45)

    def test_balanced_grid_views_and_linear_midpoint(self):
        views=[Image.new('RGB',(8,32),(n*32,)*3) for n in range(8)]
        preview=AtlasPreview(depth_views.pack(views,0,balanced=True),'depth')
        self.assertEqual(preview.render(-1,(3,12)).getpixel((1,6)),(0,0,0))
        self.assertEqual(preview.render(1,(3,12)).getpixel((1,6)),(224,224,224))
        self.assertTrue(112<=preview.render(0,(3,12)).getpixel((1,6))[0]<=114)

    def test_direct_layers_use_linear_alpha_and_reveal_background(self):
        front=Image.new('RGBA',(8,32),(255,0,0,128))
        back=Image.new('RGB',front.size,'blue')
        preview=AtlasPreview(layer_atlas.pack(front,back,.4,.5,0),'layers')
        middle=preview.render(0,(10,40)).getpixel((5,20))
        self.assertTrue(185<=middle[0]<=190)
        self.assertTrue(185<=middle[2]<=190)
        self.assertEqual(preview.render(1,(10,40)).getpixel((0,20)),(0,0,255))

    def test_metadata_strength_is_decoded_as_srgb(self):
        views=[Image.new('RGB',(4,16),'white') for _ in range(8)]
        preview=AtlasPreview(depth_views.pack(views,.5,balanced=True),'depth')
        self.assertAlmostEqual(float(preview.settings[2]),.21586,places=4)
        preview.set_lens_strength(1)
        self.assertEqual(float(preview.settings[2]),1)
        preview.set_lens_strength(0)
        self.assertEqual(float(preview.settings[2]),0)


if __name__=='__main__':unittest.main()
