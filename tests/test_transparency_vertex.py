import struct,unittest,uuid
from pathlib import Path
from fbmod_compat import Archive,unpack
import transparency_vertex as optical

class OpticalVertexTests(unittest.TestCase):
    def test_all_profiles_preserve_existing_streams_and_indices(self):
        assets=Path(optical.__file__).resolve().parent/'assets/transparency'
        for profile,mode in [('glass','glass'),('water','glass'),('crystal','crystal'),('case','case'),('case-pcb','case')]:
            with self.subTest(profile=profile):
                original=Archive((assets/('vertex-'+profile+'-transparent-mesh.fbmod')).read_bytes())
                changed=Archive(original.bytes())
                cfg=dict(tint='#123456',tint_strength=.63,haze=.72,roughness=.29,
                         reflection_strength=1.24,thickness=.014)
                reports=optical.patch_mesh(changed,13,mode,cfg)
                before=unpack(original.blobs[13]);after=unpack(changed.blobs[13])
                u=lambda b,at:struct.unpack_from('<I',b,at)[0]
                p=lambda b,at:struct.unpack_from('<Q',b,at)[0]+16
                expected=struct.pack('<12e',*optical.constants(mode,cfg))
                for lod in range(6):
                    old_lod=p(before,48+8*lod);new_lod=p(after,48+8*lod)
                    old_sections=p(before,old_lod+12);new_sections=p(after,new_lod+12)
                    chunk=original.find(3,str(uuid.UUID(bytes_le=before[old_lod+116:old_lod+132])))
                    old_data=unpack(original.blobs[chunk]);new_data=unpack(changed.blobs[chunk])
                    self.assertEqual(old_data[u(before,old_lod+92):],new_data[u(after,new_lod+92):])
                    for section in range(u(before,old_lod+8)):
                        old=old_sections+384*section;new=new_sections+384*section
                        declaration=old+112;nv=u(before,old+44)
                        length=nv*sum(before[declaration+64+2*s] for s in range(before[declaration+97]))
                        old_offset=u(before,old+40);new_offset=u(after,new+40)
                        self.assertEqual(old_data[old_offset:old_offset+length],new_data[new_offset:new_offset+length])
                        if section in (0,1):
                            self.assertEqual(new_data[new_offset+length:new_offset+length+24*nv],expected*nv)
                            self.assertEqual(after[new+112+96:new+112+98],bytes((9,7)))
                            self.assertEqual(after[new+112:new+212],after[new+212:new+312])
                            self.assertEqual(after[new+112:new+112+24],before[declaration:declaration+24])
                self.assertLess(reports[0]['added_bytes'],300_000)

    def test_distinct_decks_and_limits_keep_their_own_constants(self):
        a=optical.constants('glass',dict(tint='#ff0000',haze=0,reflection_strength=0,thickness=.001))
        b=optical.constants('glass',dict(tint='#0000ff',haze=1,reflection_strength=2,thickness=.03))
        self.assertNotEqual(a,b)
        self.assertEqual(a[:3],(1,0,0));self.assertEqual(b[:3],(0,0,1))
        self.assertEqual(a[4],0);self.assertEqual(b[4],1)
        self.assertEqual(a[6],0);self.assertEqual(b[6],2)
        self.assertEqual(optical.constants('crystal',dict(cuts=399))[8],399)
        for values in (a,b):
            decoded=struct.unpack('<12e',struct.pack('<12e',*values))
            for expected,actual in zip(values,decoded):self.assertAlmostEqual(expected,actual,delta=.0005)

    def test_an_existing_optical_stream_cannot_be_added_twice(self):
        asset=Path(optical.__file__).resolve().parent/'assets/transparency/vertex-glass-transparent-mesh.fbmod'
        archive=Archive(asset.read_bytes());optical.patch_mesh(archive,13,'glass')
        with self.assertRaises(ValueError):optical.patch_mesh(archive,13,'glass')

    def test_mismatched_duplicate_declaration_is_rejected(self):
        asset=Path(optical.__file__).resolve().parent/'assets/transparency/vertex-glass-transparent-mesh.fbmod'
        archive=Archive(asset.read_bytes());mesh=bytearray(unpack(archive.blobs[13]))
        lod=struct.unpack_from('<Q',mesh,48)[0]+16
        section=struct.unpack_from('<Q',mesh,lod+12)[0]+16
        mesh[section+212+96]=5
        archive.replace(13,mesh);before=archive.bytes()
        with self.assertRaisesRegex(ValueError,'declarations disagree'):
            optical.patch_mesh(archive,13,'glass')
        self.assertEqual(archive.bytes(),before)

if __name__=='__main__':unittest.main()
