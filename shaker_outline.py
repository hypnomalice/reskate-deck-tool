"""Inset silhouette in visible board coordinates, shared with the native mask."""
import numpy as np
from board_preview import NOSE_CAP,TAIL_CAP,NOSE_POWER,TAIL_POWER

LEFT,RIGHT,TOP,BOTTOM=.04,.96,.015,.985

def inside(u,v):
    y=(np.asarray(v)-TOP)/(BOTTOM-TOP)
    nose=y<.5
    end=np.where(nose,1-y/NOSE_CAP,1-(1-y)/TAIL_CAP)
    end=np.clip(end,0,1)
    width=(RIGHT-LEFT)*.5*np.sqrt(np.maximum(0,1-end**np.where(nose,NOSE_POWER,TAIL_POWER)))
    return (y>=0)&(y<=1)&(np.abs(np.asarray(u)-.5)<width)
