"""Independent finish coverage for Ghost Rare; source art stays unchanged."""
import math
import numpy as np
from PIL import ImageColor, ImageOps
import image_placement


def coverage(art, settings=None, fit='Stretch', placement=None, *, label='finish'):
    cfg=settings or {};method=cfg.get('selection','all')
    if method=='all':return np.ones((art.height,art.width),dtype=np.float32)
    if method=='mask':
        path=cfg.get('mask')
        if not path:raise ValueError('Choose a '+label+' mask PNG, or select Whole board.')
        mask=image_placement.frame(path,fit,'#000000',placement,alpha=True,size=art.size)
        return np.asarray(ImageOps.grayscale(mask),dtype=np.float32)/255*np.asarray(mask.getchannel('A'),dtype=np.float32)/255
    if method=='colour':
        tolerance=float(cfg.get('tolerance',.15))
        if not math.isfinite(tolerance) or not 0<=tolerance<=1:raise ValueError('Colour tolerance must be between 0 and 100%.')
        target=np.asarray(ImageColor.getrgb(cfg.get('colour','#ffffff')),dtype=np.float32)/255
        rgb=np.asarray(art.convert('RGB'),dtype=np.float32)/255
        distance=np.sqrt(np.mean((rgb-target)**2,axis=2));edge=max(.005,tolerance*.1)
        return np.clip((tolerance+edge-distance)/edge,0,1)
    raise ValueError('Choose a supported '+label+' area method.')
