-- Decode the 31-input shaker contract. Metadata is authored, never a held output.
local M={keys=require("shaker_data_keys")}
local function cross(a,b,c)return (b[1]-a[1])*(c[2]-a[2])-(b[2]-a[2])*(c[1]-a[1]) end
local function area(v)
 local total=0;for i,p in v do local q=v[i%#v+1];total+=p[1]*q[2]-q[1]*p[2] end;return total*.5
end
local function hull(a,b)
 local points={};for _,part in {a,b} do for _,p in part do
  local found=false;for _,q in points do if p[1]==q[1] and p[2]==q[2] then found=true;break end end
  if not found then table.insert(points,p) end
 end end
 table.sort(points,function(p,q)return p[1]<q[1] or p[1]==q[1] and p[2]<q[2] end)
 local lower,upper={},{}
 for _,p in points do while #lower>=2 and cross(lower[#lower-1],lower[#lower],p)<=1e-12 do table.remove(lower) end;table.insert(lower,p) end
 for i=#points,1,-1 do local p=points[i];while #upper>=2 and cross(upper[#upper-1],upper[#upper],p)<=1e-12 do table.remove(upper) end;table.insert(upper,p) end
 table.remove(lower);table.remove(upper);for _,p in upper do table.insert(lower,p) end
 return lower
end
local function decompose(vertices)
 local convex=true
 for i,p in vertices do if cross(vertices[(i-2)%#vertices+1],p,vertices[i%#vertices+1]) < -1e-12 then convex=false;break end end
 if convex then return {vertices} end
 local left=table.clone(vertices);local parts={}
 while #left>3 do
  local clipped=false
  for i,b in left do
   local ia=(i-2)%#left+1;local ic=i%#left+1;local a,c=left[ia],left[ic]
   if cross(a,b,c)>1e-12 then
    local inside=false
    for j,p in left do if j~=ia and j~=i and j~=ic and cross(a,b,p)>=-1e-12 and cross(b,c,p)>=-1e-12 and cross(c,a,p)>=-1e-12 then inside=true;break end end
    if not inside then table.insert(parts,{a,b,c});table.remove(left,i);clipped=true;break end
   end
  end
  assert(clipped,"Shaker outline cannot be triangulated")
 end
 table.insert(parts,left)
 local changed=true
 while changed do
  changed=false
  for i=1,#parts do
   for j=1,i-1 do
    local merged=hull(parts[i],parts[j])
    if #merged<=8 and math.abs(area(merged)-area(parts[i])-area(parts[j]))<1e-11 then
     parts[j]=merged;table.remove(parts,i);changed=true;break
    end
   end
   if changed then break end
  end
 end
 assert(#parts<=24,"Shaker outline exceeds its collision budget")
 return parts
end
function M.signature(live,count)
 if not live[M.keys[1][1]] then return nil end
 local values={}
 for i=1,count do for _,key in M.keys[i] do
  local p=assert(live[key],"Shaker piece metadata is missing").value
  table.insert(values,tostring(p.r));table.insert(values,tostring(p.g));table.insert(values,tostring(p.b))
 end end
 return table.concat(values,",")
end
function M.read(live,count)
 local shapes={}
 for i=1,count do
  local c=assert(live[M.keys[i][1]],"Shaker dimensions are missing").value
  local width,height,mass=c.r*.2,c.g*.2,c.b*100
  assert(width>0 and height>0 and width<.16 and height<.16 and mass>0 and mass<=100,"Invalid shaker dimensions or mass")
  local bytes={}
  for j=2,8 do
   local value=assert(live[M.keys[i][j]],"Shaker outline is missing").value
   for _,channel in {value.r,value.g,value.b} do
    local n=math.floor(channel*16777216+.5)
    table.insert(bytes,math.floor(n/65536)%256);table.insert(bytes,math.floor(n/256)%256);table.insert(bytes,n%256)
   end
  end
  local n=bytes[1];assert(n>=3 and n<=31,"Invalid shaker vertex count")
  local vertices={}
  for j=1,n do table.insert(vertices,{bytes[j*2]/255*width,-bytes[j*2+1]/255*height}) end
  if area(vertices)<0 then local rev={};for j=#vertices,1,-1 do table.insert(rev,vertices[j]) end;vertices=rev end
  local sum,cx,cz=0,0,0
  for j,p in vertices do local q=vertices[j%n+1];local a=p[1]*q[2]-q[1]*p[2];sum+=a;cx+=(p[1]+q[1])*a;cz+=(p[2]+q[2])*a end
  assert(sum>1e-9,"Shaker outline has no area");cx/=3*sum;cz/=3*sum
  local radius=0
  for _,p in vertices do p[1]-=cx;p[2]-=cz;radius=math.max(radius,math.sqrt(p[1]^2+p[2]^2)) end
  assert(radius<.082,"Shaker piece does not fit the chamber")
  local moment=0
  for j,p in vertices do local q=vertices[j%n+1];moment+=(p[1]*q[2]-q[1]*p[2])*(p[1]^2+p[1]*q[1]+q[1]^2+p[2]^2+p[2]*q[2]+q[2]^2) end
  local inertia=mass*moment/(6*sum)
  assert(inertia>0,"Invalid shaker inertia")
  table.insert(shapes,{vertices=vertices,parts=decompose(vertices),mass=mass,inertia=inertia,radius=radius})
 end
 return shapes
end
return M
