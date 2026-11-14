import re

def patch(source,IR):
 actual,sampler=re.search(r'%holo_front = call .*?Handle (%[\w]+), %dx.types.Handle (%[\w]+)',source).groups()
 cb=re.search(r'(%\w+) = call %dx.types.Handle @dx.op.createHandle\(i32 57, i8 2, i32 \d+, i32 1, i1 false\)',source)[1]
 # Existing effect/header accesses stay on the left atlas tile.
 lines=[];index=0
 for line in source.splitlines():
  if '@dx.op.sample' in line and ('%dx.types.Handle '+actual+',') in line and ' = call ' in line:
   pattern=r'(%dx.types.Handle '+re.escape(sampler)+r', float )([^,]+)'
   match=re.search(pattern,line)
   if match:
    index+=1;name='%layer_old_u_'+str(index);lines.append('  '+name+' = fmul float '+match[2]+', 2.500000e-01');line=line[:match.start(2)]+name+line[match.end(2):]
  lines.append(line)
 source='\n'.join(lines)+'\n'
 class Layers(IR):
  def emit(self,expr):
   self.n+=1;v='%layer_'+str(self.n);self.lines.append('  '+v+' = '+expr);return v
 ir=Layers()
 def sample(page,u,v,channel):
  u=ir.minimum(1-.5/512,ir.maximum(.5/512,u));v=ir.minimum(1-.5/4096,ir.maximum(.5/4096,v))
  value=ir.sample(actual,sampler,ir.add(page*.25,ir.mul(u,.25)),v)
  return ir.channel(value,channel)
 def data(page,u,v,channel):return sample(page,u,ir.add(.5,ir.mul(v,.5)),channel)
 def colour(page,u,v):
  v=ir.minimum(1-.5/2048,ir.maximum(.5/2048,v));return [sample(page,u,ir.add(64/4096,ir.mul(v,1984/4096)),c) for c in range(3)]
 def smooth(v):
  t=ir.sat(v);return ir.mul(ir.mul(t,t),ir.sub(3,ir.mul(2,t)))
 vals=[];masses=[]
 for slot in (2,3):
  val=ir.emit(f'call %dx.types.CBufRet.f32 @dx.op.cbufferLoadLegacy.f32(i32 59, %dx.types.Handle {cb}, i32 {slot})');vals.append(val)
  masses.append([ir.mul(ir.sub(ir.emit(f'extractvalue %dx.types.CBufRet.f32 {val}, {c}'),.5),32*2) for c in (0,1)])
 both=ir.cmp('ogt',ir.emit(f'extractvalue %dx.types.CBufRet.f32 {vals[0]}, 2'),.75)
 top=[sample(0,.125,36/4096,c) for c in range(3)];bottom=[sample(0,.375,36/4096,c) for c in range(3)]
 topx=ir.mul(top[0],512);topy=ir.mul(top[1],2048);bottomx=ir.mul(bottom[0],512);bottomy=ir.mul(bottom[1],2048);radius=ir.maximum(ir.mul(top[2],512),1);split=ir.mul(bottom[2],512)
 ax=ir.sub(bottomx,topx);ay=ir.sub(bottomy,topy);length=ir.maximum(ir.unary(24,ir.add(ir.mul(ax,ax),ir.mul(ay,ay))),1);ax=ir.div(ax,length);ay=ir.div(ay,length);centre_y=ir.mul(ir.add(topy,bottomy),.5)
 movement=ir.mul('%continuous_angle',ir.select('%direct_reverse','%direct_strength',ir.sub(0,'%direct_strength')))
 movement=ir.mul(movement,ir.emit(f'extractvalue %dx.types.CBufRet.f32 {vals[1]}, 2'))
 u='%mask_base_u';v='%mask_base_v';tx=ir.mul(u,512);ty=ir.mul(v,2048);x=tx;y=ty
 def distance(px,py):return ir.unary(24,ir.add(ir.mul(ir.sub(x,px),ir.sub(x,px)),ir.mul(ir.sub(y,py),ir.sub(y,py))))
 for _ in range(8):
  su=ir.div(x,512);sv=ir.div(y,2048);mask=data(0,su,sv,0)
  topweight=ir.mul(smooth(ir.div(distance(topx,topy),radius)),smooth(ir.div(ir.add(ir.mul(ir.sub(x,topx),ax),ir.mul(ir.sub(y,topy),ay)),70)))
  bottomweight=ir.mul(smooth(ir.div(distance(bottomx,bottomy),radius)),smooth(ir.div(ir.add(ir.mul(ir.sub(bottomx,x),ax),ir.mul(ir.sub(bottomy,y),ay)),60)))
  mask=ir.mul(mask,ir.mul(topweight,ir.select(both,bottomweight,1)));blend=smooth(ir.div(ir.add(ir.sub(ir.mul(ir.sub(x,split),ay),ir.mul(ir.sub(y,centre_y),ax)),20),40))
  dx=ir.mul(mask,ir.add(masses[0][0],ir.mul(blend,ir.sub(masses[1][0],masses[0][0]))));dy=ir.mul(mask,ir.add(masses[0][1],ir.mul(blend,ir.sub(masses[1][1],masses[0][1]))))
  height=data(0,su,sv,1);x=ir.add(x,ir.mul(ir.sub(tx,ir.sub(ir.add(x,dx),ir.mul(ir.mul(height,movement),512))),.7));y=ir.add(y,ir.mul(ir.sub(ty,ir.add(y,dy)),.7))
 mu=ir.div(x,512);mv=ir.div(y,2048);bu=u;fu=u
 for _ in range(6):
  bu=ir.mul(ir.add(ir.add(bu,u),ir.mul(data(1,bu,v,0),movement)),.5)
  fu=ir.mul(ir.add(ir.add(fu,u),ir.mul(data(0,fu,v,2),movement)),.5)
 def inside(q):return ir.both(ir.cmp('oge',q,0),ir.cmp('ole',q,1))
 alpha=ir.select(ir.both(inside(mu),inside(mv)),data(1,mu,mv,1),0)
 has_clean=ir.cmp('ogt',sample(1,.125,36/4096,0),.5)
 alpha=ir.mul(alpha,ir.select(has_clean,1,ir.sub(1,data(1,mu,mv,2))))
 front=ir.select(inside(fu),data(1,fu,v,2),0)
 bg=colour(1,bu,v);moving=colour(0,mu,mv);fg=colour(2,fu,v)
 result=[]
 for back,move,fore in zip(bg,moving,fg):
  mixed=ir.add(back,ir.mul(ir.sub(move,back),alpha));result.append(ir.add(mixed,ir.mul(ir.sub(fore,mixed),front)))
 at=source.index('  call void @dx.op.storeOutput.f32(i32 5, i32 1, i32 0, i8 0,');source=source[:at]+'\n'.join(ir.lines)+'\n'+source[at:]
 for c,value in enumerate(result):
  pattern=rf'(call void @dx.op.storeOutput.f32\(i32 5, i32 1, i32 0, i8 {c}, float )%\w+(\))'
  source,n=re.subn(pattern,rf'\g<1>{value}\2',source);assert n==1
 return source
