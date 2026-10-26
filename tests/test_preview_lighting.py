import unittest
import numpy as np
from PIL import Image
from preview_lighting import normals, shade
from board_preview import texture_uv, DECK_THICKNESS


class SurfaceTests(unittest.TestCase):
    def test_caps_crop_planar_art_instead_of_squeezing_it(self):
        self.assertAlmostEqual(texture_uv(.1,.5)[0],.1)
        self.assertGreater(texture_uv(.1,0)[0],.49)
        self.assertLess(texture_uv(.9,1)[0],.51)
        self.assertEqual(texture_uv(.2,.35)[1],.35)
        self.assertTrue(.02<DECK_THICKNESS<.05)

    def test_rotated_surface_normals_are_finite_and_unit_length(self):
        for yaw,pitch in [(0,0),(-70,65),(70,-65)]:
            n=normals(40,160,yaw,pitch)
            self.assertTrue(np.isfinite(n).all())
            np.testing.assert_allclose(np.linalg.norm(n,axis=-1),1,atol=1e-5)
        self.assertGreater(float(normals(40,160,0,0)[80,20]@np.array([0,0,-1])),.99)

    def test_lighting_changes_with_pose_without_mutating_art(self):
        image=Image.new('RGB',(40,160),(110,140,160));before=image.tobytes()
        front=np.asarray(shade(image,0,0));side=np.asarray(shade(image,60,30))
        self.assertGreater(np.abs(front.astype(float)-side).mean(),5)
        self.assertEqual(before,image.tobytes())
        self.assertGreater(float(front.std()),.5)


class MenuCaptureCalibrationTests(unittest.TestCase):
    def test_captured_neutral_and_withheld_colour_patches(self):
        from menu_profile import response
        from effect_preview import linear, display
        colours=[(0,0,0),(128,128,128),(255,255,255),(208,181,64),(56,101,185)]
        positions=np.array([[.22078,.22078,.7668,.22078,.7668]],dtype=np.float32)
        rgb=linear(np.array([colours],dtype=np.uint8))
        result=np.asarray(display(response(rgb,positions,0)),dtype=float)[0]
        measured=np.array([(28,27,25),(155,148,138),(230,224,218),(211,187,89),(92,131,189)])
        self.assertLess(float(np.abs(result-measured).mean()),6)
        self.assertLess(float(np.abs(result-measured).max()),12)

    def test_measured_view_response_is_continuous_and_bounded(self):
        from menu_profile import response
        rgb=np.full((4,8,3),.1,dtype=np.float32)
        u=np.linspace(0,1,8)[None,:]
        for yaw in (-70,-61.875,-28.125,0,28.125,61.875,70):
            value=response(rgb,u,yaw)
            self.assertTrue(np.isfinite(value).all())
            self.assertTrue((value>=0).all() and (value<=1).all())
            self.assertLess(float(np.abs(response(rgb,u,yaw+.001)-value).max()),.001)


class RecessedWindowPreviewTests(unittest.TestCase):
    def test_window_shows_recessed_walls_and_keeps_front_art(self):
        from PIL import ImageDraw
        import finish_atlas
        from effect_preview import AtlasPreview
        frame=Image.new('RGBA',(64,256))
        ImageDraw.Draw(frame).rectangle((0,0,63,255),outline='white',width=5)
        back=Image.new('RGB',(64,256),'#204060')
        ImageDraw.Draw(back).rectangle((0,0,8,255),fill='#c05030')
        renderer=AtlasPreview(finish_atlas.pack('window',frame,back),'window')
        front=np.asarray(renderer.render(0,(64,256)))
        turned=np.asarray(renderer.render(.8,(64,256)))
        self.assertGreater(float(front[0].mean()),200)
        self.assertGreater(np.abs(front.astype(float)-turned).mean(),1)
        self.assertTrue(np.isfinite(front).all())
