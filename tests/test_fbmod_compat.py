from pathlib import Path
import tempfile
import struct
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
        count_at = archive.prefix.index(b'\0\xff\xff\xff\xffIcon') - 4
        self.assertEqual(struct.unpack_from('<I',archive.prefix,count_at)[0],len(archive.blobs)+5)
        self.assertEqual(updated[:12],self.original[:12])
        self.assertEqual(updated[24:count_at],self.original[24:count_at])
        self.assertEqual(updated[count_at+4:len(archive.prefix)],self.original[count_at+4:len(archive.prefix)])
        self.assertIsNotNone(archive.find(2,'characters/lua/luaskateboardcompositor'))
        headers = [unpack(archive.blobs[i]) for i in range(len(archive.blobs))
                   if archive.key(i)[0]==2 and archive.key(i)[1].endswith('_color')]
        self.assertEqual(len(headers),1)
        self.assertEqual(headers[0][30:34],bytes((1,0,0,1)))

    def test_repairs_the_incorrect_metadata_count_from_beta_1(self):
        broken = bytearray(compatible(self.original)[0])
        archive = Archive(broken)
        at = archive.prefix.index(b'\0\xff\xff\xff\xffIcon') - 4
        struct.pack_into('<I',broken,at,len(archive.blobs))
        repaired, _ = compatible(broken)
        self.assertEqual(repaired,compatible(self.original)[0])

    def test_empty_texture_is_available_without_the_probe_mod(self):
        archive = Archive(compatible(self.original)[0])
        asset = archive.descriptors[archive.find(1,'characters/customization/reskate/board_bottomart/lenticular_black_rgb')]
        lua = archive.descriptors[archive.find(2,'characters/lua/luaskateboardcompositor')]
        def bundles(descriptor):
            _, end, _ = creator_engine.deck_archive.descriptor_parts(descriptor)
            count = struct.unpack_from('<I',descriptor,end+1)[0]
            return struct.unpack_from('<'+str(count)+'I',descriptor,end+5)
        self.assertEqual(len(bundles(asset)),6)
        self.assertEqual(bundles(asset),bundles(lua))

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
