import tempfile,unittest
from pathlib import Path
from PIL import Image,ImageDraw
import case_finish
from effect_preview import AtlasPreview
class MaskTests(unittest.TestCase):
    def test_mask_transport_and_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory);mask=Image.new('L',(512,1984));draw=ImageDraw.Draw(mask)
            for x,y in ((120,350),(390,1500)):draw.ellipse((x-12,y-12,x+12,y+12),fill=255)
            mask.save(path/'screws.png');detail=Image.new('L',mask.size);ImageDraw.Draw(detail).rectangle((200,800,300,1000),fill=255);detail.save(path/'details.png')
            cfg=dict(screw_mask=str(path/'screws.png'),detail_mask=str(path/'details.png'))
            points=case_finish.screw_positions(cfg['screw_mask']);self.assertEqual(len(points),2)
            self.assertAlmostEqual(points[0][0],120/512,delta=.005)
            atlas=case_finish.pack(Image.new('RGB',(512,1984),'red'),cfg);preview=AtlasPreview(atlas,'case')
            flags=preview.sample(.875,51/4096);self.assertGreater(flags[0],.99);self.assertGreater(flags[1],.99)
            self.assertAlmostEqual(flags[2],.72,delta=.008)
            self.assertEqual(atlas.getpixel((250,2970))[3],255);self.assertEqual(atlas.getpixel((100,2970))[3],0)
            self.assertEqual(preview.render(.3,(100,400)).size,(100,400))
            self.assertEqual(case_finish.settings(cfg)['screw_mask'],cfg['screw_mask'])
            # Supplied black mask explicitly replaces all donor screw positions.
            Image.new('L',mask.size).save(path/'blank.png');self.assertEqual(case_finish.screw_positions(path/'blank.png'),[])
    def test_editor_retains_mask_paths_when_adjusting_shell(self):
        from PySide6.QtWidgets import QApplication
        from qt_ui import Creator
        from unittest.mock import patch
        app=QApplication.instance() or QApplication([])
        with patch.object(Creator,'check_updates',lambda self:None):window=Creator()
        window.decks[0].update(mode='case',effect_chosen=True,case={'screw_mask':'screws.png','detail_mask':'details.png'})
        window.apply_deck();window.case_haze.spin.setValue(42);result=window.workspace()['decks'][0]['case']
        self.assertEqual(result['screw_mask'],'screws.png');self.assertEqual(result['detail_mask'],'details.png')
        window.clear_case_mask('screw_mask');self.assertIsNone(window.workspace()['decks'][0]['case']['screw_mask'])
        window.preview_timer.stop();window.poll_timer.stop();window.animation_timer.stop();window.baseline=window.workspace();window.close()
if __name__=='__main__':unittest.main()
