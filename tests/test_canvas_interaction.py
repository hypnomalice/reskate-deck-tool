import os,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from unittest.mock import patch
from PySide6.QtCore import QPointF,QEvent,Qt,QRectF
from PySide6.QtGui import QMouseEvent,QWheelEvent
from qt_ui import application,Creator

class CanvasInteractionTests(unittest.TestCase):
    def setUp(self):
        self.app=application()
        with patch.object(Creator,'check_updates',lambda self:None):self.w=Creator()
        self.w.show();self.app.processEvents()
    def tearDown(self):
        for timer in (self.w.preview_timer,self.w.poll_timer,self.w.animation_timer,self.w.placement_render_timer):timer.stop()
        self.w.baseline=self.w.workspace();self.w.close()
    def test_deck_list_switch_and_rename(self):
        self.w.add_deck();self.assertEqual(self.w.deck_list.count(),2)
        self.w.deck_list.setCurrentRow(0);self.assertEqual(self.w.selected,0)
        self.w.name.setText('Renamed');self.w.rename();self.assertEqual(self.w.deck_list.item(0).text(),'Renamed')
        self.assertFalse(self.w.tabs.isVisible())
    def test_drag_edits_artwork_without_orbit(self):
        b=self.w.board;b.edit_artwork=True;b.artwork_rect=QRectF(0,0,100,400);b.drag_position=QPointF(10,10)
        moves=[];orbits=[];b.artwork_dragged.connect(lambda x,y:moves.append((x,y)));b.orbit_changed.connect(lambda *args:orbits.append(args))
        event=QMouseEvent(QEvent.MouseMove,QPointF(30,50),QPointF(30,50),Qt.NoButton,Qt.LeftButton,Qt.NoModifier)
        b.mouseMoveEvent(event);self.assertEqual(moves,[(.2,.1)]);self.assertEqual(orbits,[])
    def test_placement_updates_are_coalesced(self):
        w=self.w;w.choose_placement(0)
        with patch.object(w,'schedule') as full,patch.object(w,'render_reset') as draw:
            for i in range(20):w.positions['x'].set_value(i);w.move_image()
            full.assert_not_called();draw.assert_not_called()
        self.assertTrue(w.placement_render_timer.isActive())
    def test_settings_wheel_is_ignored(self):
        event=QEvent(QEvent.Wheel)
        self.assertTrue(self.w.scroll_guard.eventFilter(self.w.positions['zoom'].spin,event))
        self.assertFalse(event.isAccepted())
