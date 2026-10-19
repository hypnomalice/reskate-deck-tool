import copy
import os
import time
from pathlib import Path


def check(folder, projects):
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from qt_ui import application, Creator, default_deck
    app = application()
    window = Creator()
    window.show()
    window.decks = []
    for project in projects:
        deck = default_deck()
        deck.update(copy.deepcopy(project))
        window.decks.append(deck)
    layers = copy.deepcopy(window.decks[0])
    layers.update(mode='layers',name='Layers interface check')
    window.decks.append(layers)
    modes = []
    try:
        for index in range(len(window.decks)):
            window.selected = index
            window.apply_deck()
            start = time.monotonic()
            while window.renderer is None and window.clip is None:
                app.processEvents()
                time.sleep(.005)
                if time.monotonic()-start>15:
                    raise AssertionError(window.status.text())
            assert window.board.frame is not None
            modes.append(window.current()['mode'])
            window.grab().save(str(Path(folder)/f'Cutroom-{window.current()["mode"]}.png'))
        window.selected = 1
        window.apply_deck()
        assert window.mode.currentIndex()==1
        window.strength.spin.setValue(12)
        assert window.strength.slider.value()==12
        assert window.workspace()['decks'][1]['depth']['strength']==.12
        assert window.tabs.count()==len(projects)+1
        start = time.monotonic()
        while window.renderer is None:
            app.processEvents()
            time.sleep(.005)
            if time.monotonic()-start>15:
                raise AssertionError(window.status.text())
        from PySide6.QtCore import QPoint, QRect
        app.processEvents()
        board_height = window.board.height()
        window.adjust_image()
        app.processEvents()
        assert window.board.height()==board_height
        for size in ((1180,920),(960,720),(1558,1157)):
            window.resize(*size)
            app.processEvents()
            def rect(widget):
                return QRect(widget.mapTo(window,QPoint(0,0)),widget.size())
            assert not rect(window.board).intersects(rect(window.inspectors))
            assert not rect(window.inspectors).intersects(rect(window.angle))
            for adjustment in window.positions.values():
                assert adjustment.rect().contains(adjustment.slider.geometry())
                assert adjustment.rect().contains(adjustment.spin.geometry())
            window.grab().save(str(Path(folder)/f'Cutroom-layout-{size[0]}x{size[1]}.png'))
        assert not window.windowIcon().isNull()
        return dict(frontend='Cutroom / Qt',preview_modes=modes,sliders=True,responsive_layout=True)
    finally:
        window.baseline = window.workspace()
        window.close()
        window.poll_timer.stop()
        window.animation_timer.stop()
        window.preview_timer.stop()
