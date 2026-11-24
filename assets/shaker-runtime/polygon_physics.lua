-- Planar rigid pieces. Convex parts share one mass, pose and angular velocity.
local M={}
local V=vector.create
local function cross(x,z,u,v)return x*v-z*u end
local function inverse(q,v)
 local xyz=V(-q[1],-q[2],-q[3]);local t=vector.cross(xyz,v)*2
 return v+t*q[4]+vector.cross(xyz,t)
end
local function world(b,outlineOnly)
 local p=b.world
 if not p then
  p={outline={v={}},parts={},source={},points={}}
  local function point(v)
   for i,q in p.source do if math.abs(q[1]-v[1])<1e-12 and math.abs(q[2]-v[2])<1e-12 then return p.points[i] end end
   table.insert(p.source,v);local q={0,0};table.insert(p.points,q);return q
  end
  for _,v in b.shape.vertices do table.insert(p.outline.v,point(v)) end
  for _,part in b.shape.parts do
   local q={v={}}
   for _,v in part do table.insert(q.v,point(v)) end
   table.insert(p.parts,q)
  end
  b.world=p
 end
 local c,s=math.cos(b.angle),math.sin(b.angle)
 local lx,lz,hx,hz=math.huge,math.huge,-math.huge,-math.huge
 for i,v in p.source do
  local q=p.points[i];local x,z=b.x+c*v[1]-s*v[2],b.z+s*v[1]+c*v[2];q[1],q[2]=x,z
  if x<lx then lx=x end;if x>hx then hx=x end;if z<lz then lz=z end;if z>hz then hz=z end
 end
 p.outline.loX,p.outline.loZ,p.outline.hiX,p.outline.hiZ=lx,lz,hx,hz
 if not outlineOnly then
  for _,part in p.parts do
   local lx,lz,hx,hz=math.huge,math.huge,-math.huge,-math.huge
   for _,v in part.v do lx=math.min(lx,v[1]);hx=math.max(hx,v[1]);lz=math.min(lz,v[2]);hz=math.max(hz,v[2]) end
   part.loX,part.loZ,part.hiX,part.hiZ=lx,lz,hx,hz
  end
 end
 return p
end
local function project(p,nx,nz)
 local lo,hi=math.huge,-math.huge
 for _,v in p.v do local q=v[1]*nx+v[2]*nz;lo=math.min(lo,q);hi=math.max(hi,q) end
 return lo,hi
end
local function manifold(a,b)
 if a.hiX<b.loX or b.hiX<a.loX or a.hiZ<b.loZ or b.hiZ<a.loZ then return end
 local depth,nx,nz=math.huge,0,0
 for pass=1,2 do
  local p=pass==1 and a or b
  for i,v in p.v do
   local w=p.v[i%#p.v+1];local dx,dz=w[1]-v[1],w[2]-v[2];local l=math.sqrt(dx*dx+dz*dz)
   if l>1e-9 then
    local x,z=dz/l,-dx/l;local al,ah=project(a,x,z);local bl,bh=project(b,x,z)
    if ah<=bl or bh<=al then return end
    local plus,minus=ah-bl,bh-al
    if minus<plus then x,z=-x,-z;plus=minus end
    if plus<depth then depth,nx,nz=plus,x,z end
   end
  end
 end
 if depth==math.huge then return end
 local _,ah=project(a,nx,nz);local bl=project(b,nx,nz)
 local tx,tz=-nz,nx
 local alo,ahi,blo,bhi=math.huge,-math.huge,math.huge,-math.huge
 for _,v in a.v do if v[1]*nx+v[2]*nz>ah-1e-6 then local t=v[1]*tx+v[2]*tz;alo=math.min(alo,t);ahi=math.max(ahi,t) end end
 for _,v in b.v do if v[1]*nx+v[2]*nz<bl+1e-6 then local t=v[1]*tx+v[2]*tz;blo=math.min(blo,t);bhi=math.max(bhi,t) end end
 local low,high=math.max(alo,blo),math.min(ahi,bhi)
 if low>high then local mid=(low+high)*.5;low,high=mid,mid end
 local normal=(ah+bl)*.5
 local out={{x=nx*normal+tx*low,z=nz*normal+tz*low,nx=nx,nz=nz,depth=depth}}
 if high-low>.002 then table.insert(out,{x=nx*normal+tx*high,z=nz*normal+tz*high,nx=nx,nz=nz,depth=depth}) end
 return out
end
local function velocity(b,x,z)
 if not b then return 0,0 end
 return b.vx-b.spin*(z-b.z),b.vz+b.spin*(x-b.x)
end
local function impulse(a,b,c,j,nx,nz)
 local x,z=nx*j,nz*j
 a.vx-=x*a.im;a.vz-=z*a.im;a.spin-=cross(c.x-a.x,c.z-a.z,x,z)*a.ii
 if b then b.vx+=x*b.im;b.vz+=z*b.im;b.spin+=cross(c.x-b.x,c.z-b.z,x,z)*b.ii end
end
local function effective(a,b,c,nx,nz)
 local ra=cross(c.x-a.x,c.z-a.z,nx,nz);local d=a.im+ra*ra*a.ii
 if b then local rb=cross(c.x-b.x,c.z-b.z,nx,nz);d+=b.im+rb*rb*b.ii end
 return d
end
local function solve(a,b,c,position)
 a.touching=true;if b then b.touching=true end
 local ax,az=velocity(a,c.x,c.z);local bx,bz=velocity(b,c.x,c.z)
 local closing=(bx-ax)*c.nx+(bz-az)*c.nz
 if closing<0 then
  local bounce=-closing>.12 and .48 or 0
  local normal=-(1+bounce)*closing/effective(a,b,c,c.nx,c.nz)
  impulse(a,b,c,normal,c.nx,c.nz)
  ax,az=velocity(a,c.x,c.z);bx,bz=velocity(b,c.x,c.z)
  local tx,tz=-c.nz,c.nx;local slip=(bx-ax)*tx+(bz-az)*tz
  local friction=math.clamp(-slip/effective(a,b,c,tx,tz),-.12*normal,.12*normal)
  impulse(a,b,c,friction,tx,tz)
 end
 if position then
  local push=math.max(c.depth-.000015,0)*.55/effective(a,b,c,c.nx,c.nz)
  local ra=cross(c.x-a.x,c.z-a.z,c.nx,c.nz)
  local rb=b and cross(c.x-b.x,c.z-b.z,c.nx,c.nz) or 0
  a.x-=c.nx*push*a.im;a.z-=c.nz*push*a.im;a.angle-=ra*push*a.ii
  if b then b.x+=c.nx*push*b.im;b.z+=c.nz*push*b.im;b.angle+=rb*push*b.ii end
 end
end
local function walls(b,p)
 local contacts={}
 for _,v in p.outline.v do
  local anchor=math.clamp(v[2],-.285,.285);local dx,dz=v[1],v[2]-anchor;local length=math.sqrt(dx*dx+dz*dz)
  if length>.088 then table.insert(contacts,{x=v[1],z=v[2],nx=dx/length,nz=dz/length,depth=length-.088}) end
 end
 table.sort(contacts,function(a,b)return a.depth>b.depth end)
 for i=1,math.min(#contacts,3) do solve(b,nil,contacts[i],true) end
end
local function pair(a,b,pa,pb)
 if (a.x-b.x)^2+(a.z-b.z)^2>(a.shape.radius+b.shape.radius)^2 then return end
 local aa,bb=pa.outline,pb.outline
 if aa.hiX<bb.loX or bb.hiX<aa.loX or aa.hiZ<bb.loZ or bb.hiZ<aa.loZ then return end
 local contacts={}
 for _,x in pa.parts do for _,y in pb.parts do
  local list=manifold(x,y)
  if list then for _,c in list do
   local duplicate=false
   for _,q in contacts do if (q.x-c.x)^2+(q.z-c.z)^2<.002^2 and q.nx*c.nx+q.nz*c.nz>.95 then duplicate=true;if c.depth>q.depth then q.depth=c.depth end;break end end
   if not duplicate then table.insert(contacts,c) end
  end end
 end end
 table.sort(contacts,function(a,b)return a.depth>b.depth end)
 for i=1,math.min(#contacts,6) do solve(a,b,contacts[i],true) end
end
function M.new(shape,count,weights)
 local shapes=shape.vertices and table.create(count,shape) or shape
 local simple=true;for _,s in shapes do if #s.parts~=1 then simple=false end end
 local self={shape=shapes[1],shapes=shapes,authored=not shape.vertices,simpleShapes=simple,count=count,bodies={},rim=true,separate=false,previous=nil}
 function self:reset()
  self.bodies={}
  for i=1,self.count do
   local shape=self.shapes[i]
   local mass=shape.mass*(weights and weights[i] or 1)
   table.insert(self.bodies,{x=(i%2==0 and .02 or -.02),z=(i-(self.count+1)/2)*.12,angle=0,spin=0,vx=0,vz=0,shape=shape,mass=mass,im=1/mass,ii=shape.mass/(mass*shape.inertia)})
  end
  self.previous=nil
  self.sleepFor=0;self.asleep=false;self.sleepForce=nil;self.restAnchors=nil
 end
 function self:step(pose,velocity,dt)
  if dt<=0 or dt>.15 then self.previous=velocity;return end
  local acceleration=self.previous and (velocity-self.previous)/dt or V(0,0,0);self.previous=velocity
  local magnitude=vector.magnitude(acceleration);if magnitude>30 then acceleration*=30/magnitude end
  local force=inverse(pose.rotation,V(0,-9.81,0)-acceleration)
  if self.asleep then
   if vector.magnitude(force-self.sleepForce)<.18 then return end
   self.asleep=false;self.sleepFor=0;self.sleepForce=nil
  end
  for _,b in self.bodies do b.touching=false end
  -- Square contacts need smaller substeps; compound outlines use 120 Hz.
  -- Bound catch-up work after a slow frame.
  local simulated=math.min(dt,1/30)
  local frequency=self.simpleShapes and 240 or 120
  local steps=math.max(1,math.ceil(simulated*frequency-1e-8));local h=simulated/steps
  for _=1,steps do
   for _,b in self.bodies do
    b.vx=(b.vx+force.x*h)*math.exp(-.16*h);b.vz=(b.vz+force.z*h)*math.exp(-.16*h)
    b.spin*=math.exp(-.7*h);b.x+=b.vx*h;b.z+=b.vz*h;b.angle=(b.angle+b.spin*h)%(2*math.pi)
   end
   for _=1,(self.simpleShapes and 5 or 4) do
    local cache={};for i,b in self.bodies do cache[i]=world(b) end
    for i=1,self.count-1 do for j=i+1,self.count do pair(self.bodies[i],self.bodies[j],cache[i],cache[j]) end end
    for _,b in self.bodies do walls(b,world(b,true)) end
   end
   for _,b in self.bodies do
    if b.vx*b.vx+b.vz*b.vz<.002^2 and math.abs(b.spin)<.01 then b.vx,b.vz,b.spin=0,0,0 end
   end
  end
  local settled=true
  for _,b in self.bodies do if not b.touching or b.vx*b.vx+b.vz*b.vz>.02^2 or math.abs(b.spin)>.25 then settled=false end end
  if self.authored then
   -- Compound contacts can cancel a small velocity with positional correction.
   -- Sleep a supported pile only after its actual poses remain within a tiny
   -- window; free movement and continuous rotation keep resetting this window.
   if not self.restAnchors then
    self.restAnchors={};for _,b in self.bodies do table.insert(self.restAnchors,{b.x,b.z,b.angle}) end
   end
   settled=true
   for i,b in self.bodies do
    local p=self.restAnchors[i];local angle=(b.angle-p[3]+math.pi)%(2*math.pi)-math.pi
    if not b.touching or (b.x-p[1])^2+(b.z-p[2])^2>.00075^2 or math.abs(angle)>.025 then settled=false;break end
   end
  end
  if settled then
   if self.sleepForce and vector.magnitude(force-self.sleepForce)>.18 then self.sleepFor=0;self.sleepForce=force end
   self.sleepForce=self.sleepForce or force;self.sleepFor+=dt
   if self.sleepFor>.75 then self.asleep=true;for _,b in self.bodies do b.vx,b.vz,b.spin=0,0,0 end end
  else self.sleepFor=0;self.sleepForce=nil;self.restAnchors=nil end
 end
 function self:parameters()
  local out={}
  for _,b in self.bodies do table.insert(out,{r=.031+(b.x/.216+.5)*.930,g=.07715+((.415-b.z)/.818)*.91797,b=(-b.angle/(2*math.pi))%1}) end
  while #out<5 do table.insert(out,{r=.5,g=.5,b=0}) end
  table.insert(out,{r=self.count/5,g=self.rim and 1 or 0,b=0});return out
 end
 self:reset();return self
end
return M
