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
