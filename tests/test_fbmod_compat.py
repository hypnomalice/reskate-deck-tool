from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import creator_engine
from fbmod_compat import Archive, UnsupportedMod, compatible, unpack, update_file


class CompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.root = Path(cls.folder.name)
        images = []
        for index, colour in enumerate(('red', 'blue')):
            path = cls.root/f'{index}.png'
            Image.new('RGB', (32,128), colour).save(path)
            images.append(str(path))
        cls.source = cls.root/'older.fbmod'
        with patch('fbmod_compat.compatible', side_effect=lambda data: (data,1)):
            creator_engine.export_pack([dict(name='Compatibility test',images=images)],cls.source)
        cls.original = cls.source.read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_upgrade_is_repeatable_and_keeps_original(self):
        updated, decks = compatible(self.original)
        self.assertEqual(decks,1)
        self.assertEqual(compatible(updated)[0],updated)
        self.assertEqual(self.source.read_bytes(),self.original)
        archive = Archive(updated)
        self.assertIsNotNone(archive.find(2,'characters/lua/luaskateboardcompositor'))
        headers = [unpack(archive.blobs[i]) for i in range(len(archive.blobs))
                   if archive.key(i)[0]==2 and archive.key(i)[1].endswith('_color')]
        self.assertEqual(len(headers),1)
        self.assertEqual(headers[0][30:34],bytes((1,0,0,1)))

    def test_saved_copies_do_not_overwrite_files(self):
        destination = self.root/'compatible.fbmod'
        self.assertEqual(update_file(self.source,destination),1)
        before = destination.read_bytes()
        for path in (self.source,destination):
            with self.assertRaises(ValueError):
                update_file(self.source,path)
        self.assertEqual(destination.read_bytes(),before)
        self.assertEqual(self.source.read_bytes(),self.original)

    def test_unknown_shader_is_rejected(self):
        archive = Archive(self.original)
        index = next(i for i in range(len(archive.blobs)) if archive.key(i)[1].startswith('shaders/bytecode/'))
        raw = bytearray(unpack(archive.blobs[index]))
        raw[-1] ^= 1
        archive.replace(index,raw)
        with self.assertRaises(UnsupportedMod):
            compatible(archive.bytes())

    def test_truncated_file_leaves_no_output(self):
        source,destination = self.root/'broken.fbmod',self.root/'not-written.fbmod'
        source.write_bytes(self.original[:40])
        with self.assertRaises(UnsupportedMod):
            update_file(source,destination)
        self.assertFalse(destination.exists())
