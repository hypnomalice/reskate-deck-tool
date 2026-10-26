import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import time
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
try:
    from PySide6.QtCore import QTimer
    from qt_ui import application, Creator
except ImportError:
    Creator = None


class SlowRenderer:
    settings = np.array([0., 0., 0.])
    active = maximum = 0
    def set_lens_strength(self, value):
        self.settings[2] = value
    def render(self, angle, size):
        SlowRenderer.active += 1
        SlowRenderer.maximum = max(SlowRenderer.maximum, SlowRenderer.active)
        try:
            time.sleep(.12)
            return Image.new('RGB', size, (round((angle+1)*100), 80, 120))
        finally:
            SlowRenderer.active -= 1


@unittest.skipIf(Creator is None, 'Qt UI dependencies not installed')
class PreviewSchedulingTests(unittest.TestCase):
    def setUp(self):
        self.app = application()
        with patch.object(Creator, 'check_updates', lambda self: None):
            self.window = Creator()
        w = self.window
        w.animation_timer.stop()
        w.renderer = SlowRenderer(); w.detail_renderer = None
        w.display_revision = w.revision; w.last_key = None
        SlowRenderer.active = SlowRenderer.maximum = 0

    def wait_for(self, condition):
        start = time.monotonic()
        while not condition():
            self.app.processEvents(); time.sleep(.002)
            self.assertLess(time.monotonic()-start, 4, 'Preview never settled')

    def tearDown(self):
        w = self.window
        self.wait_for(lambda: not w.frame_worker)
        w.preview_timer.stop(); w.poll_timer.stop()
        w.baseline = w.workspace(); w.close()

    def test_render_keeps_ui_alive_and_latest_angle_wins(self):
        w = self.window; ticks = []
        timer = QTimer(); timer.timeout.connect(lambda: ticks.append(time.monotonic())); timer.start(10)
        w.render()
        # A slow renderer must not run synchronously inside render().
        self.assertIsNone(w.board.frame)
        for value in (-80, 0, 80): w.angle.spin.setValue(value)
        self.wait_for(lambda: w.last_key is not None and w.last_key[1] == .8 and not w.frame_worker)
        timer.stop()
        self.assertGreaterEqual(len(ticks), 8)
        self.assertEqual(SlowRenderer.maximum, 1)

    def test_drag_restores_resolution_and_old_deck_cannot_repaint(self):
        w = self.window
        w.angle.slider.setSliderDown(True); w.render()
        self.wait_for(lambda: w.last_key is not None and w.last_key[5] == (120,480) and not w.frame_worker)
        w.angle.slider.setSliderDown(False); w.render()
        self.wait_for(lambda: w.last_key[5] == (180,720) and not w.frame_worker)
        w.angle.spin.setValue(-40); w.schedule(clear=True)
        self.assertIsNone(w.board.frame)
        self.wait_for(lambda: not w.frame_worker)
        self.assertIsNone(w.board.frame)


    def test_orbit_changes_effect_angle_and_restores_quality(self):
        w=self.window
        w.view_mode.setCurrentText('3D')
        w.preview_orbit_changed(40,15,True)
        self.assertGreater(w.angle.value(),50)
        self.wait_for(lambda: w.last_key is not None and w.last_key[5]==(120,480) and not w.frame_worker)
        w.preview_orbit_changed(40,15,False)
        self.wait_for(lambda: w.last_key is not None and w.last_key[5]==(180,720) and not w.frame_worker)
        w.angle.spin.setValue(-100)
        self.assertAlmostEqual(w.board.yaw,-70)
        w.enlarge()
        w.preview_orbit_changed(20,-10,False)
        self.assertEqual((w.board.yaw,w.board.pitch),(w.large_board.yaw,w.large_board.pitch))
        w.large.close()

    def test_export_check_runs_off_thread_and_ignores_changed_source(self):
        w=self.window; w.renderer.mode='classic'
        from effect_preview import AtlasPreview
        result=AtlasPreview(Image.new('RGB',(512,4096),'red'),'classic')
        def prepare(*args):
            time.sleep(.15)
            return result
        ticks=[]; timer=QTimer(); timer.timeout.connect(lambda: ticks.append(time.monotonic()));timer.start(10)
        with patch('preview_texture.prepare',side_effect=prepare):
            w.export_preview.setChecked(True)
            self.assertTrue(w.texture_worker)
            self.wait_for(lambda: not w.texture_worker)
            self.assertIs(w.active_preview_renderer(),result)
            self.assertGreaterEqual(len(ticks),4)
            w.export_preview.setChecked(False)
            self.assertIs(w.active_preview_renderer(),w.renderer)
            w.export_preview.setChecked(True)
            w.schedule(clear=True)
            self.wait_for(lambda: not w.texture_worker)
            self.assertIsNone(w.export_renderer)
            self.assertFalse(w.export_preview.isChecked())
        timer.stop()


    def test_surface_preparation_maps_artwork_only_once(self):
        import board_preview
        pixels=np.broadcast_to(np.arange(200,dtype=np.uint8)[:,None,None],(200,50,3)).copy()
        source=Image.fromarray(pixels)
        key=(self.window.revision,0,0,False,None,(50,200),False,('2D',False,0,0),False)
        expected=board_preview.map_artwork(source)
        prepared=Creator.prepare_surface(source,key)
        self.window.present_frame(prepared,key,prepared=True)
        pixel=self.window.board.frame.toImage().pixelColor(25,0)
        self.assertEqual(pixel.red(),expected.getpixel((25,0))[0])

    def test_studio_light_changes_preview_without_changing_project(self):
        w=self.window
        before=w.workspace()
        w.view_mode.setCurrentText('3D')
        self.wait_for(lambda:w.last_key is not None and not w.frame_worker)
        lit=w.board.frame.toImage().pixelColor(50,250)
        w.studio_light.setChecked(False)
        self.wait_for(lambda:w.last_key is not None and not w.frame_worker)
        unlit=w.board.frame.toImage().pixelColor(50,250)
        self.assertNotEqual(lit,unlit)
        self.assertEqual(w.workspace(),before)
