import unittest
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image
import depth_views,layer_atlas,liquid_atlas,finish_atlas,animation,animation_texture
from effect_preview import linear


def selected(atlas,linear_read=True,guard=True):
    header=np.asarray(atlas)[56,64]/255
    settings=np.asarray(atlas)[56,192]/255
    if linear_read:
        header=linear(np.asarray(atlas)[56,64]);settings=linear(np.asarray(atlas)[56,192])
    r,g,b=header
    return bool(g>.9 and .15<r<.60 and (not guard or settings[1]<.01))


class AtlasSelectorTests(unittest.TestCase):
    def test_legacy_modes_do_not_enter_three_plane_branch(self):
        image=Image.new('RGB',(64,256),'orange')
        tiled=depth_views.pack([image]*8,balanced=True)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'sample.gif'
            image.save(path,save_all=True,append_images=[Image.new('RGB',image.size,'blue')],duration=100)
            animated,_=animation_texture.atlas(animation.load(path))
        three=layer_atlas.pack_three(image.convert('RGBA'),image.convert('RGBA'),image)
        # Reproduce the reported bug under the game's linear texture reads.
        self.assertTrue(selected(tiled,True,False))
        self.assertTrue(selected(animated,True,False))
        for decoded in (False,True):
            self.assertFalse(selected(tiled,decoded))
            self.assertFalse(selected(animated,decoded))
            self.assertTrue(selected(three,decoded))
            self.assertFalse(selected(finish_atlas.pack('window',image,image),decoded))
            self.assertFalse(selected(liquid_atlas.pack(image.convert('RGBA'),image),decoded))


if __name__=='__main__':unittest.main()
