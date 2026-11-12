reskate.log('Artwork Springs controller ready: pose observation precedes material lookup.')
local Physics=require('jiggle_physics')
local V=vector.create
local solver=Physics.new({strength=.65,stiffness=50})
local keys={'1567b5742f4ec0b2','8c46cd354b18a9e2'}
local depth,attachment=100,1
local scope=nil
local motionReported=false
local lastTime,lastPosition=nil,nil
local status=''
local function report(text)
 if text~=status then status=text;reskate.log(text) end
end
local function clear()
 if scope then for _,key in keys do reskate.board.clear_parameter('deck',key,scope) end end
 scope=nil;lastTime=nil;lastPosition=nil;motionReported=false;solver:reset()
end
local function supported()
 if not reskate.board.parameter_scopes then return false end
 for _,s in reskate.board.parameter_scopes() do if s=='preview' then return true end end
 return false
end
reskate.on('tick',function()
 if not supported() then clear();report('Artwork Springs preview requires native preview-material support.');return end
 local menu=reskate.menu.game()
 local target=(menu and menu.open) and 'preview' or 'gameplay'
 if scope and scope~=target then clear() end
 local pose=nil
 local motion=nil
 if target=='preview' then
  pose=reskate.room.pose('board')
  if not pose or pose.age>.2 then clear();report('Waiting for the native preview board.');return end
  local now=reskate.time.now();local dt=lastTime and (now-lastTime)/1000 or 0
  local velocity=(lastPosition and dt>0 and dt<.12) and (pose.position-lastPosition)/dt or V(0,0,0)
  motion={deck={position=pose.position,rotation=pose.rotation},velocity=velocity}
 else
  motion=reskate.board.motion()
  if not motion or not motion.deck or not motion.velocity then clear();report('Waiting for the equipped board.');return end
 end
 local params=reskate.board.parameters('deck',target)
 local values={}
 for _,p in params or {} do values[p.key]=p.value end
 local authored=values['94c9dcae6acf67da']
 if not authored or not values[keys[1]] or not values[keys[2]] then clear();report('Waiting for the selected board material and authored spring settings.');return end
 local config={amount=math.clamp(authored.r,0,1)*100,stiffness=math.clamp(authored.g,0,1)*100,attachment=authored.b>.5 and 'both' or 'top'}
 local now=reskate.time.now();local dt=lastTime and (now-lastTime)/1000 or 0
 if scope~=target then solver:reset(motion);dt=0 end
 scope=target;solver.strength=config.amount/100;solver.stiffness=config.stiffness;attachment=config.attachment=='both' and 2 or 1;depth=100;solver:step(motion,dt)
 lastTime=now;lastPosition=motion.deck.position
 for i,m in solver.particles do
  local ok,why=reskate.board.set_parameter('deck',keys[i],{r=.5+m.x*.5,g=.5+m.y*.5,b=i==2 and depth/100 or (attachment==2 and 1 or 0)},scope)
  if not ok then clear();report('Material input unavailable: '..tostring(why));return end
 end
 if not motionReported then
  for _,m in solver.particles do
   if math.abs(m.x)+math.abs(m.y)>.001 then
    reskate.log(string.format('Artwork Springs %s displacement: x=%.5f, y=%.5f (source pixels).',target,m.x*32,m.y*32));motionReported=true;break
   end
  end
 end
 report(target=='preview' and 'Native preview artwork motion active.' or 'Gameplay artwork motion active.')
end)
reskate.on('level_loaded',function() clear() end)
reskate.on('unload',clear)
