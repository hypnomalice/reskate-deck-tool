"""CPU counterpart of assets/jiggle-runtime/jiggle_physics.lua.

Both solve the same damped springs from board acceleration. Differential tests
feed identical pose traces to Python and the exported Luau implementation.
"""
import math
import numpy as np


def limited(value, maximum):
    value=np.asarray(value,dtype=float);length=np.linalg.norm(value)
    return value*(maximum/length) if length>maximum else value


def inverse(q, vector):
    xyz=-np.asarray(q[:3]);t=np.cross(xyz,vector)*2
    return vector+t*q[3]+np.cross(xyz,t)


def rotation_rate(previous,current,dt):
    a=np.asarray(current[:3]);b=-np.asarray(previous[:3])
    xyz=a*previous[3]+b*current[3]+np.cross(a,b)
    scalar=current[3]*previous[3]-np.dot(a,b)
    if scalar<0:xyz=-xyz;scalar=-scalar
    n=np.linalg.norm(xyz)
    return xyz*(2*math.atan2(n,scalar)/(n*dt)) if n>1e-7 else np.zeros(3)


def spring(x,v,target,w,z,dt):
    a=z*w;b=w*math.sqrt(1-z*z);y=x-target
    c,s=math.cos(b*dt),math.sin(b*dt);e=math.exp(-a*dt)
    return target+e*(y*c+(v+a*y)*s/b),e*(v*c-(a*v+w*w*y)*s/b)


class Solver:
    def __init__(self,strength=.65,stiffness=50):
        self.strength=strength;self.stiffness=stiffness;self.reset()

    def reset(self,motion=None):
        self.particles=np.zeros((2,4));self.acceleration=np.zeros(3)
        self.angular=np.zeros(3);self.angular_acceleration=np.zeros(3)
        self.last=None if motion is None else dict(velocity=np.array(motion['velocity']),
            position=np.array(motion['position']),rotation=np.array(motion['rotation']),angular=np.zeros(3))

    def step(self,motion,dt):
        try:
            velocity=np.asarray(motion['velocity'],dtype=float);position=np.asarray(motion['position'],dtype=float)
            q=np.asarray(motion['rotation'],dtype=float)
            if velocity.shape!=(3,) or position.shape!=(3,) or q.shape!=(4,) or not np.isfinite(np.r_[velocity,position,q]).all():
                self.reset();return False
        except (KeyError,TypeError,ValueError):self.reset();return False
        if self.last is None or not math.isfinite(dt) or dt<=0 or dt>.12 or np.linalg.norm(position-self.last['position'])>8:
            self.reset(motion);return False
        accel=limited((velocity-self.last['velocity'])/dt,60)
        angular=limited(rotation_rate(self.last['rotation'],q,dt),25)
        angular_accel=limited((angular-self.last['angular'])/dt,100)
        blend=1-math.exp(-30*dt)
        self.acceleration+=(accel-self.acceleration)*blend
        self.angular+=(angular-self.angular)*blend
        local_a=inverse(q,self.acceleration)
        self.angular_acceleration+=(angular_accel-self.angular_acceleration)*blend
        omega=inverse(q,self.angular);alpha=inverse(q,self.angular_acceleration)
        for i,p in enumerate(self.particles):
            anchor=np.array([-.035 if i==0 else .035,.12,.02])
            rotational=-(np.cross(alpha,anchor)+np.cross(omega,np.cross(omega,anchor)))
            inertial=-local_a*.05+rotational*.65
            tx=np.clip(inertial[0],-.8,.8)*self.strength
            ty=np.clip(-inertial[2]+inertial[1]*.35,-.9,.9)*self.strength
            w=(6+np.clip(self.stiffness,0,100)*.12)*(1 if i==0 else 1.088)
            p[0],p[2]=spring(p[0],p[2],tx,w,.28,dt)
            p[1],p[3]=spring(p[1],p[3],ty,w,.28,dt)
            for axis in (0,1):
                if abs(p[axis])>self.strength:
                    p[axis]=math.copysign(self.strength,p[axis])
                    if p[axis]*p[axis+2]>0:p[axis+2]=0
        self.last=dict(velocity=velocity.copy(),position=position.copy(),rotation=q.copy(),angular=angular)
        return True


def preview_pose(yaw,pitch):
    """Turn the board, rather than animate an unrelated texture oscillator."""
    y=math.radians(yaw)/2;x=math.radians(pitch-90)/2
    return dict(position=np.zeros(3),velocity=np.zeros(3),
                rotation=np.array([math.sin(x)*math.cos(y),math.cos(x)*math.sin(y),
                                   -math.sin(x)*math.sin(y),math.cos(x)*math.cos(y)]))
