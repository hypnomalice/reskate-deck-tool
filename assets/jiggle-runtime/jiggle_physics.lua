-- Pure motion solver. No game calls, elapsed-time oscillation or global state.
local M={}
local V=vector.create
local function finite(x) return x==x and math.abs(x)<1e12 end
local function valid(v) return v and finite(v.x) and finite(v.y) and finite(v.z) end
local function limit(v,n)
    local length=vector.magnitude(v)
    return length>n and v*(n/length) or v
end
local function inverse(q,v)
    local xyz=V(-q[1],-q[2],-q[3]);local t=vector.cross(xyz,v)*2
    return v+t*q[4]+vector.cross(xyz,t)
end
local function rotation_rate(previous,current,dt)
    -- q = current * conjugate(previous), shortest arc; q and -q agree.
    local a,b=V(current[1],current[2],current[3]),V(-previous[1],-previous[2],-previous[3])
    local xyz=a*previous[4]+b*current[4]+vector.cross(a,b)
    local scalar=current[4]*previous[4]-vector.dot(a,b)
    if scalar<0 then xyz=-xyz;scalar=-scalar end
    local n=vector.magnitude(xyz)
    return n>1e-7 and xyz*(2*math.atan2(n,scalar)/(n*dt)) or V(0,0,0)
end
local function spring(x,v,target,w,z,dt)
    -- Exact underdamped solution under a constant force over this step.
    local a=z*w;local b=w*math.sqrt(1-z*z);local y=x-target
    local c,s=math.cos(b*dt),math.sin(b*dt);local e=math.exp(-a*dt)
    return target+e*(y*c+(v+a*y)*s/b),e*(v*c-(a*v+w*w*y)*s/b)
end
function M.new(options)
    options=options or {}
    local self={particles={{x=0,y=0,vx=0,vy=0},{x=0,y=0,vx=0,vy=0}},
        strength=math.clamp(options.strength or .65,0,1),stiffness=options.stiffness or 50,last=nil,
        acceleration=V(0,0,0),angular=V(0,0,0),angularAcceleration=V(0,0,0)}
    function self:reset(motion)
        for _,p in self.particles do p.x=0;p.y=0;p.vx=0;p.vy=0 end
        self.acceleration=V(0,0,0);self.angular=V(0,0,0);self.angularAcceleration=V(0,0,0)
        self.last=motion and {velocity=motion.velocity,position=motion.deck.position,rotation=table.clone(motion.deck.rotation),angular=V(0,0,0)} or nil
    end
    function self:step(motion,dt)
        if not motion or not motion.deck or not valid(motion.velocity) or not valid(motion.deck.position) then self:reset();return false end
        local q=motion.deck.rotation
        if not q or not finite(q[1]) or not finite(q[2]) or not finite(q[3]) or not finite(q[4]) then self:reset();return false end
        if not self.last or not finite(dt) or dt<=0 or dt>.12 or vector.magnitude(motion.deck.position-self.last.position)>8 then self:reset(motion);return false end
        local accel=limit((motion.velocity-self.last.velocity)/dt,60)
        local angular=limit(rotation_rate(self.last.rotation,q,dt),25)
        local angularAccel=limit((angular-self.last.angular)/dt,100)
        local blend=1-math.exp(-30*dt)
        self.acceleration+=(accel-self.acceleration)*blend
        self.angular+=(angular-self.angular)*blend
        local localA=inverse(q,self.acceleration)
        self.angularAcceleration+=(angularAccel-self.angularAcceleration)*blend
        local omega=inverse(q,self.angular);local alpha=inverse(q,self.angularAcceleration)
        for i,p in self.particles do
            local anchor=V(i==1 and -.035 or .035,.12,.02)
            local rotational=-(vector.cross(alpha,anchor)+vector.cross(omega,vector.cross(omega,anchor)))
            local inertial=-localA*.05+rotational*.65
            -- A raised virtual mass lags opposite the acceleration of its board anchor.
            -- Euler and centripetal acceleration above handle rotation in board space.
            -- U follows local X; V follows -Z. No angular-speed animation is added.
            local tx=math.clamp(inertial.x,-.8,.8)*self.strength
            local ty=math.clamp(-inertial.z+inertial.y*.35,-.9,.9)*self.strength
            local w=(6+math.clamp(self.stiffness,0,100)*.12)*(i==1 and 1 or 1.088)
            p.x,p.vx=spring(p.x,p.vx,tx,w,.28,dt)
            p.y,p.vy=spring(p.y,p.vy,ty,w,.28,dt)
            if math.abs(p.x)>self.strength then p.x=math.sign(p.x)*self.strength;if p.x*p.vx>0 then p.vx=0 end end
            if math.abs(p.y)>self.strength then p.y=math.sign(p.y)*self.strength;if p.y*p.vy>0 then p.vy=0 end end
        end
        self.last={velocity=motion.velocity,position=motion.deck.position,rotation=table.clone(q),angular=angular}
        return true
    end
    return self
end
return M
