import json,tempfile,unittest,os,subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PIL import Image,ImageDraw
import jiggle_effect,jiggle_native,jiggle_preview,jiggle_preview_ui
from effect_preview import AtlasPreview


class PreviewTests(unittest.TestCase):
    def test_render_delay_does_not_reset_spring_return(self):
        project=dict(mode='jiggle',images=['art.png'],jiggle=dict(amount=65,stiffness=50))
        owner=SimpleNamespace(current=lambda:project,spring_box=SimpleNamespace(setVisible=lambda _:None),
            isVisible=lambda:True,isMinimized=lambda:False,selected=0,spring_identity=None,
            spring_demo=None,spring_clock=0,board=SimpleNamespace(yaw=0,pitch=0),render=lambda:None)
        with patch.object(jiggle_preview_ui.time,'monotonic',return_value=.2):jiggle_preview_ui.tick(owner)
        owner.board.yaw=35
        with patch.object(jiggle_preview_ui.time,'monotonic',return_value=.4):jiggle_preview_ui.tick(owner)
        self.assertGreater(np.abs(owner.jiggle_solver.particles[:,:2]).max(),.001)
        for i in range(1,101):
            with patch.object(jiggle_preview_ui.time,'monotonic',return_value=.4+i*.2):jiggle_preview_ui.tick(owner)
        self.assertLess(np.abs(owner.jiggle_solver.particles).max(),.0001)

    def test_exports_only_authored_material_data(self):
        with tempfile.TemporaryDirectory() as folder:
            jiggle_native.write_materials([dict(name='Example',mode='jiggle',jiggle=dict(amount=81,stiffness=27,attachment='both'))],folder)
            root=Path(folder)
            self.assertEqual([p.name for p in root.iterdir()],['reskate-materials.json'])
            data=json.loads((root/'reskate-materials.json').read_text())
            self.assertEqual(data['materials'][0]['parameters'][-1]['default'],[.81,.27,1])
            checker=os.environ.get('SDEC_MATERIAL_CHECKER')
            if checker:subprocess.run([checker,str(root/'reskate-materials.json')],check=True,capture_output=True,text=True)

    def test_bare_fbmod_is_rejected_before_choosing_an_output(self):
        from qt_ui import Creator,application
        from unittest.mock import patch
        app=application()
        with patch.object(Creator,'check_updates',lambda self:None):owner=Creator()
        try:
            owner.decks[0].update(mode='jiggle',images=['art.png',None],jiggle=dict(amount=65,stiffness=50))
            owner.apply_deck()
            previous_mode=owner.export_mode.currentIndex()
            owner.export_mode.blockSignals(True)
            owner.export_mode.setCurrentIndex(owner.export_mode.findData('fbmod'))
            with patch('qt_ui.QMessageBox.warning') as warning,patch('qt_ui.QFileDialog.getSaveFileName') as choose:
                owner.export(False)
                warning.assert_called_once()
                self.assertIn('Mod ZIP',warning.call_args.args[2])
                choose.assert_not_called()
        finally:
            if owner.export_mode.signalsBlocked():
                owner.export_mode.setCurrentIndex(previous_mode);owner.export_mode.blockSignals(False)
            owner.preview_timer.stop();owner.poll_timer.stop();owner.animation_timer.stop();owner.spring_timer.stop()
            owner.baseline=owner.workspace();owner.close()

    @unittest.skipIf(jiggle_preview._render is None,'Native preview helper not built')
    def test_accelerated_pixels_match_reference(self):
        with tempfile.TemporaryDirectory() as folder:
            mask=Image.new('L',(512,2048));ImageDraw.Draw(mask).ellipse((70,900,440,1390),fill=255)
            path=Path(folder)/'mask.png';mask.save(path)
            rng=np.random.default_rng(21);art=Image.fromarray(rng.integers(0,256,(2048,512,3),dtype=np.uint8))
            renderer=AtlasPreview(jiggle_effect.pack(art,Image.linear_gradient('L').resize((512,2048)),dict(mask=str(path))),'jiggle')
            for attachment in ('top','both'):
                renderer.jiggle_attachment=attachment;renderer.jiggle_particles=rng.uniform(-.65,.65,(2,4))
                for region in ((0,0,1,1),(.1,.4,.9,.75)):
                    fast=renderer.render(.3,(64,100),region,view_pose=(35,-12))
                    with patch.object(jiggle_preview,'_render',None):slow=renderer.render(.3,(64,100),region,view_pose=(35,-12))
                    # White noise magnifies float32 coordinate rounding at texture edges.
                    delta=np.abs(np.asarray(fast).astype(int)-np.asarray(slow).astype(int))
                    self.assertLessEqual(delta.max(),4)
                    self.assertLess(delta.mean(),.1)
