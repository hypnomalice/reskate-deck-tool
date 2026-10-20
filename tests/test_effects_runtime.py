from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import deck_archive
from effects_runtime import ABI, build_runtime, migrate_file, shared_keys, split_pack, write_runtime_export
from fbmod_compat import Archive, compatible


def resources(data):
    archive = Archive(data)
    return {archive.key(i): archive.blobs[i] for i in range(len(archive.blobs))}


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fbmod_compat import pack
        # Structural fixture: pixels are irrelevant to resource partitioning.
        cls.original = deck_archive.build([
            dict(name='Runtime fixture', mode='classic', texture=bytes(2097152),
                 texture_size=(512, 4096), texture_mips=1, resident=True,
                 thumb_small=bytes(65536), thumb_large=bytes(589824))
        ], pack, 'Runtime fixture', 'Test', independent_shader=True)

    def test_partition_preserves_every_normalized_resource(self):
        content, runtime, contract = split_pack(self.original)
        normalized, _ = compatible(self.original)
        left, right = resources(content), resources(runtime)
        self.assertFalse(left.keys() & right.keys())
        self.assertEqual(left | right, resources(normalized))
        self.assertFalse(left.keys() & shared_keys())
        self.assertTrue(all(key in shared_keys() for key in right))
        self.assertEqual(contract['abi'], ABI)
        self.assertFalse(contract['third_party_compatibility_verified'])

    def test_runtime_contains_no_deck_items_or_private_materials(self):
        _, runtime, _ = split_pack(self.original)
        for _, name in resources(runtime):
            self.assertFalse(name.startswith('items/board_bottomart/'))
            self.assertFalse(name.startswith('characters/maincharacters/reskate/shaders/'))

    def test_migration_keeps_original_and_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, content, runtime = (root / n for n in ('old.fbmod', 'content.fbmod', 'runtime.fbmod'))
            source.write_bytes(self.original)
            migrate_file(source, content, runtime)
            before = content.read_bytes()
            with self.assertRaises(FileExistsError):
                migrate_file(source, content, runtime)
            self.assertEqual(source.read_bytes(), self.original)
            self.assertEqual(content.read_bytes(), before)

    def test_runtime_is_deterministic_and_can_be_reused(self):
        self.assertEqual(build_runtime(), build_runtime())
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_runtime_export(self.original, root/'one.fbmod')
            first = (root/'ReSkate Effects Runtime.fbmod').read_bytes()
            write_runtime_export(self.original, root/'two.fbmod')
            self.assertEqual((root/'ReSkate Effects Runtime.fbmod').read_bytes(), first)
            self.assertEqual((root/'one.fbmod').read_bytes(), (root/'two.fbmod').read_bytes())

    def test_failed_export_rolls_back_previously_committed_files(self):
        import os
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            destination = root/'deck.fbmod'
            destination.write_bytes(b'previous export')
            original_replace = os.replace
            def fail_contract(source, target):
                if Path(target).suffix == '.json':
                    raise OSError('Simulated disk failure')
                return original_replace(source, target)
            with patch('effects_runtime.os.replace', side_effect=fail_contract):
                with self.assertRaises(OSError):
                    write_runtime_export(self.original, destination, overwrite=True)
            self.assertEqual(destination.read_bytes(), b'previous export')
            self.assertFalse((root/'ReSkate Effects Runtime.fbmod').exists())
            self.assertFalse(destination.with_suffix('.runtime.json').exists())


if __name__ == '__main__':
    unittest.main()
