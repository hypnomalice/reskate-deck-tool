local Physics=require("shaker_physics")
local Polygon=require("polygon_physics")
local Shapes=require("shaker_shapes")
local Geometry=require("shaker_geometry")
local controls=require("shaker_controls")
local V=vector.create
local keys={}
for _,guid in controls do
    local bytes={}
    for i=1,16,2 do table.insert(bytes,1,string.sub(guid,i,i+1)) end
    table.insert(keys,table.concat(bytes))
end
local rimMode=1
local solver,scope,last,previous,signature,active
local lastWarning
local lastStatus
local function report(message)
    if lastStatus~=message then reskate.log(message);lastStatus=message end
end
-- Request native rig observation before any material-dependent early return.
if reskate.board.bones then reskate.board.bones() end
local function clear()
    if scope then
        for _,key in keys do reskate.board.clear_parameter("deck",key,scope) end
    end
    solver,scope,last,previous,signature,active=nil,nil,nil,nil,nil,false
end
local function step()
    local menu=reskate.menu.game()
    local target=menu and menu.open and "preview" or "gameplay"
    if scope and scope~=target then clear() end
    -- Both pose and material discovery are lazy readers. Keep both requested
    -- during cold start, item rebuilds and menu changes; neither gates the other.
    local pose,velocity
    if target=="preview" then pose=reskate.room.pose("board")
    else
        local motion=reskate.board.motion()
        pose=motion and motion.deck
        velocity=motion and motion.velocity
    end
    local params=reskate.board.parameters("deck",target)
    if not params then
        last,previous=nil,nil
        if solver then solver.previous=nil end
        report("Shaker waiting: "..target.." material unavailable; pose="..tostring(pose~=nil))
        return
    end
    local authored
    local live={}
    for _,p in params do live[p.key]=p;if p.key==keys[7] then authored=p.value end end
    if not authored then
        if scope then clear() end
        report("Shaker waiting: "..target.." has no shaker declaration ("..#params.." inputs)")
        return
    end
    -- The deck's own configuration is stable across writes to the live input.
    local count=math.clamp(math.floor(authored.r*5+.5),1,3)
    local shapeIndex=math.clamp(math.floor(authored.b*2+.5),0,2)
    local definition=Geometry.signature(live,count)
    if not solver or solver.count~=count or solver.defaultShape~=shapeIndex or solver.defaultRim~=(authored.g>.5) or solver.definition~=definition then
        if definition then solver=Polygon.new(Geometry.read(live,count),count)
        else solver=shapeIndex==0 and Physics.new(count,false,authored.g>.5) or Polygon.new(shapeIndex==1 and Shapes.square or Shapes.cutout,count) end
        solver.definition=definition
        solver.rim=authored.g>.5
        solver.defaultShape=shapeIndex
        solver.defaultSeparate=solver.separate
        solver.defaultRim=solver.rim
        signature=nil
    end
    local separate=solver.defaultSeparate
    local rim=solver.defaultRim
    if rimMode~=1 then rim=rimMode==3 end
    local config=tostring(solver.count)..tostring(separate)..tostring(rim)
    if signature~=config then
        solver.separate,solver.rim=separate,rim
        solver:reset()
        signature=config
    end
    local now=reskate.time.now()
    if pose then
        local dt=last and (now-last)/1000 or 0
        velocity=velocity or (previous and dt>0 and dt<.15 and (pose.position-previous)/dt) or V(0,0,0)
        solver:step(pose,velocity,dt)
    else
        last,previous=nil,nil
        solver.previous=nil
    end
    scope=target
    if pose then last,previous=now,pose.position end
    for i,value in solver:parameters() do
        local current=live[keys[i]]
        local old=current and current.value
        local changed=not old or current.inherited or math.abs(old.r-value.r)>1e-6 or math.abs(old.g-value.g)>1e-6 or math.abs(old.b-value.b)>1e-6
        -- Holds are reapplied by ReSkate itself. Only publish changed values or
        -- a new material's inherited defaults, rather than six native walks per tick.
        if changed then
            local ok,why=reskate.board.set_parameter("deck",keys[i],value,scope)
            if not ok then
                last,previous=nil,nil
                solver.previous=nil
                if not lastWarning or now-lastWarning>2000 then
                    reskate.log("Shaker waiting for the board material: "..tostring(why))
                    lastWarning=now
                end
                return
            end
        end
    end
    if pose then
        report("Shaker active: "..solver.count.." objects in "..scope)
        active=true
    else
        report("Shaker pieces visible; waiting for "..scope.." motion")
        active=false
    end
end
-- Isolate a controller exception so existing SDEC effects remain available.
local failed=false
reskate.on("tick",function()
    if failed then return end
    local ok,why=pcall(step)
    if not ok then
        failed=true
        pcall(clear)
        reskate.log("Shaker controller error: "..tostring(why))
    end
end)
reskate.on("level_loaded",function() clear();failed=false end)
reskate.on("unload",clear)
reskate.menu.page("Shaker Effects",function(ui)
    ui:heading("SHAKER PHYSICS")
    rimMode=ui:dropdown("rim","Acrylic rim",{"Deck default","Off","On"},rimMode)
    if ui:button("reset","RESET PIECES") and solver then solver:reset() end
    ui:note("Pieces share one plane and collide. Acrylic rim settings affect the selected shaker test in preview and gameplay.")
end)

reskate.log("SDEC Shaker controller ready: one shared plane, up to three pieces.")
return true
