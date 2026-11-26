import os,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from qt_ui import Creator,application

class LayerFinishUiTests(unittest.TestCase):
 def test_layer_controls_save_reload_and_preserve_mask_paths(self):
  app=application()
  with patch.object(Creator,'check_updates',lambda self:None):w=Creator()
  try:
   with tempfile.TemporaryDirectory() as temp:
    p=Path(temp)/'mask.png'
    from PIL import Image
    Image.new('RGB',(32,128),'white').save(p)
    w.decks[0].update(mode='layers',images=[str(p),str(p)],layer_finishes={'background':dict(finish='holographic',strength=.85,area='mask',mask=str(p))});w.apply_deck()
    row=w.layer_finish_controls['background'];self.assertEqual(row['finish'].currentIndex(),1);self.assertEqual(row['area'].currentIndex(),2)
    w.layer_finish_controls['foreground']['finish'].setCurrentIndex(1);w.layer_finish_controls['foreground']['strength'].spin.setValue(37)
    d=w.workspace();self.assertAlmostEqual(d['decks'][0]['layer_finishes']['foreground']['strength'],.37);self.assertFalse(d['decks'][0]['surface_finish']['holographic'])
    project=Path(temp)/'project.json';project.write_text(json.dumps(d));w.load_project(project)
    self.assertEqual(w.workspace(),d)
    self.assertEqual(w.workspace()['decks'][0]['layer_finishes']['background']['mask'],str(p.resolve()))
  finally:
   w.preview_timer.stop();w.poll_timer.stop();w.animation_timer.stop();w.baseline=w.workspace();w.close()
