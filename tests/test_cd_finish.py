import unittest
from PIL import Image
import numpy as np
import cd_finish
from effect_preview import AtlasPreview

class CDFinishTests(unittest.TestCase):
    def test_finish_and_layout_are_independent_and_roundtrip(self):
        seen=set()
        for finish in cd_finish.FINISHES:
            for layout in cd_finish.LAYOUTS:
                for colours in cd_finish.COLOURS:
                    cfg=cd_finish.settings(dict(enabled=True,finish=finish,layout=layout,colours=colours))
                    self.assertEqual(cd_finish.settings(cfg),cfg)
                    seen.add(cd_finish.marker(cfg))
        self.assertEqual(len(seen),12)
        for field in ('finish','layout','colours'):
            with self.assertRaises(ValueError):cd_finish.settings({field:'unknown'})
        self.assertFalse(cd_finish.enabled(dict(mode='ghost')))
        self.assertFalse(cd_finish.enabled(dict(mode='classic',cd=dict(enabled=True))))

    def test_artwork_is_exact_and_depth_remains_data_not_transparency(self):
        a=np.zeros((1984,512,3),np.uint8);a[:,:,0]=np.arange(512,dtype=np.uint16)%256
        image=Image.fromarray(a);depth=Image.fromarray(np.tile(np.linspace(0,255,512,dtype=np.uint8),(1984,1)))
        atlas=cd_finish.pack(image,depth,dict(enabled=True))
        np.testing.assert_array_equal(np.asarray(atlas)[64:2048,:,:3],a)
        alpha=np.asarray(atlas)[64:2048,:,3]
        self.assertEqual((alpha.min(),alpha.max()),(128,224))
        payload,sizes=cd_finish.mip_payload(atlas)
        self.assertEqual(len(sizes),13);self.assertEqual(len(payload),sum(sizes))
        self.assertEqual(payload[:sizes[0]],atlas.tobytes())

    def test_every_variant_previews_and_colour_separation_changes_image(self):
        image=Image.new('RGB',(512,1984),'white');depth=Image.new('L',image.size,180)
        previews={}
        for finish in cd_finish.FINISHES:
            for layout in cd_finish.LAYOUTS:
                for colours in cd_finish.COLOURS:
                    cfg=dict(enabled=True,finish=finish,layout=layout,colours=colours)
                    renderer=AtlasPreview(cd_finish.pack(image,depth,cfg),'cd')
                    out=renderer.render(0,(32,128),view_profile=(.1,.1,1))
                    self.assertEqual(out.size,(32,128))
                    previews[finish,layout,colours]=np.asarray(out).astype(float)
        a=previews['mirror','full','shared'];b=previews['mirror','full','separate']
        self.assertGreater(np.abs(a-b).mean(),1)
        self.assertGreater(np.abs(previews['mirror','full','separate']-previews['mirror','corner','separate']).mean(),1)

if __name__=='__main__':unittest.main()
