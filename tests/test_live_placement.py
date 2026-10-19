import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

import image_placement
import live_placement


class LivePlacementTests(unittest.TestCase):
    def deck(self,mode):
        return dict(mode=mode,fit='Stretch',background_fit='Crop to fill',background='#000000',
                    placement=[dict(zoom=1,x=0,y=0),dict(zoom=1,x=0,y=0)],
                    depth=dict(strength=0,convergence=.5,bands=1))

    def test_zero_depth_keeps_artwork(self):
        image = Image.new('RGBA',(40,160),'#2875a3')
        ImageDraw.Draw(image).rectangle((8,20,24,100),fill='white')
        d = self.deck('depth')
        actual = live_placement.render([image,Image.new('L',image.size,255)],d,.7,image.size)
        expected = image_placement.frame(image,size=image.size)
        self.assertEqual(actual.tobytes(),expected.tobytes())

    def test_layers_preserve_linear_alpha(self):
        front = Image.new('RGBA',(40,160),(255,0,0,128))
        back = Image.new('RGB',front.size,'blue')
        pixel = live_placement.render([front,back],self.deck('layers'),0,front.size).getpixel((20,80))
        self.assertTrue(185<=pixel[0]<=190 and 185<=pixel[2]<=190)
        self.assertEqual(pixel[1],0)

    def test_classic_keeps_view_direction(self):
        sources = [Image.new('RGB',(40,160),colour) for colour in ('red','blue')]
        deck = self.deck('classic')
        self.assertGreater(live_placement.render(sources,deck,1,(40,160)).getpixel((20,80))[0],245)
        self.assertGreater(live_placement.render(sources,deck,-1,(40,160)).getpixel((20,80))[2],245)

    def test_cached_source_matches_file_placement(self):
        image = Image.new('RGBA',(150,100),(60,140,200,128))
        ImageDraw.Draw(image).rectangle((0,0,40,100),fill='red')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'source.png'
            image.save(path)
            for fit in ('Stretch','Crop to fill','Fit entire image'):
                for settings in (dict(zoom=1,x=0,y=0),dict(zoom=.6,x=.2,y=-.1)):
                    cached = image_placement.frame(image,fit,placement=settings)
                    file = image_placement.frame(path,fit,placement=settings)
                    self.assertEqual(cached.tobytes(),file.tobytes())
