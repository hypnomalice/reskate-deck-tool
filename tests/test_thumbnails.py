import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
from creator_engine import thumbnail


class ThumbnailTests(unittest.TestCase):
    def test_automatic_thumbnail_excludes_margin_outside_visible_deck(self):
        source=Image.new('RGB',(512,2048),'black')
        # This white margin is outside the measured standard-deck artwork UVs.
        ImageDraw.Draw(source).rectangle((0,0,511,150),fill='white')
        original=source.tobytes()
        image=thumbnail(source,source,size=256)
        height=round(256*.79);width=height//4;top=round(256*.035);gap=round(256*.055)
        left=(256-width*2-gap)//2
        for i in range(2):
            panel=image.crop((left+i*(width+gap),top,left+i*(width+gap)+width,top+height))
            opaque=[pixel[:3] for pixel in panel.getdata() if pixel[3]==255]
            self.assertTrue(opaque)
            self.assertTrue(all(pixel==(0,0,0) for pixel in opaque))
        self.assertEqual(source.tobytes(),original)
        self.assertEqual(image.getpixel((0,0))[3],0)

    def test_custom_thumbnail_keeps_its_own_composition(self):
        custom=Image.new('RGBA',(80,120),'red')
        ImageDraw.Draw(custom).rectangle((0,0,79,15),fill='white')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'custom.png';custom.save(path)
            actual=thumbnail(None,None,custom=str(path),size=256)
        expected=ImageOps.pad(custom,(256,256),Image.Resampling.LANCZOS,color=(0,0,0,0))
        self.assertEqual(actual.tobytes(),expected.tobytes())


if __name__=='__main__':unittest.main()
