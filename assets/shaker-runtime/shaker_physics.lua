local M = {}
local V = vector.create
local function restitution(speed)
    return speed > .12 and .48 or 0
end
local function inverse(q, v)
    local xyz = V(-q[1],-q[2],-q[3])
    local t = vector.cross(xyz,v)*2
    return v+t*q[4]+vector.cross(xyz,t)
end
local function confine(body, radius)
    local anchor = math.clamp(body.z,-.285,.285)
    local dx,dz = body.x,body.z-anchor
    local length = math.sqrt(dx*dx+dz*dz)
    local limit = .088-radius
    if length <= limit then return end
    local nx,nz = dx/length,dz/length
    body.x,body.z = nx*limit,anchor+nz*limit
    local outward = body.vx*nx+body.vz*nz
    if outward > 0 then
        local normalImpulse = outward*(1+restitution(outward))
        body.vx -= normalImpulse*nx
        body.vz -= normalImpulse*nz
        local tx,tz = -nz,nx
        local slip = body.vx*tx+body.vz*tz+radius*body.spin
        -- Unit-mass disc: I = r^2/2; contact inverse mass is 1+r^2/I.
        local friction = math.clamp(-slip/3,-.12*normalImpulse,.12*normalImpulse)
        body.vx += friction*tx
        body.vz += friction*tz
        body.spin += 2*friction/radius
    end
end
local function collide(a,b,radius)
    local dx,dz = b.x-a.x,b.z-a.z
    local distance = math.sqrt(dx*dx+dz*dz)
    if distance >= radius*2 then return end
    local nx,nz = 1,0
    if distance > .000001 then nx,nz = dx/distance,dz/distance end
    local correction = (radius*2-distance)*.5
    a.x -= nx*correction
    a.z -= nz*correction
    b.x += nx*correction
    b.z += nz*correction
    local closing = (b.vx-a.vx)*nx+(b.vz-a.vz)*nz
    if closing < 0 then
        local impulse = -closing*(1+restitution(-closing))*.5
        a.vx -= impulse*nx
        a.vz -= impulse*nz
        b.vx += impulse*nx
        b.vz += impulse*nz
        local tx,tz = -nz,nx
        local slip = (b.vx-a.vx)*tx+(b.vz-a.vz)*tz-radius*(a.spin+b.spin)
        -- Tangential impulse changes both translation and rotation; it cannot
        -- add energy merely because touching pieces are sliding past each other.
        local friction = math.clamp(-slip/6,-.12*impulse,.12*impulse)
        a.vx -= friction*tx
        a.vz -= friction*tz
        b.vx += friction*tx
        b.vz += friction*tz
        a.spin -= 2*friction/radius
        b.spin -= 2*friction/radius
    end
end
function M.new(count, separate, rim)
    local self = {bodies={},count=count,separate=false,rim=rim,previous=nil}
    function self:reset()
        self.bodies={}
        for i=1,self.count do
            table.insert(self.bodies,{
                x=(i%2==0 and .025 or -.025),
                z=(i-(self.count+1)/2)*.09,
                vx=0,vz=0,angle=(i-1)*.7,spin=0
            })
        end
        if self.count==1 then self.bodies[1].x=0 end
        self.previous=nil
    end
    function self:step(pose,velocity,dt)
        if dt<=0 or dt>.15 then self.previous=velocity;return end
        local acceleration = self.previous and (velocity-self.previous)/dt or V(0,0,0)
        self.previous=velocity
        local magnitude=vector.magnitude(acceleration)
        if magnitude>30 then acceleration*=30/magnitude end
        local force=inverse(pose.rotation,V(0,-9.81,0)-acceleration)
        local steps=math.ceil(dt*240)
        local h=dt/steps
        local radius=self.rim and .030 or .026
        for _=1,steps do
            for i,body in self.bodies do
                local drag=.16
                body.vx=(body.vx+force.x*h)*math.exp(-drag*h)
                body.vz=(body.vz+force.z*h)*math.exp(-drag*h)
                body.x+=body.vx*h
                body.z+=body.vz*h
                body.angle=(body.angle+body.spin*h)%(2*math.pi)
                body.spin*=math.exp(-.7*h)
            end
            for _=1,8 do
                    for i=1,self.count-1 do
                        for j=i+1,self.count do collide(self.bodies[i],self.bodies[j],radius) end
                    end
                for _,body in self.bodies do confine(body,radius) end
            end
            for _,body in self.bodies do
                if body.vx*body.vx+body.vz*body.vz < .002^2 and math.abs(body.spin)<.01 then
                    body.vx,body.vz,body.spin=0,0,0
                end
            end
        end
    end
    function self:parameters()
        local colours={}
        for _,body in self.bodies do
            table.insert(colours,{
                r=.031+(body.x/.216+.5)*.930,
                g=.07715+((.415-body.z)/.818)*.91797,
                b=body.angle/(2*math.pi)
            })
        end
        while #colours<5 do table.insert(colours,{r=.5,g=.5,b=0}) end
        table.insert(colours,{r=self.count/5,g=self.rim and 1 or 0,b=0})
        return colours
    end
    self:reset()
    return self
end
return M
