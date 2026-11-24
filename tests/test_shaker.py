from pathlib import Path
import tempfile,unittest,copy,math
import numpy as np
from PIL import Image,ImageDraw
import shaker_effect as effect
from shaker_preview import Simulation,ShakerPreview

class ShakerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        background=self.root/'bg.png';Image.new('RGB',(512,2048),'#305070').save(background)
        self.pieces=[]
        for i,colour in enumerate(['red','green','blue']):
            image=Image.new('RGBA',(128,128));d=ImageDraw.Draw(image)
            if i==0:d.ellipse((5,5,123,123),fill=colour)
            elif i==1:d.rectangle((5,5,123,123),fill=colour)
            else:d.polygon([(64,5),(80,44),(124,44),(90,75),(110,122),(64,94),(18,122),(38,75),(4,44),(48,44)],fill=colour)
            path=self.root/f'{i}.png';image.save(path);self.pieces.append(dict(image=str(path),width_mm=45+i*3,weight=i+1))
        self.project=dict(name='Shaker',mode='shaker',images=[str(background),None],fit='Crop to fill',shaker=dict(rim=True,blur=0,pieces=self.pieces))
    def tearDown(self):self.temp.cleanup()
    def test_native_data_budget_and_float32_round_trip(self):
        p=effect.prepare(self.project);rows=effect.parameters(p)
        self.assertEqual(len(rows),31)
        for piece in p['pieces']:
            expected=effect.unpack_bytes(piece['metadata'][1:])
            actual=effect.unpack_bytes(np.asarray(piece['metadata'][1:],dtype=np.float32).tolist())
            self.assertEqual(expected,actual);self.assertLessEqual(expected[0],31)
            from shapely.geometry import Polygon,Point
            self.assertLess(Polygon(piece['vertices']).centroid.distance(Point(0,0)),1e-9)
    def test_weight_changes_mass_but_not_geometry_or_free_acceleration(self):
        project=copy.deepcopy(self.project);project['shaker']['pieces']=project['shaker']['pieces'][:1]
        a=effect.prepare(project);project['shaker']['pieces'][0]['weight']=4;b=effect.prepare(project)
        self.assertAlmostEqual(b['pieces'][0]['mass']/a['pieces'][0]['mass'],4)
        self.assertEqual(a['pieces'][0]['vertices'],b['pieces'][0]['vertices'])
        first,second=Simulation(a),Simulation(b)
        for _ in range(40):
            x=first.step((-.70710678,0,0,.70710678),dt=1/120)
            y=second.step((-.70710678,0,0,.70710678),dt=1/120)
            np.testing.assert_allclose(x,y,atol=1e-8)
    def test_each_piece_owns_its_sprite_bank(self):
        p=effect.prepare(self.project)
        colours=[p['atlas'].getpixel((256,2176+i*512))[:3] for i in range(3)]
        self.assertEqual(colours,[(255,0,0),(0,128,0),(0,0,255)])
        renderer=ShakerPreview(p);renderer.advance(20,10,1/60)
        self.assertEqual(renderer.render(.3,(64,256)).size,(64,256))
    def test_invalid_settings_and_empty_images_are_rejected(self):
        for field,value in [('width_mm',float('nan')),('weight',0),('collision','depth-layers'),('rim_mm',6),('rim_mm',float('nan')),('rim_strength',-1),('rim_strength',float('inf'))]:
            with self.subTest(field=field),self.assertRaises(ValueError):effect.settings({'pieces':[dict(self.pieces[0],**{field:value})]})
        with self.assertRaises(ValueError):effect.settings({'pieces':self.pieces*2})
        image=self.root/'empty.png';Image.new('RGBA',(64,64)).save(image)
        with self.assertRaises(ValueError):effect.prepare_piece(dict(self.pieces[0],image=str(image)))
    def test_acrylic_width_changes_collision_and_strength_only_changes_appearance(self):
        from shapely.geometry import Polygon
        p=dict(self.pieces[1],collision='outline',rim_mm=0,rim_strength=1)
        bare=effect.prepare_piece(p)
        wide=effect.prepare_piece(dict(p,rim_mm=3))
        faint=effect.prepare_piece(dict(p,rim_mm=3,rim_strength=.25))
        clear=effect.prepare_piece(dict(p,rim_mm=3,rim_strength=0))
        disabled=effect.prepare_piece(dict(p,rim_mm=3),False)
        self.assertGreater(Polygon(wide['vertices']).area,Polygon(bare['vertices']).area)
        np.testing.assert_allclose(disabled['vertices'],bare['vertices'])
        self.assertEqual(wide['metadata'],faint['metadata']);self.assertEqual(wide['metadata'],clear['metadata'])
        from effect_preview import linear
        a,b=linear(wide['mask'])[:,:,1],linear(faint['mask'])[:,:,1]
        self.assertGreater(np.count_nonzero(a),0)
        np.testing.assert_allclose(b,a*.25,atol=.004)
        self.assertEqual(np.asarray(clear['mask'])[:,:,1].max(),0)
        self.assertEqual(wide['sprite'].tobytes(),faint['sprite'].tobytes())
        # Neutral X/Y normals must decode to .5 in the shader despite the
        # atlas's sRGB RGB channels and linear alpha channel.
        image=np.asarray(wide['mask']);rgb=linear(wide['mask'])
        self.assertAlmostEqual(float(rgb[128,256,2]),.5,delta=.006)
        self.assertAlmostEqual(float(image[128,256,3])/255,.5,delta=.006)
    def test_piece_preview_uses_native_banks_at_rotated_positions(self):
        from effect_preview import AtlasPreview
        prepared=effect.prepare(self.project);r=ShakerPreview(prepared)
        # Sample artwork at known pose centres, then move off the pieces. This
        # catches sampling an adjacent bank or leaving trails after motion.
        r.poses=np.array([[.3,.25,.1],[.5,.5,.25],[.7,.75,.6]])
        u=r.poses[:,0].copy();v=r.poses[:,1]/2
        expected=np.array([r.pixels[2176+i*512,256] for i in range(3)])
        np.testing.assert_allclose(r.sample(u,v),expected,atol=.015)
        r.poses[:,0]+=2
        np.testing.assert_allclose(r.sample(u,v),AtlasPreview.sample(r,u,v),atol=1e-8)
    def test_shaker_rejects_bare_fbmod_before_writing(self):
        import creator_engine
        target=self.root/'bad.fbmod'
        with self.assertRaisesRegex(ValueError,'Mod ZIP'):creator_engine.export_pack([self.project],target)
        self.assertFalse(target.exists())
    def test_native_shaker_export_honours_explicit_grip_off(self):
        from unittest.mock import patch
        import creator_engine,eink_mesh
        from fbmod_compat import Archive,unpack
        from deck_archive import texture_rid
        import struct
        on=copy.deepcopy(self.project);on['name']='Shaker Grip On';on['glass']={'grip_tape':True}
        off=copy.deepcopy(on);off['name']='Shaker Grip Off';off['glass']['grip_tape']=False
        destination=self.root/'optional-grip.fbmod'
        with patch.object(eink_mesh,'equipped_grip',wraps=eink_mesh.equipped_grip) as export_grip:
            creator_engine.export_pack([on,off],destination,shared_runtime=True)
        self.assertEqual(export_grip.call_count,1)
        self.assertEqual(export_grip.call_args.args[1],['Shaker Grip On'])
        self.assertTrue(on['glass']['grip_tape']);self.assertFalse(off['glass']['grip_tape'])
        archive=Archive(destination.read_bytes());key=struct.pack('<Q',texture_rid(effect.MATERIAL))
        import uuid
        for project in (on,off):
            token=uuid.uuid5(uuid.NAMESPACE_URL,'sdec/eink-rim/'+project['name'].casefold()).hex
            mesh=archive.find(2,'characters/maincharacters/reskate/'+token+'_mesh')
            self.assertIsNotNone(mesh)
            self.assertIn(key,unpack(archive.blobs[mesh]))
    def test_artwork_and_rim_do_not_extend_into_the_shadow_only_region(self):
        # A nonzero border texel must never be extended by a clamped sample.
        # Deliberately poison the bank: the independent coverage guards, rather
        # than a fortunate clear border in one PNG, must keep this area empty.
        from effect_preview import AtlasPreview
        project=copy.deepcopy(self.project);project['shaker']['pieces']=project['shaker']['pieces'][:1]
        r=ShakerPreview(effect.prepare(project));r.poses=np.array([[.5,.5,0],[.5,.5,0],[.5,.5,0]])
        sprite,mask=r.banks[0];sprite[:]=[1,0,0,1];mask[:]=[0,1,.5,.5]
        yscale=effect.PPM/(2048*.91797/.818)
        for angle in (0,.17,.43,.78):
            r.poses[0,2]=angle;c,s=np.cos(angle*math.tau),np.sin(angle*math.tau)
            # Just beyond the image's bottom, but within the translated shadow
            # region. Artwork/rim must be zero even when shadow is in bounds.
            px,py=-s*132,c*132
            u=.5+px/512;v=(.5+py/(2048*yscale))/2
            shadow_y=(py-22)*c-(px-13)*s
            if abs(shadow_y)>127.5:continue
            np.testing.assert_allclose(r.sample(u,v),AtlasPreview.sample(r,u,v),atol=1e-8)
        # Well outside both banks, in every direction: exactly background.
        u=np.array([.5,2,-1,.5]);v=np.array([0,.25,.25,.5])
        np.testing.assert_allclose(r.sample(u,v),AtlasPreview.sample(r,u,v),atol=1e-8)
    def test_background_inset_has_rounded_nose_and_tail(self):
        from shaker_outline import inside,TOP,BOTTOM
        u=(np.arange(2000)+.5)/2000
        nose=[np.count_nonzero(inside(u,v)) for v in (TOP+.0005,TOP+.005,TOP+.02,TOP+.06,.5)]
        tail=[np.count_nonzero(inside(u,v)) for v in (BOTTOM-.0005,BOTTOM-.005,BOTTOM-.02,BOTTOM-.06,.5)]
        self.assertEqual(nose,sorted(nose));self.assertEqual(tail,sorted(tail))
        self.assertGreater(len(set(nose)),4);self.assertGreater(len(set(tail)),4)
        self.assertTrue(inside(.5,TOP+.005));self.assertFalse(inside(.1,TOP+.005))
        self.assertTrue(inside(.5,BOTTOM-.005));self.assertFalse(inside(.9,BOTTOM-.005))
        prepared=effect.prepare(self.project);renderer=ShakerPreview(prepared)
        np.testing.assert_array_equal(renderer.artwork_inset(u,TOP+.005),inside(u,TOP+.005))
    def test_preview_shake_uses_inertia_to_lift_pieces_and_dimmer_preserves_print(self):
        prepared=effect.prepare(self.project);r=ShakerPreview(prepared);poses=[]
        for i in range(60*6):
            r.advance(0,0,1/60,velocity=r.shake_velocity(i/60));poses.append(r.poses.copy())
        motion=np.array(poses)
        self.assertGreater(np.ptp(motion[:,:,1]),.3)
        self.assertGreater(np.ptp(motion[:,:,0]),.12)
        r.poses=np.array([[.3,.25,.1],[.5,.5,.25],[.7,.75,.6]])
        before=r.sample(r.poses[:,0],r.poses[:,1]/2)
        r.dim_background=True
        np.testing.assert_allclose(r.sample(r.poses[:,0],r.poses[:,1]/2),before,atol=.015)
        dim=r.sample(.12,.2);r.dim_background=False
        np.testing.assert_allclose(dim,r.sample(.12,.2)*.16,atol=1e-6)
    def test_mixed_shapes_settle_and_wake_at_different_frame_rates(self):
        prepared=effect.prepare(self.project)
        for hz in (30,60,120,240):
            with self.subTest(hz=hz):
                solver=Simulation(prepared);tail=[]
                for frame in range(hz*30):
                    poses=solver.step((-.7071067811865476,0,0,.7071067811865476),dt=1/hz)
                    if frame>=hz*29:tail.append(poses)
                self.assertLess(np.ptp(np.array(tail),axis=0).max(),1e-8)
                before=poses.copy()
                for frame in range(hz):poses=solver.step((-.3826834324,0,0,.9238795325),dt=1/hz)
                self.assertGreater(np.abs(poses-before).max(),1e-4)
