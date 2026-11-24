"""The game's Luau solver, hosted by a small bundled tool-only CPU library."""
from pathlib import Path
import ctypes,json,math,copy
import numpy as np
from transparency_preview import TransparencyPreview
from effect_preview import AtlasPreview
import shaker_effect

ROOT=Path(__file__).resolve().parent/'assets/shaker-runtime'
_dll=None
def library():
    global _dll
    if _dll is None:
        if not (ROOT/'shaker_preview.dll').exists():raise RuntimeError('Build the shaker preview helper before running this source checkout.')
        _dll=ctypes.CDLL(str(ROOT/'shaker_preview.dll'))
        _dll.shaker_create.argtypes=[ctypes.c_char_p,ctypes.c_int];_dll.shaker_create.restype=ctypes.c_void_p
        _dll.shaker_destroy.argtypes=[ctypes.c_void_p]
        _dll.shaker_error.restype=ctypes.c_char_p
        _dll.shaker_step.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_double)]
        _dll.shaker_step.restype=ctypes.c_int
    return _dll

def literal(value):
    if isinstance(value,dict):return '{'+','.join('['+json.dumps(k)+']='+literal(v) for k,v in value.items())+'}'
    if isinstance(value,list):return '{'+','.join(literal(v) for v in value)+'}'
    return repr(value)

class Simulation:
    def __init__(self,prepared):
        self.handle=None;self.lib=library()
        fields={shaker_effect.key(p['guid']):{'value':dict(zip(('r','g','b'),p['default']))} for p in shaker_effect.parameters(prepared)}
        code='local modules,cache={},{}\nlocal function require(n) if not cache[n] then cache[n]=modules[n]() end;return cache[n] end\n'
        for name in ['shaker_data_keys','shaker_geometry','polygon_physics']:
            code+='modules['+json.dumps(name)+']=function()\n'+(ROOT/(name+'.lua')).read_text()+'\nend\n'
        code+='local live='+literal(fields)+'\nlocal solver=require("polygon_physics").new(require("shaker_geometry").read(live,'+str(len(prepared['pieces']))+'),'+str(len(prepared['pieces']))+')\n'
        code+='''function tick(qx,qy,qz,qw,vx,vy,vz,dt)
 solver:step({rotation={qx,qy,qz,qw}},vector.create(vx,vy,vz),dt)
 return solver:parameters()
end
'''
        self.script=code.encode();self.reset()
    def reset(self):
        if self.handle:self.lib.shaker_destroy(self.handle)
        self.handle=self.lib.shaker_create(self.script,len(self.script))
        if not self.handle:raise RuntimeError(self.lib.shaker_error().decode(errors='replace'))
    def step(self,rotation=(0,0,0,1),velocity=(0,0,0),dt=0):
        source=(ctypes.c_double*8)(*rotation,*velocity,dt);output=(ctypes.c_double*9)()
        if not self.lib.shaker_step(self.handle,source,output):raise RuntimeError(self.lib.shaker_error().decode(errors='replace'))
        return np.array(output).reshape(3,3)
    def __del__(self):
        if getattr(self,'handle',None):self.lib.shaker_destroy(self.handle);self.handle=None

class ShakerPreview(TransparencyPreview):
    def __init__(self,prepared,value=None):
        super().__init__(prepared['atlas'],'glass',value)
        self.mode='shaker';self.prepared=prepared;self.solver=Simulation(prepared)
        self.poses=self.solver.step();self.count=len(prepared['pieces']);self.rim=prepared['config']['rim']
        self.banks=[]
        for i in range(self.count):
            def bank(start):return np.dstack((self.pixels[start:start+256],self.alpha[start:start+256]))
            self.banks.append((bank(2048+i*512),bank(2304+i*512)))
    def advance(self,yaw,pitch,dt,velocity=(0,0,0)):
        # The preview's upright deck has its nose above its tail.
        ax=-math.pi/2+math.radians(pitch);ay=math.radians(yaw)
        sx,cx,sy,cy=math.sin(ax/2),math.cos(ax/2),math.sin(ay/2),math.cos(ay/2)
        self.poses=self.solver.step((sx*cy,cx*sy,sx*sy,cx*cy),velocity=velocity,dt=dt)
    @staticmethod
    def shake_velocity(seconds):
        # Container translation, fed through the real solver's acceleration
        # input. It can overcome gravity rather than only stirring the pile.
        return (.8*math.sin(seconds*5.3),2.6*math.sin(seconds*7),0)
    def artwork_inset(self,u,v):
        from shaker_outline import inside
        return inside(u,v)
    def glass_reflection(self,bu,bv,angle,wave,roughness):
        # A broad, restrained studio reflection leaves the artwork readable.
        # This is approximate preview lighting, not a change to native glass.
        centre=.30+angle*.36
        broad=np.exp(-((bu-centre)/(.13+roughness*.2))**2)
        return broad*(.025+.12*abs(angle)**2)+.008*np.exp(-((bu-.85)/.22)**2)
    @staticmethod
    def bank_sample(data,x,y):
        x=np.clip(x+255.5,0,511);y=np.clip(y+127.5,0,255)
        x0,y0=np.floor(x).astype(np.int32),np.floor(y).astype(np.int32)
        x1,y1=np.minimum(x0+1,511),np.minimum(y0+1,255)
        tx,ty=(x-x0)[:,None],(y-y0)[:,None]
        return (data[y0,x0]*(1-tx)+data[y0,x1]*tx)*(1-ty)+(data[y1,x0]*(1-tx)+data[y1,x1]*tx)*ty
    def sample(self,u,v):
        colour=AtlasPreview.sample(self,u,v)
        if not hasattr(self,'banks'):return colour
        if getattr(self,'dim_background',False):colour=colour*.16
        u,v=np.broadcast_arrays(np.asarray(u),np.asarray(v));shape=u.shape
        u,v=u.ravel(),v.ravel();colour=colour.reshape(-1,3).copy()
        yscale=shaker_effect.PPM/(2048*.91797/.818)
        for i,(x,y,a) in enumerate(self.poses[:self.count]):
            px=(u-x)*512;py=(v*2-y)*2048*yscale
            c,s=np.cos(a*2*np.pi),np.sin(a*2*np.pi)
            rx=px*c+py*s;ry=py*c-px*s
            sx,sy=px-13,py-22;srx=sx*c+sy*s;sry=sy*c-sx*s
            object_bounds=(np.abs(rx)<=255.5)&(np.abs(ry)<=127.5)
            shadow_bounds=(np.abs(srx)<=255.5)&(np.abs(sry)<=127.5)
            visible=object_bounds|shadow_bounds
            if not visible.any():continue
            sprite,maskbank=self.banks[i]
            artwork=self.bank_sample(sprite,rx[visible],ry[visible])
            values=self.bank_sample(maskbank,rx[visible],ry[visible])
            mask=[values[:,j] for j in range(4)]
            alpha=artwork[:,3]*object_bounds[visible]
            shadow=self.bank_sample(maskbank,srx[visible],sry[visible])[:,0]*.43*shadow_bounds[visible]
            local=colour[visible]*(1-shadow[:,None])
            mx,my=mask[2]*2-1,mask[3]*2-1
            nx,ny=mx*c-my*s,mx*s+my*c
            light=np.clip(.58-nx*.24-ny*.34,.2,1)
            rim=mask[1]*int(self.rim)*object_bounds[visible]
            plastic=local*.6+light[...,None]*[.23,.28,.30]
            local=local+(plastic-local)*rim[...,None]
            colour[visible]=local+(artwork[:,:3]-local)*alpha[...,None]
        return colour.reshape(*shape,3)
    def render(self,*args,**kwargs):
        # The glass preview shares its existing approximate lighting and shell.
        self.mode='glass'
        try:return super().render(*args,**kwargs)
        finally:self.mode='shaker'
