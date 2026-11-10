import os,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from unittest.mock import patch
from qt_ui import application,Creator

class EditorWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.app=application()
        with patch.object(Creator,'check_updates',lambda self:None):self.w=Creator()
        self.w.decks[0]['mode']='cd';self.w.apply_deck();self.w.show();self.app.processEvents()
    def tearDown(self):
        self.w.preview_timer.stop();self.w.poll_timer.stop();self.w.animation_timer.stop();self.w.baseline=self.w.workspace();self.w.close()
    def test_transform_roundtrip_and_linked_depth(self):
        w=self.w;w.adjust_image();self.assertTrue(w.board.edit_artwork)
        w.positions['rotation'].spin.setValue(32.75);w.positions['zoom'].spin.setValue(675)
        w.drag_artwork(.12,-.08)
        d=w.workspace()['decks'][0]
        self.assertEqual(d['placement'][0],d['placement'][1])
        self.assertAlmostEqual(d['placement'][0]['rotation'],32.75)
        self.assertAlmostEqual(d['placement'][0]['zoom'],6.75)
        w.apply_deck();self.assertAlmostEqual(w.positions['rotation'].value(),32.75)
        self.assertAlmostEqual(w.positions['x'].value(),12)
    def test_static_preview_is_not_on_an_animation_timer(self):
        self.assertFalse(self.w.animation_timer.isActive())
        self.assertEqual(self.w.preview_quality.currentText(),'Light preview')

    def test_case_settings_fit_default_inspector(self):
        w=self.w;w.decks[0].update(mode='case',effect_chosen=True);w.apply_deck()
        w.inspector_tabs.setCurrentIndex(1);self.app.processEvents()
        self.assertTrue(w.case_help.wordWrap())
        self.assertEqual(w.inspectors.horizontalScrollBar().maximum(),0)
        self.assertLessEqual(w.case_box.width(),w.inspectors.viewport().width())

    def test_eink_tilt_range_roundtrips(self):
        w=self.w;w.decks[0].update(mode='eink',effect_chosen=True);w.apply_deck()
        w.eink_span.spin.setValue(180)
        self.assertAlmostEqual(w.workspace()['decks'][0]['eink']['span'],1.8)
        self.assertEqual(w.eink_span.spin.suffix(),'%')
        w.apply_deck()
        self.assertEqual(w.eink_span.value(),180)
    def test_cd_duplicate_controls_are_hidden(self):
        self.w.inspector_tabs.setCurrentIndex(1);self.app.processEvents()
        self.assertFalse(self.w.strength.isVisible());self.assertFalse(self.w.convergence.isVisible())
        self.assertFalse(self.w.thumb_name.isVisible());self.assertFalse(self.w.pack_button.isVisible())

    def test_holographic_and_palette_controls_roundtrip(self):
        w=self.w;w.decks[0]['mode']='layers';w.apply_deck()
        self.assertFalse(w.surface_holo.isChecked())
        w.surface_holo.setChecked(True);w.surface_holo_strength.spin.setValue(72)
        cfg=w.workspace()['decks'][0]['surface_finish']
        self.assertTrue(cfg['holographic']);self.assertAlmostEqual(cfg['holo_strength'],.72)
        w.decks[0]['mode']='glitch';w.apply_deck();w.glitch_colours.setCurrentIndex(2)
        self.assertEqual(w.workspace()['decks'][0]['glitch']['colour_mode'],'two')
