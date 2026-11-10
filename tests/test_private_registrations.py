import struct
import unittest
from pathlib import Path
from fbmod_compat import Archive, unpack
from deck_archive import bundle_add, build
from fbmod_compat import pack
from eink_mesh import merge_registrations, attach


def routes(raw):
    pool, bundles, lookups = (struct.unpack_from('<Q', raw, q)[0] for q in (16, 24, 8))
    def text(t):
        if t == 0xffffffff: return ''
        at = pool + (t & 0x7fffff)
        start = at + 4 if t & 0x800000 else pool + struct.unpack_from('<I', raw, at + 4)[0]
        return text(struct.unpack_from('<I', raw, at)[0]) + raw[start:start + (t >> 24)].decode()
    names = [''] + [text(struct.unpack_from('<I', raw, bundles + i * 8)[0])
                     for i in range(1, struct.unpack_from('<I', raw, 76)[0])]
    return {h: (names[b], text(t)) for h, b, t in
            (struct.unpack_from('<QII', raw, lookups + i * 16)
             for i in range(struct.unpack_from('<I', raw, 72)[0]))}


class RegistrationTests(unittest.TestCase):
    def test_private_meshes_keep_their_native_material_permutations(self):
        assets = Path(__file__).resolve().parents[1] / 'assets'
        for mode, seed in [('case','case-shell-mesh.fbmod'),('glitch','glitch-opaque-mesh.fbmod')]:
            with self.subTest(mode=mode):
                title = 'Native material regression ' + mode
                data = build([dict(name=title,mode='classic',texture=bytes(2097152),
                    texture_size=(512,4096),texture_mips=1,resident=True,
                    thumb_small=bytes(65536),thumb_large=bytes(589824))],pack,'Regression','',independent_shader=True)
                result = Archive(attach(data,[title], [title] if mode=='glitch' else [],
                    case_names=[title] if mode=='case' else []))
                donor = Archive((assets/seed).read_bytes())
                native = unpack(donor.blobs[20])
                recipes = [unpack(result.blobs[i]) for i in range(len(result.blobs))
                    if result.key(i)[0]==2 and '/shaders/lenticular_' in result.key(i)[1]]
                self.assertEqual(len(recipes),1)
                self.assertEqual(recipes[0][16:24],native[16:24])
                self.assertEqual(len(recipes[0]),len(native))

    def test_private_additions_preserve_all_existing_routes(self):
        a = Archive((Path(__file__).resolve().parents[1] / 'assets/eink-rim-mesh.fbmod').read_bytes())
        base = unpack(a.blobs[a.find(2, 'characters/customization/configs/cas_main_bundlereftable')])
        left, _ = bundle_add(base, ['characters/customization/reskate/test/ordinary_ap'])
        right, _ = bundle_add(base, ['characters/customization/reskate/test/private_ap'])
        merged, meta = merge_registrations(left, right)
        expected = routes(left) | routes(right)
        self.assertEqual(routes(merged), expected)
        self.assertEqual(struct.unpack('<IIQ', meta), (len(merged)-20, 20, 0))
        again, _ = merge_registrations(merged, right)
        self.assertEqual(again, merged)


if __name__ == '__main__': unittest.main()
