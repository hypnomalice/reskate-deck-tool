"""Camera-to-surface incidence for the procedural material preview.

Uses the same two angular components consumed by the authored finish shaders;
this is geometry/camera incidence, not an animation clock or gravity input.
"""
import math
import numpy as np


def view_vector(angle, pose=None):
    if pose is None:
        x=float(np.clip(angle,-1,1))
        return np.array([x,0,math.sqrt(max(0,1-x*x))],dtype=np.float32)
    yaw,pitch=map(math.radians,pose)
    return np.array([-math.sin(yaw)*math.cos(pitch),-math.sin(pitch),math.cos(yaw)*math.cos(pitch)],dtype=np.float32)


def gravity_vector(pose=None):
    if pose is None:return np.array([0,1,0],dtype=np.float32)
    yaw,pitch=map(math.radians,pose)
    return np.array([math.sin(yaw)*math.sin(pitch),math.cos(pitch),-math.cos(yaw)*math.sin(pitch)],dtype=np.float32)


def cavity(renderer,u,v,view,liquid=False):
    """Authored shader's box intersection, wall UVs and interior illumination."""
    u,v=np.broadcast_arrays(u,v);px=u-.5;py=(v-.5)*4
    rx=view[0]*.35+px/1.2;ry=view[1]*-.80+py/1.2
    if liquid:rx=rx*5;ry=ry*5
    half_x,half_y,depth,depth_uv=(.495,1.98,.14,.176) if liquid else (.44,1.60,.7,.88)
    sx=(half_x-np.where(rx>0,1,-1)*px)/np.maximum(np.abs(rx),.001)
    sy=(half_y-np.where(ry>0,1,-1)*py)/np.maximum(np.abs(ry),.001)
    z=np.maximum(0,np.minimum(depth,np.minimum(sx,sy)))
    hx=px+rx*z;hy=py+ry*z;side=sx<sy;rear=z>depth-.001
    back_u=.5+hx/(half_x*2);back_v=.5+hy/(half_y*2)
    du=z/depth_uv;side_u=np.where(rx>0,du,1-du)
    bu=np.clip(np.where(rear,back_u,np.where(side,side_u,back_u)),.001,.999)
    bv=np.clip(np.where(rear,back_v,np.where(side,back_v,du)),.001,.999)
    illumination=np.where(rear,.85,np.where(side,.60,.70))/(1+z*.18)
    background=renderer.sample(bu,.25+bv*.25)*illumination[...,None]
    return background,(rx,ry,z,bu,bv,illumination)


def volume_offset(gravity,depth,amount):
    """Same bounded volume quantile as the authored closed-box shader."""
    largest,middle,smallest=sorted((abs(gravity[0])*.5,abs(gravity[1])*2,abs(gravity[2])*depth*.5),reverse=True)
    def pair_cdf(t):
        a=np.abs(t)
        centre=.5+a/max(largest*2,1e-6)
        tail=1-np.maximum(0,largest+middle-a)**2/max(largest*middle*8,1e-8)
        pos=np.where(a<=largest-middle,centre,tail)
        return np.clip(np.where(t>=0,pos,1-pos),0,1)
    bound=largest+middle+smallest;lo=-bound;hi=bound
    for _ in range(11):
        mid=(lo+hi)*.5
        fraction=sum(pair_cdf(mid-smallest*n)*w for n,w in ((-.8611363116,.1739274226),(-.3399810436,.3260725774),(.3399810436,.3260725774),(.8611363116,.1739274226)))
        if fraction<amount:lo=mid
        else:hi=mid
    return (lo+hi)*.5


def wet_path(level,direction,depth,amount):
    denominator=np.where(direction>=0,1,-1)*np.maximum(np.abs(direction),1e-5)
    crossing=-level/denominator
    exit=np.minimum(depth,np.maximum(0,crossing))
    entry=np.minimum(depth,np.maximum(0,depth-crossing))
    wet=np.where(level>=0,np.where(direction<0,exit,depth),np.where(direction>0,entry,0))
    if amount<=.00001:wet=np.zeros_like(level)
    if amount>=.99999:wet=np.full_like(level,depth)
    return wet,crossing
