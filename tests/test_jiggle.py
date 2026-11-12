import json,math,os,subprocess,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import jiggle_effect
from jiggle_physics import Solver
from effect_preview import AtlasPreview


class JiggleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.mask=Image.new('L',(512,2048));ImageDraw.Draw(self.mask).ellipse((80,900,430,1350),fill=255)
        self.mask.save(self.root/'mask.png');self.cfg=dict(mask=str(self.root/'mask.png'),amount=65,stiffness=50)
        self.art=Image.new('RGB',(512,2048),'#bd692e');self.depth=Image.new('L',(512,2048),180)

    def test_black_stays_fixed_and_neutral_is_identity(self):
        renderer=AtlasPreview(jiggle_effect.pack(self.art,self.depth,self.cfg),'jiggle')
        u=np.array([.1,.5,.9]);v=np.array([.1,.55,.9]);zero=np.zeros((2,4))
        x,y=jiggle_effect.warp(renderer,u,v,zero,'top')
        np.testing.assert_allclose(x,u);np.testing.assert_allclose(y,v)
        moving=zero.copy();moving[:,0]=.6;moving[:,1]=.4
        x,y=jiggle_effect.warp(renderer,u,v,moving,'top')
        self.assertEqual(x[0],u[0]);self.assertEqual(x[2],u[2]);self.assertLess(x[1],u[1])

    def test_attachments_and_reverse_are_saved_in_atlas(self):
        c=dict(self.cfg,top_pin=[.4,.45],bottom_pin=[.6,.65],reverse=True)
        renderer=AtlasPreview(jiggle_effect.pack(self.art,self.depth,c),'jiggle')
        np.testing.assert_allclose(renderer.sample(.125,36/4096)[:2],[.4,.45],atol=.004)
        np.testing.assert_allclose(renderer.sample(.375,36/4096)[:2],[.6,.65],atol=.004)
        self.assertGreater(renderer.motion[2],.99)
        self.assertRaises(ValueError,jiggle_effect.pack,self.art,self.depth,dict(c,top_pin=[.4,.8]))

    def test_springs_settle_without_a_sine_animation(self):
        solver=Solver();motion=dict(position=np.zeros(3),velocity=np.zeros(3),rotation=np.array([0,0,0,1]))
        solver.step(motion,1/120)
        motion=dict(motion,velocity=np.array([1.,0,0]));solver.step(motion,1/120)
        self.assertLess(solver.particles[0,0],0)
        for _ in range(2400):solver.step(motion,1/120)
        self.assertLess(np.max(np.abs(solver.particles)),1e-9)

    @unittest.skipUnless(os.environ.get('RESKATE_LUAU_RUNNER'),'Luau runner required for cross-language parity')
    def test_python_matches_exported_luau_motion_trace(self):
        lua_source=(Path(__file__).resolve().parents[1]/'assets/jiggle-runtime/jiggle_physics.lua').read_text()
        code=['local M=(function()\n'+lua_source+'\nend)()'];expected=[]
        for strength,stiffness in ((0,0),(.2,15),(.65,50),(1,100)):
            solver=Solver(strength,stiffness);code.append(f'local solver=M.new({{strength={strength},stiffness={stiffness}}})')
            t=0
            for i in range(180):
                dt=(1/60,1/120,1/90)[i%3];t+=dt;a=.5*math.sin(t*3)
                q=[0,math.sin(a/2),0,math.cos(a/2)];v=[math.cos(t*2),0,math.sin(t*2)];p=[.5*math.sin(t*2),0,-.5*math.cos(t*2)]
                solver.step(dict(position=p,velocity=v,rotation=q),dt);expected.extend(solver.particles.reshape(-1).tolist())
                vec=lambda x:'vector.create('+','.join(repr(n) for n in x)+')'
                code.append('solver:step({deck={position='+vec(p)+',rotation={'+','.join(repr(n) for n in q)+'}},velocity='+vec(v)+'},'+repr(dt)+')')
                code.append('for _,p in solver.particles do print(string.format("%.12g %.12g %.12g %.12g",p.x,p.y,p.vx,p.vy)) end')
        script=self.root/'parity.lua';script.write_text('\n'.join(code))
        result=subprocess.run([os.environ['RESKATE_LUAU_RUNNER'],str(script)],capture_output=True,text=True,check=True)
        actual=np.fromstring(result.stdout,sep=' ').reshape(-1,4);expected=np.asarray(expected).reshape(-1,4)
        # Luau vectors are float32; spring positions stay below 0.000064 source pixels of disagreement.
        np.testing.assert_allclose(actual[:,:2],expected[:,:2],atol=2e-6,rtol=2e-5)
        np.testing.assert_allclose(actual[:,2:],expected[:,2:],atol=2e-5,rtol=2e-5)


if __name__=='__main__':unittest.main()
