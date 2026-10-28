"""Optional tool-only depth rasterizer. The Python reference remains the fallback."""
import ctypes
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image

@lru_cache(maxsize=1)
def backend():
    try:
        dll=ctypes.CDLL(str(Path(__file__).resolve().parent/'assets/depth-raster.dll'))
        dll.depth_raster_version.restype=ctypes.c_int
        if dll.depth_raster_version()!=1:return None
        dll.depth_raster.argtypes=[ctypes.c_void_p]*3+[ctypes.c_int]*2+[ctypes.c_double]*3
        dll.depth_raster.restype=ctypes.c_int
        return dll
    except (OSError,AttributeError):return None

def render(image,depth,angle,strength,convergence):
    if image.mode!='RGB' or depth.mode!='L' or depth.size!=image.size:
        raise ValueError('Depth rasterizer needs matching RGB artwork and L depth images.')
    dll=backend()
    if dll is None or not -1<=angle<=1:return None
    rgb=np.ascontiguousarray(image,dtype=np.uint8)
    z=np.ascontiguousarray(depth,dtype=np.uint8)
    out=np.empty_like(rgb)
    width,height=image.size
    if not dll.depth_raster(rgb.ctypes.data,z.ctypes.data,out.ctypes.data,width,height,angle,strength,convergence):
        raise RuntimeError('Depth rasterizer could not prepare this view.')
    return Image.fromarray(out)
