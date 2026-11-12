import os,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from unittest.mock import patch
import numpy as np
from PIL import Image
import crystal_finish
from effect_preview import AtlasPreview

class CrystalTests(unittest.TestCase):
 def test_artwork_controls_and_deterministic_cuts(self):
  art=Image.new('RGB',(512,1984),'#7294c6')
  a=crystal_finish.pack(art,dict(tint='#80b0ee',cuts=40,grip_tape=True));b=crystal_finish.pack(art,dict(tint='#eeb080',cuts=240,grip_tape=False))
  np.testing.assert_array_equal(np.asarray(a)[64:2048,:,:3],np.asarray(art))
  np.testing.assert_array_equal(np.asarray(crystal_finish.facet_map(40)),np.asarray(crystal_finish.facet_map(40)))
  self.assertGreater(len(np.unique(np.asarray(b)[2048:,:,:3].reshape(-1,3),axis=0)),len(np.unique(np.asarray(a)[2048:,:,:3].reshape(-1,3),axis=0)))
  pa,pb=AtlasPreview(a,'crystal'),AtlasPreview(b,'crystal')
  np.testing.assert_allclose(pa.sample(.875,27/4096),crystal_finish.MARKER,atol=.008)
  self.assertGreater(pa.sample(.875,23/4096)[0],.95);self.assertLess(pb.sample(.875,23/4096)[0],.05)
  self.assertFalse(np.allclose(pa.sample(.875,11/4096),pb.sample(.875,11/4096)))
  u=np.linspace(.1,.9,40)[None,:];v=np.linspace(.1,.9,80)[:,None]
  # Grip is fixed even when the viewing angle changes; exposed crystal remains optical.
  np.testing.assert_array_equal(np.asarray(crystal_finish.preview(pa,-.8,u,v,top=True)),np.asarray(crystal_finish.preview(pa,.8,u,v,top=True)))
  self.assertFalse(np.array_equal(np.asarray(crystal_finish.preview(pb,-.8,u,v)),np.asarray(crystal_finish.preview(pb,.8,u,v))))
 def test_invalid_cut_values(self):
  for cuts in (0,401,float('nan'),float('inf')):
   with self.assertRaises(ValueError):crystal_finish.settings(dict(cuts=cuts))
 def test_controls_persist_and_do_not_leak_into_case(self):
  from qt_ui import application,Creator
  app=application()
  with patch.object(Creator,'check_updates',lambda self:None):w=Creator()
  try:
   w.decks[0].update(mode='crystal',effect_chosen=True,crystal=dict(tint='#a382e6',cuts=64,grip_tape=True));w.apply_deck();w.show();w.inspector_tabs.setCurrentIndex(1);app.processEvents()
   self.assertTrue(w.crystal_box.isVisible());self.assertFalse(w.case_box.isVisible())
   w.crystal_cuts.spin.setValue(230);w.crystal_grip.setChecked(False)
   cfg=w.workspace()['decks'][0]['crystal'];self.assertEqual(cfg,dict(tint='#a382e6',cuts=230,grip_tape=False))
   w.apply_deck();self.assertEqual(w.crystal_cuts.value(),230)
   w.decks[0]['mode']='case';w.apply_deck();app.processEvents();self.assertFalse(w.crystal_box.isVisible());self.assertTrue(w.case_box.isVisible())
  finally:
   w.preview_timer.stop();w.poll_timer.stop();w.animation_timer.stop();w.baseline=w.workspace();w.close()
