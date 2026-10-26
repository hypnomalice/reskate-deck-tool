"""Menu-capture colour/illumination approximation for the procedural preview.

The numerical profile is fitted to supplied HDR-to-SDR menu captures. It does
not read the game's live lights, shadows, material buffers or graphics settings.
"""
import numpy as np
from effect_preview import linear, display
from board_preview import rotate, DECK_LENGTH, NOSE_KICK, TAIL_KICK
from menu_profile import response


def normals(width, height, yaw, pitch):
    u=(np.arange(width,dtype=np.float32)[None,:]+.5)/width
    v=(np.arange(height,dtype=np.float32)[:,None]+.5)/height
    nx=np.broadcast_to(.44*(u-.5),(height,width))
    slope=-2*NOSE_KICK*np.maximum(0,(.24-v)/.24)/(.24*DECK_LENGTH)
    slope+=2*TAIL_KICK*np.maximum(0,(v-.77)/.23)/(.23*DECK_LENGTH)
    ny=np.broadcast_to(slope,(height,width))
    nz=np.full((height,width),-1,dtype=np.float32)
    n=np.stack(rotate(nx,ny,nz,yaw,pitch),axis=-1)
    return n/np.maximum(np.linalg.norm(n,axis=-1,keepdims=True),1e-6)


def shade(image, yaw, pitch, emission=None):
    rgb=linear(image.convert('RGB'));height,width=rgb.shape[:2]
    u=(np.arange(width,dtype=np.float32)[None,:]+.5)/width
    n=normals(width,height,yaw,pitch)
    flat=np.array(rotate(0,0,-1,yaw,0),dtype=np.float32)
    light=np.array([.37,-.6,-1],dtype=np.float32);light/=np.linalg.norm(light)
    illumination=(.6+.4*np.clip(n@light,0,1))/(.6+.4*np.clip(flat@light,0,1))
    return display(response(rgb,u,yaw,illumination,emission=emission))


def map_emission(value,size):
    from PIL import Image
    from board_preview import map_artwork
    return np.stack([np.asarray(map_artwork(Image.fromarray(value[...,c].astype(np.float32)),size)) for c in range(3)],axis=-1)
