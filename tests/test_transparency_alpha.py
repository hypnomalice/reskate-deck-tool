import tempfile,unittest
from pathlib import Path
from PIL import Image,ImageDraw
import creator_engine,preview_texture
import transparency_finish
from transparency_preview import TransparencyPreview

class TransparentArtworkTests(unittest.TestCase):
    def test_real_export_preserves_transparent_padding_and_partial_alpha(self):
        with tempfile.TemporaryDirectory() as folder:
            image=Image.new('RGBA',(512,2048),(255,0,255,0))
            ImageDraw.Draw(image).rectangle((220,300,290,380),fill=(240,20,30,128))
            path=Path(folder)/'alpha.png';image.save(path)
            for mode,cfg in [('glass',{}),('glass',{'finish':'liquid'}),('case',{}),('crystal',{})]:
                with self.subTest(mode=mode,cfg=cfg):
                    p=dict(name='Alpha Test',mode=mode,images=[str(path),None],fit='Stretch',background='#00ff00',placement=[dict(zoom=.8,x=.1,y=.1),{}])
                    p[mode]=cfg
                    exported=creator_engine.export_texture(p)
                    decoded=preview_texture.decode_bc7(exported['texture'],exported['texture_size'])
                    alpha=decoded.getchannel('A')
                    self.assertEqual(alpha.getpixel((150,600)),0)
                    self.assertTrue(100<alpha.getpixel((306,680))<155)
                    preview=TransparencyPreview(decoded,mode,cfg).render(0,(128,512))
                    self.assertLess(preview.getpixel((38,150))[3],200)

    def test_liquid_label_uses_full_deck_coordinates(self):
        image=Image.new('RGBA',(512,2048),(0,0,0,0))
        ImageDraw.Draw(image).rectangle((200,400,300,500),fill=(240,20,30,255))
        preview=TransparencyPreview(transparency_finish.artwork_atlas(image),'glass',dict(finish='liquid'))
        result=preview.render(0,(128,512))
        self.assertEqual(result.getpixel((62,112))[3],255)
        self.assertLess(result.getpixel((62,220))[3],255)

    def test_haze_filters_colour_in_premultiplied_alpha(self):
        image=Image.new('RGBA',(512,2048),(255,0,0,0))
        ImageDraw.Draw(image).rectangle((200,400,300,500),fill=(0,255,0,255))
        atlas=transparency_finish.artwork_atlas(image,4)
        r,g,b,a=atlas.getpixel((198,450))
        self.assertTrue(0<a<255)
        self.assertEqual((r,b),(0,0))
