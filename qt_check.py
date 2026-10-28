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
    layers.update(mode='layers',name='Layers interface check',middle_image=projects[0]['images'][0])
    window.decks.append(layers)
    for mode in ('ghost','depth'):
        smooth=copy.deepcopy(window.decks[1])
        smooth.update(mode=mode,lenticular=False,name=f'{mode} smooth interface check')
        window.decks.append(smooth)
    for mode in ('metal','ink','window','liquid'):
        deck=copy.deepcopy(window.decks[0])
        deck.update(mode=mode,name=f'{mode} interface check')
        if mode=='metal':deck['images']=[deck['images'][0],None]
        if mode=='window':deck['middle_image']=projects[0]['images'][0]
        window.decks.append(deck)
    for mode in ('neon','classic'):
        deck=copy.deepcopy(window.decks[0]);deck.update(mode=mode,name=mode+' new interface check')
        if mode=='neon':deck['neon']=dict(selection='mask',brightness=1)
        else:deck['extra_images']=projects[0]['images']
        window.decks.append(deck)
    modes = []
    try:
        for index in range(len(window.decks)):
            window.selected = index
            window.apply_deck()
            start = time.monotonic()
            while (window.renderer is None and window.clip is None) or window.board.frame is None or window.last_key is None or window.last_key[0]!=window.revision:
                app.processEvents()
                time.sleep(.005)
                if time.monotonic()-start>15:
                    raise AssertionError(window.status.text())
            assert window.board.frame is not None
            if window.current()['mode']=='layers':
                assert window.renderer.mode=='layers3'
                assert window.placement_choice.count()==3
                assert all(c.isVisible() for c in window.layer_depth_controls)
            if window.current()['mode']=='ink':
                assert all(c.isVisible() for c in (window.ink_strength,window.ink_contrast,window.ink_invert))
                window.ink_strength.spin.setValue(65)
                window.ink_contrast.spin.setValue(175)
                window.ink_invert.setChecked(True)
                window.ink_showthrough.spin.setValue(35)
                cfg=window.workspace()['decks'][index]['ink']
                assert cfg==dict(strength=.65,contrast=1.75,invert=True,showthrough=.35,background_colour='#242c42',revealed_colour='#88c0d3')
                window.apply_deck()
                assert window.ink_strength.value()==65 and window.ink_invert.isChecked()
            if window.current()['mode']=='liquid':
                assert window.renderer.mode=='liquid'
                assert all(c.isVisible() for c in (window.liquid_colour,window.liquid_cloud,window.liquid_depth,window.liquid_amount,window.liquid_thickness))
                window.liquid_amount.spin.setValue(73)
                window.liquid_cloud.spin.setValue(42)
                window.liquid_thickness.spin.setValue(66)
                cfg=window.workspace()['decks'][index]['liquid']
                assert cfg['amount']==.73 and cfg['cloudiness']==.42 and cfg['thickness']==.66
            modes.append(window.current()['mode'])
            window.grab().save(str(Path(folder)/f'Cutroom-{window.current()["mode"]}.png'))
        window.selected = 1
        window.apply_deck()
        assert window.current()['mode']=='depth'
        window.strength.spin.setValue(12)
        assert window.strength.slider.value()==12
        assert window.workspace()['decks'][1]['depth']['strength']==.12
        assert window.tabs.count()==len(projects)+9
        start = time.monotonic()
        while window.renderer is None or window.last_key is None or window.last_key[0]!=window.revision:
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
        window.view_mode.setCurrentText('3D')
        app.processEvents()
        assert window.board.view_mode=='3D'
        window.grab().save(str(Path(folder)/'preview-3d.png'))
        window.enlarge()
        app.processEvents()
        assert window.large_board.view_mode=='3D'
        window.view_mode.setCurrentText('2D')
        app.processEvents()
        assert window.board.view_mode==window.large_board.view_mode=='2D'
        window.large.close()
        window.close_placement()
        window.selected = 0
        window.apply_deck()
        start = time.monotonic()
        while window.renderer is None or window.display_revision != window.revision:
            app.processEvents(); time.sleep(.005)
            if time.monotonic()-start>30: raise AssertionError(window.status.text())
        window.view_mode.setCurrentText('3D')
        window.preview_orbit_changed(35,20,False)
        assert window.angle.value()>50
        window.export_preview.setChecked(True)
        start = time.monotonic()
        while window.texture_worker or window.last_key is None or not window.last_key[-1]:
            app.processEvents(); time.sleep(.005)
            if time.monotonic()-start>60: raise AssertionError(window.status.text())
        assert window.active_preview_renderer() is window.export_renderer
        window.grab().save(str(Path(folder)/'preview-export-texture.png'))
        from unittest.mock import patch
        from qt_ui import QFileDialog, QMessageBox, QInputDialog
        exported = []
        window.export_mode.setCurrentIndex(0)
        def zip_export(projects, destination, progress, **options):
            exported.append((projects,destination,options))
            return Path(destination)
        with patch.object(QFileDialog,'getSaveFileName',return_value=(str(Path(folder)/'Native UI Check.zip'),'Installable ReSkate ZIP (*.zip)')), \
             patch.object(window,'native_export_options',return_value=dict(game_root='test-game',compiler='test-compiler')), \
             patch('native_export.export_zip',side_effect=zip_export), \
             patch.object(QMessageBox,'information') as message:
            window.export(False)
            start=time.monotonic()
            while window.busy:
                app.processEvents();time.sleep(.005)
                if time.monotonic()-start>15:raise AssertionError('ZIP export UI timed out')
            assert len(exported)==1 and len(exported[0][0])==1
            assert exported[0][2]['title']=='Native UI Check'
            assert 'No manual Studio import' in message.call_args.args[2]
        import tempfile
        with tempfile.TemporaryDirectory(prefix='folder-ui-',dir=folder) as native_parent:
            def folder_export(projects,destination,progress,**options):
                Path(destination).mkdir(parents=True)
                exported.append((projects,destination,options))
                return Path(destination)
            window.export_mode.setCurrentIndex(1)
            assert window.export_button.text()=='Install deck'
            with patch.object(QInputDialog,'getText',return_value=('My Named Pack',True)), \
                 patch.object(QFileDialog,'getSaveFileName',side_effect=AssertionError('Install must not ask for an export file')), \
                 patch.object(window,'native_export_options',return_value=dict(game_root=native_parent,compiler='test-compiler')), \
                 patch('native_export.export_folder',side_effect=folder_export), \
                 patch.object(QMessageBox,'information') as message:
                window.export(False)
                start=time.monotonic()
                while window.busy:
                    app.processEvents();time.sleep(.005)
                    if time.monotonic()-start>15:raise AssertionError('Folder export UI timed out')
                assert len(exported)==2 and Path(exported[-1][1]).is_dir()
                assert Path(exported[-1][1])==Path(native_parent)/'Mods'/'My Named Pack'
                assert exported[-1][2]['title']=='My Named Pack'
                assert 'Deck pack installed' in message.call_args.args[2]
            with patch.object(QInputDialog,'getText',return_value=('',False)), \
                 patch.object(window,'native_export_options',side_effect=AssertionError('Cancelled install must stop')):
                window.export(False)
                assert not window.busy and len(exported)==2
            window.export_mode.setCurrentIndex(0)
        return dict(frontend='Cutroom / Qt',preview_modes=modes,sliders=True,responsive_layout=True,
                    view_switch=True,standard_deck_uv_mapping=True,camera_linked=True,export_texture_preview=True,native_zip_export=True,native_folder_export=True)
    finally:
        window.baseline = window.workspace()
        window.close()
        window.poll_timer.stop()
        window.animation_timer.stop()
        window.preview_timer.stop()
