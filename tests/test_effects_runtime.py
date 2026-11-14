from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import deck_archive
from effects_runtime import ABI, RUNTIME_NAME, build_runtime, migrate_file, shared_keys, split_pack, write_runtime_export
from fbmod_compat import Archive, compatible


def resources(data):
    archive = Archive(data)
    return {archive.key(i): archive.blobs[i] for i in range(len(archive.blobs))}


class RuntimeTests(unittest.TestCase):
    def test_content_registers_authored_items_in_inventory(self):
        from fbmod_compat import unpack
        from ebx_tools import Ebx
        content, _, _ = split_pack(self.original, include_runtime=False)
        records = resources(content)
        items = [Ebx(unpack(raw)) for (kind, name), raw in records.items()
                 if kind == 1 and name.startswith('items/board_bottomart/')]
        collections = [Ebx(unpack(raw)) for (kind, name), raw in records.items()
                       if kind == 1 and name.endswith('_itemcollection')]
        self.assertTrue(items)
        self.assertTrue(collections)
        for item in items:
            self.assertTrue(any(item.f[:16] + item.data[:16] in c.imports for c in collections))

    def test_content_retains_the_material_routes_its_recipes_require(self):
        import struct
        from fbmod_compat import unpack
        content, _, _ = split_pack(self.original)
        archive = Archive(content)
        recipe_keys = {struct.unpack_from('<Q',unpack(archive.blobs[i]),16)[0]
                       for i in range(len(archive.blobs))
                       if archive.key(i)[0]==2 and '/shaders/lenticular_' in archive.key(i)[1]}
        db = next(i for i in range(len(archive.blobs)) if archive.key(i)[1].endswith('_shaderstate_db'))
        raw = unpack(archive.blobs[db])
        descriptor = archive.descriptors[db]
        tail = deck_archive.descriptor_parts(descriptor)[2]
        size,rel = struct.unpack_from('<II',descriptor,tail+16)
        at = size+rel
        count = struct.unpack_from('<I',raw,at)[0];at+=4
        routed = set()
        for _ in range(count):
            key,n = struct.unpack_from('<QI',raw,at);routed.add(key);at+=12+4*n
        self.assertTrue(recipe_keys)
        self.assertLessEqual(recipe_keys,routed)

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
        overlap = left.keys() & right.keys()
        self.assertTrue(all('_bundlereftable' in name or ('_shaderstate_' in name or name.endswith('_itemcollection')) for _, name in overlap))
        self.assertEqual(left, {key: value for key, value in resources(normalized).items()
                                if key not in shared_keys() or ('_shaderstate_' in key[1] or key[1].endswith('_itemcollection'))})
        self.assertEqual(right, resources(build_runtime()))
        self.assertTrue(all(('_shaderstate_' in name or name.endswith('_itemcollection')) for _,name in left.keys() & shared_keys()))
        self.assertTrue(all(key in shared_keys() or '_bundlereftable' in key[1] for key in right))
        self.assertEqual(contract['abi'], ABI)
        self.assertFalse(contract['third_party_compatibility_verified'])

    def test_runtime_keeps_fixed_loader_assets_but_not_the_authored_fixture(self):
        _, runtime, _ = split_pack(self.original)
        keys=resources(runtime)
        self.assertIn((1,'items/board_bottomart/own_lenticular_95ff40e6bbdc52bb8939fb789615e1ad'),keys)
        authored={key for key in resources(self.original) if key[1].startswith('items/board_bottomart/')}
        self.assertFalse(authored & keys.keys())

    def test_runtime_payloads_are_valid_native_archive_streams(self):
        import struct
        from effects_runtime import _runtime_updates
        from fbmod_compat import unpack
        from deck_archive import descriptor_parts
        for record,payload in _runtime_updates():
            with self.subTest(resource=(record['kind'],record['name'])):
                raw=unpack(payload)
                descriptor=bytes.fromhex(record['descriptor'])
                sha,_,_=descriptor_parts(descriptor)
                self.assertEqual(len(raw),struct.unpack_from('<Q',descriptor,sha+20)[0])

    def test_runtime_preserves_native_compositor_and_owns_background(self):
        from fbmod_compat import unpack
        from effects_runtime import COMPOSITOR, _runtime_updates
        archive = Archive(build_runtime())
        keys = {archive.key(i) for i in range(len(archive.blobs))}
        self.assertFalse(keys & COMPOSITOR)
        self.assertEqual(keys, {(record['kind'], record['name']) for record, _ in _runtime_updates()})
        for record, payload in _runtime_updates():
            i = archive.find(record['kind'], record['name'])
            self.assertIsNotNone(i)
            self.assertEqual(archive.blobs[i], payload)
        lua = unpack(archive.blobs[archive.find(2, 'characters/lua/luaskateboardcompositor')])
        self.assertIn(b'deck:addBundleRef(emptyTexture)', lua)
        self.assertNotIn(b'bindings.DeckToolEmpty', lua)

    def test_migration_keeps_original_and_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, content, runtime = (root / n for n in ('old.fbmod', 'content.fbmod', 'runtime.zip'))
            source.write_bytes(self.original)
            migrate_file(source, content, runtime)
            before = content.read_bytes()
            with self.assertRaises(FileExistsError):
                migrate_file(source, content, runtime)
            self.assertEqual(source.read_bytes(), self.original)
            self.assertEqual(content.read_bytes(), before)
            self.assertFalse(runtime.exists())

    def test_runtime_is_deterministic_and_can_be_reused(self):
        self.assertEqual(build_runtime(), build_runtime())
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_runtime_export(self.original, root/'one.fbmod')
            self.assertFalse((root/(RUNTIME_NAME+'.zip')).exists())
            write_runtime_export(self.original, root/'two.fbmod')
            self.assertFalse((root/(RUNTIME_NAME+'.zip')).exists())
            self.assertEqual((root/'one.fbmod').read_bytes(), (root/'two.fbmod').read_bytes())

    def test_content_export_writes_only_the_deck_and_preserves_original(self):
        from effects_runtime import write_content_export
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'new.fbmod'
            contract=write_content_export(self.original,target)
            self.assertEqual(list(root.iterdir()),[target])
            content=resources(target.read_bytes())
            self.assertTrue(all(('_shaderstate_' in name or name.endswith('_itemcollection')) for _,name in content.keys() & shared_keys()))
            self.assertIn('neon-mask',contract['runtime_features'])
            before=target.read_bytes()
            with self.assertRaises(FileExistsError):write_content_export(self.original,target)
            self.assertEqual(target.read_bytes(),before)

    def test_failed_content_export_preserves_previous_file_and_exports_no_core(self):
        import os
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            destination = root/'deck.fbmod'
            destination.write_bytes(b'previous export')
            original_replace = os.replace
            def fail_contract(source, target):
                if Path(target)==destination:
                    raise OSError('Simulated disk failure')
                return original_replace(source, target)
            with patch('effects_runtime.os.replace', side_effect=fail_contract):
                with self.assertRaises(OSError):
                    write_runtime_export(self.original, destination, overwrite=True)
            self.assertEqual(destination.read_bytes(), b'previous export')
            self.assertFalse((root/(RUNTIME_NAME+'.fbmod')).exists())
            self.assertFalse(destination.with_suffix('.runtime.json').exists())


if __name__ == '__main__':
    unittest.main()
