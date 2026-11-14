"""Fast, numerically equivalent artwork preview; NumPy remains the fallback."""
import ctypes
from pathlib import Path
import numpy as np
from PIL import Image

try:
    _dll=ctypes.CDLL(str(Path(__file__).parent/'assets/jiggle-runtime/jiggle_preview.dll'))
    _render=_dll.render_springs
    _render.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_void_p]
    _render.restype=None
    _layered=getattr(_dll,'render_layered_springs',None)
    if _layered is not None:_layered.argtypes=_render.argtypes;_layered.restype=None
except OSError:
    _render=None;_layered=None

def render(renderer,u,v,particles,attachment,movement):
    if getattr(renderer,'jiggle_layer_view','Combined')!='Combined' or getattr(renderer,'jiggle_mask_overlay',False):return None
    if _render is None:return None
    u=np.asarray(u);v=np.asarray(v);w=u.shape[-1];h=v.shape[0]
    if w<2 or h<2:return None
    du=float(u[0,-1]-u[0,0])/(w-1);dv=float(v[-1,0]-v[0,0])/(h-1)
    coords=[float(u[0,0])-du/2,float(v[0,0])-dv/2,float(u[0,-1])+du/2,float(v[-1,0])+dv/2]
    params=np.array(coords+list(np.asarray(particles)[:,:2].ravel())+[attachment=='both',movement],dtype=np.float64)
    function=_layered if hasattr(renderer,'layer_pixels') else _render
    if function is None:return None
    pixels=np.ascontiguousarray(renderer.layer_pixels if hasattr(renderer,'layer_pixels') else renderer.pixels,dtype=np.float32);output=np.empty((h,w,3),dtype=np.uint8)
    function(pixels.ctypes.data,renderer.width,renderer.height,output.ctypes.data,w,h,params.ctypes.data)
    return Image.fromarray(output)
