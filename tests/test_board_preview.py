import unittest
import numpy as np
from PIL import Image
from board_preview import ARTWORK_REGION, map_artwork, surface


class BoardPreviewTests(unittest.TestCase):
    def test_measured_mapping_moves_marked_rows_without_changing_source(self):
        rows=np.arange(1000,dtype=np.float32)
        pixels=np.zeros((1000,200,3),dtype=np.uint8)
        pixels[:,:,0]=np.rint(rows[:,None]*255/999).astype(np.uint8)
        source=Image.fromarray(pixels)
        original=source.tobytes()
        mapped=map_artwork(source)
        self.assertAlmostEqual(mapped.getpixel((100,0))[0],ARTWORK_REGION[1]*255,delta=1)
        self.assertAlmostEqual(mapped.getpixel((100,500))[0],sum(ARTWORK_REGION[1::2])/2*255,delta=1)
        self.assertEqual(source.tobytes(),original)
        self.assertEqual(mapped.size,source.size)

    def test_horizontal_crop_and_resized_output(self):
        pixels=np.tile(np.arange(256,dtype=np.uint8)[None,:,None],(1024,1,3))
        mapped=map_artwork(Image.fromarray(pixels),(100,400))
        self.assertEqual(mapped.size,(100,400))
        self.assertAlmostEqual(mapped.getpixel((0,200))[0],ARTWORK_REGION[0]*255,delta=2)
        self.assertAlmostEqual(mapped.getpixel((99,200))[0],ARTWORK_REGION[2]*255,delta=2)

    def test_authored_shape_is_bounded_and_has_kicks(self):
        self.assertLess(abs(surface(0,0)[0]),.01)
        self.assertLess(abs(surface(1,1)[0]),.01)
        self.assertLess(surface(.5,.5)[2],surface(.5,0)[2])
        self.assertAlmostEqual(surface(0,.5)[0],-.5)


if __name__=='__main__':unittest.main()


class OrbitCalibrationTests(unittest.TestCase):
    def test_orbit_is_continuous_reversible_and_bounded(self):
        from board_preview import orbit_angle, orbit_yaw
        self.assertEqual(orbit_angle(0),0)
        for value in (-1,-.75,-.1,0,.1,.75,1):
            self.assertAlmostEqual(orbit_angle(orbit_yaw(value)),value)
        self.assertAlmostEqual(orbit_angle(-100),-1)
        self.assertAlmostEqual(orbit_angle(100),1)


class CaptureShapeTests(unittest.TestCase):
    def test_visible_nose_and_tail_match_capture_proportions(self):
        self.assertTrue(.71 < surface(1,.04)[0]*2 < .76)
        self.assertTrue(.94 < surface(1,.12)[0]*2 < .98)
        self.assertTrue(.57 < surface(1,.96)[0]*2 < .65)
        from board_preview import CAMERA_DISTANCE, TRUCK_CENTRES, PLATE_CENTRES, PLATE_WIDTH, BOLT_HALF_WIDTH
        self.assertGreater(CAMERA_DISTANCE,15)
        self.assertAlmostEqual(TRUCK_CENTRES[0],.228,delta=.005)
        self.assertGreater(PLATE_CENTRES[0],TRUCK_CENTRES[0])
        self.assertLess(PLATE_CENTRES[1],TRUCK_CENTRES[1])
        self.assertLess(2*BOLT_HALF_WIDTH,PLATE_WIDTH)


class LensViewCalibrationTests(unittest.TestCase):
    def test_calibrated_front_favours_the_native_second_picture_without_export_changes(self):
        from effect_preview import AtlasPreview
        from creator_engine import atlas
        from board_preview import LENS_VIEW_PROFILE
        renderer=AtlasPreview(atlas(Image.new('RGB',(32,128),'red'),Image.new('RGB',(32,128),(0,255,0))),'classic')
        before=renderer.pixels.tobytes()
        image=np.asarray(renderer.render(0,(96,384),view_profile=LENS_VIEW_PROFILE),dtype=float)
        self.assertGreater(image[:,:,1].mean(),image[:,:,0].mean())
        self.assertEqual(before,renderer.pixels.tobytes())
        # Full authoring range remains available without the 3D camera profile.
        first=np.asarray(renderer.render(1,(32,128)),dtype=float)
        last=np.asarray(renderer.render(-1,(32,128)),dtype=float)
        self.assertGreater(first[:,:,0].mean(),last[:,:,0].mean())
