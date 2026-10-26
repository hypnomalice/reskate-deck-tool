import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageDraw
import numpy as np
import creator_engine
import preview_texture
from fbmod_compat import Archive, unpack


class ExportPreviewTests(unittest.TestCase):
    def test_texture_only_matches_real_export_without_building_a_mod(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            art = Image.new('RGB',(64,256),'#4b779a')
            ImageDraw.Draw(art).rectangle((0,0,31,127),fill='#d67c43')
            depth = Image.new('L',art.size,128)
            art.save(root/'art.png'); depth.save(root/'depth.png')
            project = dict(name='Preview parity',mode='ghost',images=[str(root/'art.png'),str(root/'depth.png')],
                           fit='Stretch',background='#000000',placement=[dict(zoom=1.2,x=.1,y=-.1),{}],
                           ghost={'silver':{'selection':'colour','colour':'#d67c43','tolerance':.1}})
            original = copy.deepcopy(project)
            with patch.object(creator_engine.deck_archive,'build',side_effect=AssertionError('Texture check must not build a mod')):
                texture = creator_engine.export_texture(project)
            self.assertEqual(project,original)
            self.assertEqual(set(p.name for p in root.iterdir()),{'art.png','depth.png'})
            creator_engine.export_pack([project],root/'real.fbmod',title='Parity',shared_runtime=True)
            exported = Archive((root/'real.fbmod').read_bytes())
            chunks = [unpack(exported.blobs[i]) for i in range(len(exported.blobs)) if exported.key(i)[0]==3]
            self.assertIn(texture['texture'],chunks)
            decoded = preview_texture.decode_bc7(texture['texture'],texture['texture_size'])
            self.assertEqual(decoded.size,(512,4096))
            self.assertGreater(decoded.getpixel((64,56))[0],100)
            self.assertLess(decoded.getpixel((64,56))[1],5)
            with patch.object(creator_engine,'export_texture',return_value=texture):
                renderer = preview_texture.prepare(project,'ghost')
            from effect_preview import linear
            np.testing.assert_array_equal(renderer.pixels,linear(decoded))

    def test_incomplete_or_invalid_texture_is_reported(self):
        with self.assertRaises(ValueError): preview_texture.decode_bc7(b'',(16,16))
        with self.assertRaises(ValueError): preview_texture.decode_bc7(b'',(0,16))


if __name__=='__main__': unittest.main()
