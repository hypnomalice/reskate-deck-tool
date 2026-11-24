"""Packaged-app verification of the shaker editor, motion and ZIP export."""
from pathlib import Path
import os,json,time,traceback

def check(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    # The external compiler must use a normal, inspectable staging directory.
    import tempfile
    tempfile.tempdir=str(folder.resolve())
    report={'ok':False};owner=None;settings_patch=None
    try:
        from PIL import Image,ImageDraw
        from unittest.mock import patch
        from PySide6.QtWidgets import QFileDialog,QMessageBox
        from PySide6.QtCore import QSettings
        # Test the actual first-run setup without reading or changing the
        # user's registry preferences or portable export configuration.
        preferences=QSettings(str((folder/'preferences.ini').resolve()),QSettings.IniFormat)
        assert not preferences.contains('native/game') and not preferences.contains('native/compiler'), 'Self-test folder must have fresh preferences'
        from qt_ui import Creator,application,default_deck
        # The organization/application constructor uses the registry on Windows;
        # route only its storage to a real isolated INI for this self-test.
        settings_patch=patch('qt_ui.QSettings',lambda *args:QSettings(str((folder/'preferences.ini').resolve()),QSettings.IniFormat))
        settings_patch.start()
        from app_version import APP_VERSION
        from shaker_effect import prepare,parameters
        app=application()
        background=folder/'background.png';Image.new('RGB',(512,2048),'#253960').save(background)
        paths=[]
        for i,colour in enumerate(['#58df72','#ef9bd4','#f4d577']):
            image=Image.new('RGBA',(200,200));d=ImageDraw.Draw(image)
            if i==0:d.ellipse((15,15,185,185),fill=colour)
            elif i==1:d.rectangle((15,15,185,185),fill=colour)
            else:d.polygon([(100,8),(126,70),(193,75),(141,120),(160,190),(100,150),(40,190),(59,120),(7,75),(74,70)],fill=colour)
            path=folder/f'piece-{i}.png';image.save(path);paths.append(str(path.resolve()))
        project=default_deck('Shaker App Check');project.update(mode='shaker',images=[str(background.resolve()),None],fit='Crop to fill',shaker=dict(rim=True,blur=0,pieces=[dict(image=p,width_mm=45+i*4,weight=1+i*.5) for i,p in enumerate(paths)]))
        with patch.object(Creator,'check_updates',lambda self:None):owner=Creator()
        owner.decks=[project];owner.apply_deck();owner.show();owner.resize(1440,1000)
        def wait_preview():
            deadline=time.monotonic()+25
            while time.monotonic()<deadline:
                app.processEvents();time.sleep(.01)
                if owner.renderer and owner.renderer.mode=='shaker' and owner.board.frame is not None and owner.display_revision==owner.revision and owner.last_key and owner.last_key[0]==owner.revision:return
            raise AssertionError('Preview failed: '+owner.status.text())
        wait_preview()
        assert owner.shaker_count.currentIndex()==2 and owner.transparency_style.count()==1
        owner.shaker_rows[1]['width'].setValue(52);owner.shaker_rows[1]['weight'].setValue(2.5)
        owner.shaker_rows[0]['rim_width'].setValue(2.5);owner.shaker_rows[0]['rim_strength'].setValue(35)
        owner.shaker_rows[1]['rim_width'].setValue(.5);owner.shaker_rows[1]['rim_strength'].setValue(80)
        owner.shaker_blur.setValue(1.5);owner.remember()
        assert owner.current()['shaker']['pieces'][1]['weight']==2.5
        assert owner.current()['shaker']['pieces'][1]['width_mm']==52
        assert owner.current()['shaker']['blur']==1.5
        saved=folder/'Round trip.json'
        with patch.object(QFileDialog,'getSaveFileName',return_value=(str(saved),'Deck project (*.json)')):assert owner.save_project()
        owner.load_project(saved);wait_preview()
        assert owner.current()['shaker']['pieces'][1]['weight']==2.5
        assert owner.current()['shaker']['pieces'][0]['rim_mm']==2.5
        assert owner.current()['shaker']['pieces'][0]['rim_strength']==.35
        assert owner.shaker_rows[1]['rim_width'].value()==.5
        assert owner.shaker_rows[1]['rim_strength'].value()==80
        assert owner.transparency_grip.isChecked() and owner.transparency_grip.isEnabled()
        owner.transparency_grip.setChecked(False);owner.remember()
        assert owner.current()['glass']['grip_tape'] is False
        with patch.object(QFileDialog,'getSaveFileName',return_value=(str(saved),'Deck project (*.json)')):assert owner.save_project()
        owner.load_project(saved);wait_preview()
        assert not owner.transparency_grip.isChecked() and owner.transparency_grip.isEnabled()
        assert owner.current()['glass']['grip_tape'] is False
        owner.transparency_grip.setChecked(True);owner.remember()
        before=owner.renderer.poses.copy()
        for i in range(90):owner.renderer.advance(i*.6,15,1/120)
        assert abs(owner.renderer.poses-before).max()>.0001
        # Inspect tools are view state, not authored settings. Pause keeps the
        # actual solver pose, and the dimmer must reach the rendered snapshot.
        owner.shaker_demo.setChecked(True)
        deadline=time.monotonic()+1.5
        poses=[]
        while time.monotonic()<deadline:
            app.processEvents();time.sleep(.01);poses.append(owner.renderer.poses.copy())
        import numpy as np
        assert np.ptp(np.array(poses)[:,:,1])>.08,'Shake preview did not visibly move the pieces'
        owner.shaker_pause.setChecked(True);owner.shaker_dim.setChecked(True)
        still=owner.renderer.poses.copy();deadline=time.monotonic()+.3
        while time.monotonic()<deadline:app.processEvents();time.sleep(.01)
        np.testing.assert_array_equal(owner.renderer.poses,still)
        assert owner.renderer.dim_background
        owner.remember();assert 'dim_background' not in owner.current().get('shaker',{})
        owner.shaker_dim.setChecked(False);owner.shaker_demo.setChecked(False)
        # Real widgets and the real asynchronous Export ZIP command.
        owner.inspector_tabs.setCurrentIndex(1);app.processEvents()
        shot=folder/'Editor.png';owner.grab().save(str(shot))
        report.update(version=APP_VERSION,project_round_trip=True,independent_size_weight=True,independent_rim_width_strength=True,live_motion=True,pause_and_dimmer=True,native_grip=True,native_grip_optional=True,parameters=len(parameters(prepare(owner.current()))),screenshot=str(shot))
        config=folder/'compile-config.json'
        if config.exists():
            setup=json.loads(config.read_text());destination=folder/'Packaged Shaker Export.zip'
            import sys,native_export
            assert not Path(sys.executable).with_suffix('.export.json').exists(),'Do not use a portable export sidecar for the first-run check'
            with patch.object(QFileDialog,'getExistingDirectory',return_value=setup['game_root']) as choose_game,patch.object(QFileDialog,'getOpenFileName',return_value=(setup['compiler'],'Studio compiler (*.exe)')) as choose_compiler,patch.object(QMessageBox,'information'),patch.object(QMessageBox,'warning') as setup_warning:
                selected=owner.native_export_options()
                assert selected==setup and not setup_warning.called
                assert choose_game.call_count==1
                candidates=[Path(setup['game_root'])/f/'reskate_cli.exe' for f in ('Studio','Studio with Shaders')]
                if not any(native_export.supports_shared_core(p) for p in candidates):assert choose_compiler.call_count==1,'Legacy compiler was selected automatically'
            preferences.sync()
            assert preferences.value('native/game')==setup['game_root'] and preferences.value('native/compiler')==setup['compiler']
            with patch.object(QFileDialog,'getExistingDirectory') as choose_game,patch.object(QFileDialog,'getOpenFileName') as choose_compiler:
                assert owner.native_export_options()==setup
                choose_game.assert_not_called();choose_compiler.assert_not_called()
            report.update(fresh_export_setup=True,export_setup_persisted=True,legacy_compiler_not_autoselected=True)
            import copy,eink_mesh
            on=copy.deepcopy(owner.current());on['name']='Shaker App Check Grip On';on.setdefault('glass',{})['grip_tape']=True
            off=copy.deepcopy(on);off['name']='Shaker App Check Grip Off';off['glass']['grip_tape']=False
            owner.decks=[on,off];owner.selected=0;owner.apply_deck()
            with patch.object(QFileDialog,'getSaveFileName',return_value=(str(destination),'Mod ZIP (*.zip)')),patch.object(QMessageBox,'information'),patch.object(QMessageBox,'critical') as critical,patch.object(QMessageBox,'warning') as warning,patch.object(eink_mesh,'equipped_grip',wraps=eink_mesh.equipped_grip) as grip_export:
                owner.export_mode.setCurrentIndex(owner.export_mode.findData('zip'));owner.export(True)
                deadline=time.monotonic()+120
                while owner.busy and time.monotonic()<deadline:app.processEvents();time.sleep(.02)
                assert not owner.busy,'Export timed out'
                assert destination.exists() and not critical.called and not warning.called, str(critical.call_args or warning.call_args)
                assert grip_export.call_count==1 and grip_export.call_args.args[1]==[on['name']], 'Native grip was not isolated to the enabled shaker deck'
            import zipfile
            with zipfile.ZipFile(destination) as z:
                assert z.testzip() is None
                assert not any(n.endswith('.lua') or n.endswith('reskate-plugin.json') for n in z.namelist())
            report.update(native_export=True,content_only=True,export_zip=str(destination))
        report['ok']=True
    except Exception:
        report['error']=traceback.format_exc()
    finally:
        if owner:
            for name in ['preview_timer','poll_timer','animation_timer','spring_timer','shaker_timer']:getattr(owner,name).stop()
            owner.baseline=owner.workspace();owner.close()
        if settings_patch:settings_patch.stop()
        (folder/'check.json').write_text(json.dumps(report,indent=2)+'\n')
    if not report['ok']:raise RuntimeError(report['error'])
    return report
