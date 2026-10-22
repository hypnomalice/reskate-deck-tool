import unittest
import numpy as np
from PIL import Image,ImageDraw
import layer_atlas
from effect_preview import AtlasPreview
import live_placement

class ThreeLayerTests(unittest.TestCase):
    def test_both_transparencies_composite_in_linear_light(self):
        size=(40,160)
        front=Image.new('RGBA',size,(255,0,0,128));middle=Image.new('RGBA',size,(0,255,0,128));back=Image.new('RGB',size,'blue')
        atlas=layer_atlas.pack_three(front,middle,back)
        pixel=AtlasPreview(atlas,'layers3').render(0,size).getpixel((20,80))
        self.assertTrue(185<=pixel[0]<=190,pixel)
        self.assertTrue(134<=pixel[1]<=140 and 134<=pixel[2]<=140,pixel)
        self.assertEqual(atlas.getpixel((20,56)),(128,255,0))
        self.assertEqual(atlas.getpixel((20,3500))[:2],(188,188))

    def test_three_planes_move_at_their_own_depths(self):
        size=(256,1024);images=[]
        for x,color in [(64,'red'),(128,'lime'),(192,'blue')]:
            image=Image.new('RGBA',size,(0,0,0,0) if x!=192 else (0,0,0,255))
            ImageDraw.Draw(image).rectangle((x-3,100,x+3,924),fill=color);images.append(image)
        preview=AtlasPreview(layer_atlas.pack_three(*images,strength=.2),'layers3')
        def centres(angle):
            rgb=np.asarray(preview.render(angle,size),dtype=float);weights=rgb[200:800].sum(axis=0)
            return [(weights[:,c]*np.arange(size[0])).sum()/weights[:,c].sum() for c in range(3)]
        a,b=centres(-.3),centres(.3);delta=np.array(b)-a
        self.assertGreater(delta[0],10);self.assertTrue(.7<delta[1]<3,delta);self.assertLess(delta[2],-10)

    def test_live_placement_matches_three_layer_compositing(self):
        size=(40,160);front=Image.new('RGBA',size,(255,0,0,128));middle=Image.new('RGBA',size,(0,255,0,128));back=Image.new('RGB',size,'blue')
        deck=dict(mode='layers',fit='Stretch',background_fit='Stretch',background='#000000',placement=[{},{}],middle_placement={},layer_depths=[.1,.45,.9],depth=dict(strength=.08,bands=0),lenticular=False)
        expected=AtlasPreview(layer_atlas.pack_three(front,middle,back),'layers3').render(0,size)
        actual=live_placement.render([front,back,middle],deck,0,size)
        self.assertLess(np.abs(np.asarray(expected,dtype=float)-np.asarray(actual,dtype=float)).max(),2)

    def test_invalid_layer_depths_are_rejected(self):
        image=Image.new('RGBA',(8,32))
        for depths in [(0,1),(0,float('nan'),1),(0,2,1)]:
            with self.assertRaises(ValueError):layer_atlas.pack_three(image,image,image,depths=depths)
