import unittest
import numpy as np
from PIL import Image
from material_view import view_vector,gravity_vector,cavity,volume_offset,wet_path
from effect_preview import AtlasPreview,linear,display
import finish_atlas,advanced_atlas


class AuthoredMaterialTests(unittest.TestCase):
    def test_native_window_wall_coordinates_and_lighting(self):
        class Sampler:
            def sample(self,u,v):
                u,v=np.broadcast_arrays(u,v)
                return np.stack((u,v,np.ones_like(u)),axis=-1)
        centre,hit=cavity(Sampler(),np.array([[.5]]),np.array([[.5]]),view_vector(0))
        np.testing.assert_allclose(hit[2],.7)
        np.testing.assert_allclose(hit[3],.5)
        np.testing.assert_allclose(hit[4],.5)
        np.testing.assert_allclose(centre,[[(.5*.85/1.126,.375*.85/1.126,.85/1.126)]],rtol=1e-6)
        _,wall=cavity(Sampler(),np.array([[.9]]),np.array([[.5]]),view_vector(0))
        np.testing.assert_allclose(wall[2],.12,atol=1e-6)
        np.testing.assert_allclose(wall[3],.12/.88,atol=1e-6)

    def test_ink_uses_native_ink_base_instead_of_showing_art_at_oblique_angles(self):
        art=Image.new('RGB',(32,128),'red');mask=Image.new('L',art.size,255)
        r=AtlasPreview(finish_atlas.pack('ink',art,mask),'ink')
        off=np.asarray(r.render(0,(32,128),view_pose=(65,0)))
        expected=np.array(display(np.array([[[.018,.025,.055]]],dtype=np.float32)))[0,0]
        np.testing.assert_allclose(off,np.broadcast_to(expected,off.shape),atol=1)
        front=np.asarray(r.render(0,(32,128),view_pose=(0,0)))
        self.assertGreater(float(front[:,:,1].mean()),float(off[:,:,1].mean())+80)

    def test_neon_keeps_unmasked_albedo_and_separate_hdr_emission(self):
        art=Image.new('RGB',(32,128),(36,49,59));mask=Image.new('L',art.size,0)
        atlas=advanced_atlas.neon_pack(art,mask,{'brightness':.7})
        r=AtlasPreview(atlas,'neon');unlit=r.render(0,(32,128));material=r.render(0,(32,128),material=True)
        np.testing.assert_allclose(np.asarray(unlit),np.asarray(art),atol=1)
        np.testing.assert_allclose(np.asarray(material),np.asarray(art),atol=1)
        self.assertEqual(float(material.info['linear_emission'].max()),0)
        r=AtlasPreview(advanced_atlas.neon_pack(art,Image.new('L',art.size,255),{'brightness':1}),'neon')
        emission=r.render(0,(32,128),material=True).info['linear_emission']
        np.testing.assert_allclose(emission,linear(art)*32,atol=.02)

    def test_neon_capture_colour_targets(self):
        from menu_profile import response
        rgb=linear(np.array([[[36,49,59],[0,223,255]]],dtype=np.uint8))
        result=np.asarray(display(response(rgb,np.array([[.75,.75]]),0,emission=rgb*.7*32)),dtype=float)
        self.assertLess(float(abs(result-np.array([[[142,165,181],[220,248,248]]])).mean()),3)

    def test_gravity_is_independent_of_view_and_fill_volume_is_conserved(self):
        np.testing.assert_allclose(gravity_vector((0,0)),gravity_vector((60,0)),atol=1e-6)
        self.assertGreater(np.linalg.norm(gravity_vector((0,45))-gravity_vector((0,0))),.5)
        rng=np.random.default_rng(8);xyz=rng.uniform(-1,1,(100000,3))*np.array([.5,2,.06])
        for g in ([0,1,0],[0,0,1],[.3,.7,.64]):
            g=np.asarray(g)/np.linalg.norm(g)
            for amount in (.2,.5,.8):
                offset=volume_offset(g,.12,amount)
                filled=float(np.mean(xyz@g+offset>=0))
                self.assertAlmostEqual(filled,amount,delta=.008)
        level=np.ones((4,4))*.03
        wet,_=wet_path(level,-1,.1,0)
        self.assertFalse(wet.any())
        wet,_=wet_path(level,-1,.1,1)
        np.testing.assert_allclose(wet,.1)
