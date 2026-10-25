import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from ghost_areas import coverage
from effect_preview import AtlasPreview
import smooth_effect


class GhostAreaTests(unittest.TestCase):
    def test_default_matches_legacy_full_board(self):
        art=Image.new('RGB',(32,128),'#ca5030');depth=Image.new('L',art.size,128)
        self.assertEqual(smooth_effect.pack(art,depth,ghost=True).tobytes(),smooth_effect.pack(art,depth,ghost=True,areas={'silver':{'selection':'all'},'holo':{'selection':'all'}}).tobytes())

    def test_independent_channels_and_unselected_artwork(self):
        art=Image.new('RGB',(32,128),'#ca5030');depth=Image.new('L',art.size,128)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'off.png';Image.new('L',art.size,0).save(path)
            areas={'silver':{'selection':'mask','mask':str(path)},'holo':{'selection':'all'}}
            renderer=AtlasPreview(smooth_effect.pack(art,depth,ghost=True,areas=areas),'ghost')
            self.assertEqual(float(renderer.sample(.5,.75)[0]),0)
            self.assertEqual(float(renderer.sample(.5,.75)[2]),1)
            areas['holo']={'selection':'mask','mask':str(path)}
            image=AtlasPreview(smooth_effect.pack(art,depth,ghost=True,areas=areas),'ghost').render(0,(32,128))
            self.assertLess(np.abs(np.asarray(image,dtype=float)-np.asarray(art,dtype=float)).max(),2)

    def test_transparent_and_soft_masks(self):
        art=Image.new('RGB',(8,32),'red')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'mask.png';Image.new('RGBA',art.size,(255,255,255,128)).save(path)
            self.assertAlmostEqual(float(coverage(art,{'selection':'mask','mask':str(path)})[10,4]),128/255,places=4)
            Image.new('RGBA',art.size,(255,255,255,0)).save(path)
            self.assertEqual(float(coverage(art,{'selection':'mask','mask':str(path)})[10,4]),0)

    def test_colour_selection_and_missing_mask(self):
        art=Image.new('RGB',(8,32),'red')
        self.assertEqual(float(coverage(art,{'selection':'colour','colour':'red','tolerance':0})[10,4]),1)
        self.assertEqual(float(coverage(art,{'selection':'colour','colour':'blue','tolerance':0})[10,4]),0)
        with self.assertRaises(ValueError):coverage(art,{'selection':'mask'})
        with self.assertRaises(ValueError):coverage(art,{'selection':'colour','tolerance':float('nan')})

    def test_export_masks_follow_artwork_placement_without_mutating_project(self):
        from unittest.mock import patch
        import copy
        import creator_engine
        import image_placement
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);art=root/'art.png';mask=root/'mask.png'
            Image.new('RGB',(64,256),'red').save(art)
            pixels=Image.new('RGBA',(64,256),(0,0,0,0))
            pixels.paste((255,255,255,255),(16,64,48,192));pixels.save(mask)
            placement={'zoom':1.3,'x':.1,'y':-.05}
            project={'name':'Masked','mode':'ghost','fit':'Stretch','images':[str(art),str(art)],
                     'placement':[placement,placement],
                     'ghost':{'silver':{'selection':'mask','mask':str(mask)},'holo':{'selection':'all'}}}
            original=copy.deepcopy(project)
            def inspect(projects,*args,**kwargs):
                prepared=projects[0]
                actual=Image.open(prepared['ghost']['silver']['mask']).convert('RGBA')
                expected=image_placement.frame(mask,'Stretch','#000000',placement,alpha=True)
                self.assertEqual(actual.tobytes(),expected.tobytes())
                self.assertEqual(prepared['fit'],'Stretch')
                return 'verified'
            with patch.object(creator_engine,'_export_pack',side_effect=inspect):
                self.assertEqual(creator_engine.export_pack([project],root/'test.fbmod',lambda text:None),'verified')
            self.assertEqual(project,original)


if __name__=='__main__':unittest.main()
