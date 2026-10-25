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
