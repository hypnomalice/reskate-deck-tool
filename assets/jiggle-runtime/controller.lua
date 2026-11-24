local decks=__DECKS__
local config=nil
local Physics=require('jiggle_physics')
local V=vector.create
local solver=Physics.new({strength=.65,stiffness=50})
local keys={'1567b5742f4ec0b2','8c46cd354b18a9e2'}
local amount,stiffness,depth,attachment=65,50,65,1
local scope=nil
local lastTime,lastPosition=nil,nil
local selectedItem=nil
local status='Artwork spring settings were authored in the Deck Tool.'
local function owns(item)
 local s=string.lower(tostring(item or ''))
 if decks[s] then return decks[s] end
 for _,cfg in decks do if string.find(s,cfg.token,1,true) then return cfg end end
 return nil
end
local function report(text)
 if text~=status then status=text;reskate.log(text) end
end
local function clear()
 if scope then for _,key in keys do reskate.board.clear_parameter('deck',key,scope) end end
 scope=nil;lastTime=nil;lastPosition=nil;solver:reset()
end
local function supported()
 if not reskate.board.parameter_scopes then return false end
 for _,s in reskate.board.parameter_scopes() do if s=='preview' then return true end end
 return false
end
reskate.on('tick',function()
 if not supported() then clear();report('This test requires the preview-enabled runtime.');return end
 local menu=reskate.menu.game()
 local target=(menu and menu.open) and 'preview' or 'gameplay'
 local item=nil
 if target=='preview' then
  local grid=reskate.menu.grid()
  if grid and grid.focused and grid.focused~='' then
   if selectedItem~=grid.focused then clear() end
   selectedItem=grid.focused
  end
  -- Native material declarations below verify the actual rendered item too.
  config=owns(selectedItem)
  if not config then clear();report('Select a deck from this artwork pack.');return end
 else
  selectedItem=nil
  for _,part in reskate.outfit.board() or {} do if owns(part.item) then item=part.item;break end end
  config=owns(item)
  if not config then clear();report('Equip a test deck for gameplay motion.');return end
 end
 if scope and scope~=target then clear() end
 local pose=nil
 local motion=nil
 if target=='preview' then
  pose=reskate.room.pose('board')
  if not pose or pose.age>.2 then clear();report('Waiting for the native preview board.');return end
  local params=reskate.board.parameters('deck','preview')
  local has={}
  for _,p in params or {} do has[p.key]=true end
  if not has[keys[1]] or not has[keys[2]] then clear();report('Waiting for the selected deck material to settle.');return end
  local now=reskate.time.now();local dt=lastTime and (now-lastTime)/1000 or 0
  local velocity=(lastPosition and dt>0 and dt<.12) and (pose.position-lastPosition)/dt or V(0,0,0)
  motion={deck={position=pose.position,rotation=pose.rotation},velocity=velocity}
 else
  motion=reskate.board.motion()
  if not motion or not motion.deck or not motion.velocity then clear();report('Waiting for the equipped board.');return end
 end
 local now=reskate.time.now();local dt=lastTime and (now-lastTime)/1000 or 0
 if scope~=target then solver:reset(motion);dt=0 end
 scope=target;solver.strength=config.amount/100;solver.stiffness=config.stiffness;attachment=config.attachment=='both' and 2 or 1;depth=100;solver:step(motion,dt)
 lastTime=now;lastPosition=motion.deck.position
 for i,m in solver.particles do
  local ok,why=reskate.board.set_parameter('deck',keys[i],{r=.5+m.x*.5,g=.5+m.y*.5,b=i==2 and depth/100 or (attachment==2 and 1 or 0)},scope)
  if not ok then clear();report('Material input unavailable: '..tostring(why));return end
 end
 report(target=='preview' and 'Native preview artwork motion active.' or 'Gameplay artwork motion active.')
end)
reskate.on('level_loaded',function() selectedItem=nil;clear() end)
reskate.on('unload',clear)
