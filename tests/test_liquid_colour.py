from pathlib import Path
import sys,unittest,tempfile,json
from PIL import Image
import transparency_finish as finish
import transparency_native as native
from transparency_preview import TransparencyPreview

class LiquidColourTests(unittest.TestCase):
    def test_default_and_validation(self):
        self.assertEqual(finish.settings('glass',dict(finish='liquid'))['liquid_colour'],'#22aca6')
        for value in [None,False,[1,2,3],'bad colour','#ffffff00']:
            with self.subTest(value=value),self.assertRaises(ValueError):
                finish.settings('glass',dict(finish='liquid',liquid_colour=value))
        self.assertEqual(finish.settings('glass',dict(finish='liquid',liquid_colour='RED'))['liquid_colour'],'#ff0000')

    def test_colour_is_exported_independently_from_glass_tint_and_motion(self):
        with tempfile.TemporaryDirectory() as folder:
            p=dict(name='Liquid Red',mode='glass',glass=dict(finish='liquid',liquid_colour='#ff0000',tint='#0000ff',opacity=.65,viscosity=.4))
            native.write_materials([p],folder)
            data=json.loads((Path(folder)/'reskate-materials.json').read_text())
            values={v['guid']:v['default'] for v in data['materials'][0]['parameters']}
            self.assertEqual(len(values),3)
            self.assertEqual(values['f2750d14eec871a459ff5e8801001713'],[.65,.4,1])
            import transparency_vertex
            record=transparency_vertex.constants('glass',p['glass'])
            self.assertEqual(record[:3],(0,0,1))
            self.assertEqual(record[8:11],(1,0,0))
            self.assertEqual(p['glass']['tint'],'#0000ff')

    def test_colour_changes_only_wet_area_in_preview(self):
        atlas=finish.artwork_atlas(Image.new('RGBA',(512,2048),(0,0,0,0)))
        red=TransparencyPreview(atlas,'glass',dict(finish='liquid',liquid_colour='#ff0000')).render(0,(128,512))
        blue=TransparencyPreview(atlas,'glass',dict(finish='liquid',liquid_colour='#0000ff')).render(0,(128,512))
        self.assertEqual(red.getpixel((64,100)),blue.getpixel((64,100)))
        self.assertNotEqual(red.getpixel((64,400)),blue.getpixel((64,400)))
        self.assertEqual(red.getchannel('A').tobytes(),blue.getchannel('A').tobytes())

    def test_colour_picker_survives_project_round_trip(self):
        import os
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from unittest.mock import patch
        from PySide6.QtWidgets import QWidget,QVBoxLayout
        from PySide6.QtGui import QColor
        from qt_ui import application,Adjustment
        import transparency_ui
        app=application()
        class Owner(QWidget):
            def __init__(self):
                super().__init__()
                self.deck=dict(mode='glass',glass=dict(finish='liquid',tint='#334455'))
                self.changes=0
            def current(self):return self.deck
            def changed(self):self.changes+=1
        owner=Owner()
        transparency_ui.install(owner,QVBoxLayout(owner),Adjustment)
        transparency_ui.apply(owner,owner.deck)
        self.assertFalse(owner.glass_liquid_colour.isHidden())
        with patch.object(transparency_ui.QColorDialog,'getColor',return_value=QColor('#ff9900')):
            owner.glass_liquid_colour.click()
        transparency_ui.remember(owner,owner.deck)
        owner.deck=json.loads(json.dumps(owner.deck))
        transparency_ui.apply(owner,owner.deck)
        self.assertEqual(owner.deck['glass']['liquid_colour'],'#ff9900')
        self.assertEqual(owner.deck['glass']['tint'],'#334455')
        self.assertEqual(owner.glass_liquid_colour.text(),'Liquid colour #ff9900')
        owner.deck['glass']['finish']='display'
        transparency_ui.apply(owner,owner.deck)
        self.assertTrue(owner.glass_liquid_colour.isHidden())
        owner.close()

    def test_colour_reaches_every_shell_vertex_without_changing_other_streams(self):
        import struct,uuid
        from fbmod_compat import Archive,unpack
        import transparency_vertex as optical
        seed=Path(native.__file__).resolve().parent/'assets/transparency/vertex-liquid-transparent-mesh.fbmod'
        original=Archive(seed.read_bytes())
        changed=Archive(original.bytes())
        cfg=dict(finish='liquid',liquid_colour='#ff6600',rim_mm=17)
        optical.patch_mesh(changed,13,'glass',cfg)
        before=unpack(original.blobs[13]);after=unpack(changed.blobs[13])
        u=lambda b,at:struct.unpack_from('<I',b,at)[0]
        ptr=lambda b,at:struct.unpack_from('<Q',b,at)[0]+16
        record=struct.pack('<12e',*optical.constants('glass',cfg))
        self.assertEqual(struct.unpack('<12e',record)[8:11],(1,struct.unpack('<e',struct.pack('<e',.4))[0],0))
        self.assertEqual(struct.unpack('<12e',record)[11],17)
        for lod in range(6):
            old_lod=ptr(before,48+8*lod);new_lod=ptr(after,48+8*lod)
            old_sections=ptr(before,old_lod+12);new_sections=ptr(after,new_lod+12)
            chunk=original.find(3,str(uuid.UUID(bytes_le=before[old_lod+116:old_lod+132])))
            old_data=unpack(original.blobs[chunk]);new_data=unpack(changed.blobs[chunk])
            self.assertEqual(old_data[u(before,old_lod+92):],new_data[u(after,new_lod+92):])
            for section in range(u(before,old_lod+8)):
                old=old_sections+384*section;new=new_sections+384*section
                decl=old+112;count=u(before,old+44)
                length=count*sum(before[decl+64+2*s] for s in range(before[decl+97]))
                old_offset=u(before,old+40);new_offset=u(after,new+40)
                self.assertEqual(old_data[old_offset:old_offset+length],new_data[new_offset:new_offset+length])
                if section in (0,1):
                    self.assertEqual(new_data[new_offset+length:new_offset+length+24*count],record*count)
                    self.assertEqual(after[new+112+64+12],24)
        self.assertEqual(optical.constants('glass',dict(finish='display'))[8:11],(140,0,0))
