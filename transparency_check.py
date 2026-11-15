"""Offscreen checks for the shipped transparency UI, preview and native exporter."""
from pathlib import Path
import copy,json,os,time,traceback


def check(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    report={'ok':False};window=None
    try:
        from PIL import Image,ImageDraw
        from qt_ui import application,Creator,default_deck,MODES
        from transparency_preview import TransparencyPreview
        app=application();art=folder/'art.png'
        if not art.exists():
            im=Image.new('RGB',(512,2048),'#b39261');draw=ImageDraw.Draw(im);draw.rectangle((45,180,466,1940),fill='#233654');draw.polygon([(80,1600),(430,350),(410,1800)],fill='#f4d9ab');im.save(art)
        window=Creator();window.show();window.decks=[]
        from PySide6.QtWidgets import QLabel
        from PySide6.QtGui import QAction
        dependency=[label for label in window.findChildren(QLabel)
                    if 'thunderstore.io/c/reskate/p/IdolRiot/Sofis_Deck_Effect_Core/' in label.text()]
        assert dependency and dependency[0].openExternalLinks()
        assert not any('Save matching SDEC' in action.text() for action in window.findChildren(QAction))
        definitions=[('glass',{'tint':'#123456','tint_strength':.61}),('case',{'haze':.73,'future_note':'retained'}),('crystal',{'tint':'#9474d2'}),('glass',{'finish':'water'}),('case',{'interior':'pcb'}),('glass',{'finish':'liquid','liquid_colour':'#eaa324'})]
        for index,(mode,cfg) in enumerate(definitions):
            d=default_deck();d.update(name=['SDEC Tool Display Glass','SDEC Tool Hazy Artwork Case','SDEC Tool Cut Crystal','SDEC Tool Water Shell','SDEC Tool Hazy PCB Case','SDEC Tool Liquid in Glass'][index],mode=mode,images=[str(art.resolve()),None]);d[mode]=cfg;window.decks.append(d)
        def wait_preview():
            start=time.monotonic()
            while window.worker or window.renderer is None or window.last_key is None or window.last_key[0]!=window.revision:
                app.processEvents();time.sleep(.005)
                if time.monotonic()-start>25:
                    import sys,threading
                    stacks={t.name:''.join(traceback.format_stack(sys._current_frames()[t.ident])) for t in threading.enumerate() if t.ident in sys._current_frames()}
                    (folder/'worker-stacks.json').write_text(json.dumps(stacks,indent=2),encoding='utf8')
                    raise AssertionError('Preview did not finish: '+window.status.text()+' state='+repr(dict(index=window.selected,worker=window.worker,frame=window.frame_worker,revision=window.revision,display=window.display_revision,last=window.last_key,pending=window.pending)))
        screenshots=[]
        for index in range(len(window.decks)):
            window.selected=index;window.apply_deck();window.inspector_tabs.setCurrentIndex(1);wait_preview()
            assert isinstance(window.renderer,TransparencyPreview)
            assert window.transparency_box.isVisible() and not window.case_box.isVisible() and not window.crystal_box.isVisible()
            assert window.placement_choice.count()==1
            if index==5:
                assert window.glass_liquid_colour is not window.liquid_colour
                assert window.glass_liquid_colour.isVisible() and not window.liquid_colour.isVisible()
                from unittest.mock import patch
                from PySide6.QtGui import QColor
                with patch('transparency_ui.QColorDialog.getColor',return_value=QColor('#eaa324')):
                    window.glass_liquid_colour.click()
                window.remember()
                assert window.current()['glass']['liquid_colour']=='#eaa324'
                assert window.glass_liquid_colour.text()=='Liquid colour #eaa324'
            before=copy.deepcopy(window.current().get(window.current()['mode'],{}));window.transparency_controls['reflection_strength'].spin.setValue(137);window.remember();wait_preview()
            cfg=window.current()[window.current()['mode']];assert cfg['reflection_strength']==1.37
            if 'tint' in before:assert cfg['tint']==before['tint']
            if 'future_note' in before:assert cfg['future_note']==before['future_note']
            window.renderer.render(.35,(128,512)).save(folder/('material-'+str(index)+'.png'))
            shot=folder/('interface-'+str(index)+'.png');window.grab().save(str(shot));screenshots.append(str(shot))
        # Switching modes may not rewrite the inactive material's stored settings.
        window.selected=1;window.apply_deck();window.transparency_controls['haze'].spin.setValue(83);window.remember();stored=copy.deepcopy(window.current()['case'])
        window.mode.setCurrentIndex(list(MODES).index('classic'));window.remember();assert window.current()['case']==stored
        window.mode.setCurrentIndex(list(MODES).index('case'));window.remember();assert window.current()['case']==stored
        window.transparency_style.setCurrentIndex(1);window.remember();assert window.current()['case']['finish']=='glossy';assert not window.transparency_controls['haze'].isEnabled();assert window.current()['case']['roughness']==.04
        window.transparency_style.setCurrentIndex(0);window.remember();window.transparency_controls['haze'].spin.setValue(83)
        workspace=window.workspace();path=folder/'Round trip.json';path.write_text(json.dumps(workspace,indent=2),encoding='utf8');window.load_project(path)
        for old,new in zip(workspace['decks'],window.decks):
            for mode in ('glass','case','crystal'):
                if mode in old:assert old[mode]==new[mode],(mode,old[mode],new[mode])
        wait_preview();projects=window.workspace()['decks']
        # The compressed texture inspector uses the same material renderer.
        import preview_texture
        decoded=preview_texture.prepare(projects[0],'glass');assert isinstance(decoded,TransparencyPreview);assert decoded.optics['tint']=='#123456';decoded.render(.2,(128,512)).save(folder/'Decoded texture material.png')
        water=window.decks[3];from transparency_finish import artwork_atlas
        preview=TransparencyPreview(artwork_atlas(Image.open(art)),'glass',water['glass']);preview.clock_seconds=0;a=preview.render(.35,(128,512)).tobytes();preview.clock_seconds=1;b=preview.render(.35,(128,512)).tobytes();assert a!=b
        native=False
        if (folder/'compile-config.json').exists():
            import native_export
            setup=json.loads((folder/'compile-config.json').read_text());native_export.export_zip(projects,folder/'UI transparency export.zip',title='UI Transparency Export Check',**setup);native=True
            if (folder/'visual-project.json').exists():
                window.load_project(folder/'visual-project.json')
                native_export.export_zip(window.workspace()['decks'],folder/'SDEC Tool Finish Examples.zip',title='SDEC Tool Finish Examples',**setup)
        report=dict(ok=True,modes=['Glass','Clear Case','Crystal'],previews=6,independent_liquid_colour_picker=True,project_round_trip=True,inactive_settings_preserved=True,decoded_texture_preview=True,water_animation=True,native_export=native,separate_core_required=True,screenshots=screenshots)
    except Exception:report=dict(ok=False,error=traceback.format_exc())
    finally:
        if window is not None:
            window.baseline=window.workspace();window.hide();window.animation_timer.stop();window.preview_timer.stop()
        (folder/'transparency-check.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    return report
