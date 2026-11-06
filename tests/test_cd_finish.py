import unittest
from PIL import Image
import numpy as np
import cd_finish
from effect_preview import AtlasPreview

class CDFinishTests(unittest.TestCase):
    def test_centred_motion_has_opposite_relief_and_no_background_drift(self):
        h=128/255+np.array([0,.25,.5,.75])*(96/255)
        offsets=cd_finish.motion_offset(h,1.2,.5)
        self.assertEqual(offsets[0],0)
        self.assertLess(offsets[1],0)
        self.assertAlmostEqual(offsets[2],0)
        self.assertGreater(offsets[3],0)
        np.testing.assert_array_equal(cd_finish.motion_offset(h,0,.5),np.zeros(4))
        np.testing.assert_allclose(cd_finish.motion_offset(h,1.2,-.5),-offsets)
        np.testing.assert_allclose(cd_finish.motion_offset(h,1.2,.5,legacy=True),.5*(h-128/255)*.035)

    def test_scratches_visible_at_max_and_zero_count_is_off(self):
        image=Image.new('RGB',(512,1984),'gray');depth=Image.new('L',image.size,128)
        def preview(strength,count):
            atlas=cd_finish.pack(image,depth,dict(layout='corner',scratch_strength=strength,scratch_amount=count))
            return np.asarray(AtlasPreview(atlas,'cd').render(0,(192,768))).astype(int)
        clean=preview(0,4);scratched=preview(4,4)
        np.testing.assert_array_equal(clean,preview(4,0))
        self.assertGreater(np.max(np.abs(scratched-clean)),5)
        self.assertGreater(np.count_nonzero(np.max(np.abs(scratched-clean),axis=2)>3),20)

    def test_motion_strength_does_not_destroy_depth_gradients(self):
        depth=Image.fromarray(np.tile(np.arange(256,dtype=np.uint8),(1984,2)))
        image=Image.new('RGB',depth.size,'black')
        atlases=[cd_finish.pack(image,depth,dict(depth_strength=s)) for s in (0,.5,1,2)]
        for atlas in atlases[1:]:
            np.testing.assert_array_equal(np.asarray(atlas)[64:2048,:,3],np.asarray(atlases[0])[64:2048,:,3])
        for atlas,s in zip(atlases,(0,.5,1,2)):
            r=AtlasPreview(atlas,'cd')
            self.assertAlmostEqual(float(r.sample(.375,4/4096)[0])*2,s,delta=.012)
            self.assertAlmostEqual(float(r.sample(.125,4/4096)[2]),.45,delta=.005)

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
