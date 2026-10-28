import unittest
import numpy as np
import smooth_effect

class NativeDepthSequenceTests(unittest.TestCase):
    def test_constant_depth_has_full_native_displacement(self):
        class Plane:
            mode='smooth'
            motion=np.array([.5,.5,0])
            def sample_channel(self,u,v,c):return np.ones(np.broadcast_shapes(u.shape,v.shape))
            def sample(self,u,v):return np.repeat(np.broadcast_arrays(u,v)[0][...,None],3,axis=-1)
        u=np.array([[.5,.75]]);v=np.array([[.3]])
        np.testing.assert_allclose(smooth_effect.render(Plane(),1,u,v)[...,0],[[.25,.5]],atol=1e-7)
        plane=Plane();plane.motion=np.array([.5,.5,1])
        np.testing.assert_allclose(smooth_effect.render(plane,1,u,v)[...,0],[[.75,1]],atol=1e-7)

    def test_sloped_depth_matches_closed_form_native_relaxation(self):
        class Ramp:
            mode='smooth'
            motion=np.array([.5,.5,0])
            def sample_channel(self,u,v,c):return np.broadcast_arrays(u,v)[0]
            def sample(self,u,v):return np.repeat(np.broadcast_arrays(u,v)[0][...,None],3,axis=-1)
        # At u=.25 the native initial displacement is .375. Its recurrence is
        # x_next=.25+.25*x, with fixed point 1/3 and exactly six updates.
        expected=1/3+(.375-1/3)*.25**6
        actual=smooth_effect.render(Ramp(),1,np.array([[.25]]),np.array([[.3]]))
        self.assertAlmostEqual(actual[0,0,0],expected,places=9)


class DepthCameraIntegrationTests(unittest.TestCase):
    def test_3d_depth_uses_shared_native_camera_calibration(self):
        from PIL import Image
        from qt_ui import Creator
        from effect_preview import AtlasPreview
        from board_preview import LENS_VIEW_PROFILE
        import depth_views
        renderers=[AtlasPreview(depth_views.pack([Image.new('RGB',(16,64),(n*32,)*3) for n in range(8)],0,balanced=True),'depth')]
        art=Image.fromarray(np.broadcast_to(np.arange(64,dtype=np.uint8)[None,:,None],(128,64,3)).copy())
        for mode in ('smooth','ghost'):
            renderers.append(AtlasPreview(smooth_effect.pack(art,Image.new('L',art.size,255),.3,.5,mode=='ghost'),mode))
        key=(0,.5,0,False,None,(40,160),False,('3D',False,30,0),False)
        for renderer in renderers:
            actual=Creator.effect_frame(renderer,.5,(40,160),key)
            expected=renderer.render(.5,(40,160),view_profile=LENS_VIEW_PROFILE)
            self.assertEqual(actual.tobytes(),expected.tobytes())
            flat=key[:7]+(('2D',False,30,0),)+key[8:]
            self.assertEqual(Creator.effect_frame(renderer,.5,(40,160),flat).tobytes(),renderer.render(.5,(40,160)).tobytes())
