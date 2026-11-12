import re

def patch_pixel(source,IR,graphic_register):
 actual=re.search(r'(%\w+) = call %dx.types.Handle @dx.op.createHandle\(i32 57, i8 0, i32 \d+, i32 '+str(graphic_register)+r', i1 false\)',source)[1]
 old,sampler=re.search(r'%holo_front = call .*?Handle (%[\w]+), %dx.types.Handle (%[\w]+)',source).groups()
 lines=[]
 for line in source.splitlines():
  if re.match(r'  %[A-Za-z]\w* = call %dx.types.ResRet.f32 @dx.op.sample',line):line=line.replace(f'%dx.types.Handle {old},',f'%dx.types.Handle {actual},',1)
  lines.append(line)
 source='\n'.join(lines)+'\n'
 cb=re.search(r'(%\w+) = call %dx.types.Handle @dx.op.createHandle\(i32 57, i8 2, i32 \d+, i32 1, i1 false\)',source)[1]
 source=source.replace('  %art_u =','  %mask_base_u =',1).replace('  %art_v =','  %mask_base_v =',1)
 ir=IR();ir.n=3100000;masses=[];values=[]
 for slot in (2,3):
  val=ir.emit(f'call %dx.types.CBufRet.f32 @dx.op.cbufferLoadLegacy.f32(i32 59, %dx.types.Handle {cb}, i32 {slot})');values.append(val)
  masses.append([ir.mul(ir.sub(ir.emit(f'extractvalue %dx.types.CBufRet.f32 {val}, {c}'),.5),64) for c in (0,1)])
 both=ir.cmp('ogt',ir.emit(f'extractvalue %dx.types.CBufRet.f32 {values[0]}, 2'),.75)
 def header(u):
  sample=ir.emit(f'call %dx.types.ResRet.f32 @dx.op.sampleLevel.f32(i32 62, %dx.types.Handle {actual}, %dx.types.Handle {sampler}, float {u}, float 0x3F82000000000000, float undef, float undef, i32 0, i32 0, i32 undef, float 0.000000e+00)')
  return [ir.emit(f'extractvalue %dx.types.ResRet.f32 {sample}, {c}') for c in range(3)]
 top_pin=header('1.250000e-01');bottom_pin=header('3.750000e-01')
 radius=ir.maximum(ir.mul(top_pin[2],512),1)
 top_x=ir.mul(top_pin[0],512);top_y=ir.mul(top_pin[1],2048)
 bottom_x=ir.mul(bottom_pin[0],512);bottom_y=ir.mul(bottom_pin[1],2048)
 split=ir.mul(bottom_pin[2],512)

 def smooth(v):
  t=ir.sat(v);return ir.mul(ir.mul(t,t),ir.sub(3,ir.mul(2,t)))
 qx=ir.mul('%mask_base_u',512);qy=ir.mul('%mask_base_v',2048);tx=qx;ty=qy
 # Inverse artwork warp, with the supplied texture mask evaluated in source space.
 # Black is exactly fixed. Boundary feathering and attachment ramps are internal.
 for _ in range(8):
  u=ir.div(qx,512);v=ir.add(.5,ir.div(qy,4096))
  sample=ir.emit(f'call %dx.types.ResRet.f32 @dx.op.sampleLevel.f32(i32 62, %dx.types.Handle {actual}, %dx.types.Handle {sampler}, float {u}, float {v}, float undef, float undef, i32 0, i32 0, i32 undef, float 0.000000e+00)')
  mask=ir.sat(ir.emit(f'extractvalue %dx.types.ResRet.f32 {sample}, 0'))
  def pin_distance(px,py):
   dx=ir.sub(qx,px);dy=ir.sub(qy,py)
   return ir.unary(24,ir.add(ir.mul(dx,dx),ir.mul(dy,dy)))
  top=ir.mul(smooth(ir.div(ir.sub(qy,top_y),70)),smooth(ir.div(pin_distance(top_x,top_y),radius)))
  bottom=ir.mul(smooth(ir.div(ir.sub(bottom_y,qy),60)),smooth(ir.div(pin_distance(bottom_x,bottom_y),radius)))
  mask=ir.mul(mask,ir.mul(top,ir.select(both,bottom,1)))
  blend=smooth(ir.div(ir.sub(qx,ir.sub(split,20)),40))
  dx=ir.mul(mask,ir.add(masses[0][0],ir.mul(blend,ir.sub(masses[1][0],masses[0][0]))))
  dy=ir.mul(mask,ir.add(masses[0][1],ir.mul(blend,ir.sub(masses[1][1],masses[0][1]))))
  qx=ir.add(qx,ir.mul(ir.sub(tx,ir.add(qx,dx)),.7));qy=ir.add(qy,ir.mul(ir.sub(ty,ir.add(qy,dy)),.7))
 ir.lines += [f'  %maid_depth = extractvalue %dx.types.CBufRet.f32 {values[1]}, 2',f'  %art_u = fdiv float {qx}, 5.120000e+02',f'  %art_v = fdiv float {qy}, 2.048000e+03']
 pos=source.index('\n',source.index('  %mask_base_v ='));source=source[:pos]+'\n'+'\n'.join(ir.lines)+source[pos:]
 source=source.replace('%holo_depth_view = fmul float %angle_metric,','%holo_depth_view = fmul float %continuous_angle,')
 source=source.replace('%holo_angle = fmul float %holo_depth_bound, %app_negative_strength','%maid_angle0 = fmul float %holo_depth_bound, %app_negative_strength\n  %holo_angle = fmul float %maid_angle0, %maid_depth')
 source=source.replace('%holo_height = fsub float %art_b_5_1, %direct_balance','%holo_height = fsub float %direct_balance, %direct_balance')
 for c in range(3):
  pat=rf'(call void @dx.op.storeOutput.f32\(i32 5, i32 1, i32 0, i8 {c}, float )%\w+(\))';source,n=re.subn(pat,rf'\g<1>%holo_art{c}\2',source);assert n==1
 for name in ('art_vhalf','art_vfinal'):
  source=re.sub(r'float %'+name+r', float undef',r'float %'+name+'_classic, float undef',source)
 return neutralize_donor_surface(source),8

def neutralize_donor_surface(source):
 # The donor has a base-board normal (t36) and a graphic-layer normal two slots
 # before the graphic colour. Flatten both; keep the authored colour/depth atlas.
 front=re.search(r'%holo_front = call .*?Handle (%[\w]+),',source)
 if not front:raise ValueError('Missing authored graphic sampler')
 graphic=int(re.search(re.escape(front[1])+r' = call %dx.types.Handle @dx.op.createHandle\(i32 57, i8 0, i32 \d+, i32 (\d+),',source)[1])
 count=0
 slots={int(m[2]):m[1] for m in re.finditer(r'(%\w+) = call %dx.types.Handle @dx.op.createHandle\(i32 57, i8 0, i32 \d+, i32 (\d+),',source)}
 for slot in sorted(set(slots)-{graphic}):
  handle=re.search(r'(%\w+) = call %dx.types.Handle @dx.op.createHandle\(i32 57, i8 0, i32 \d+, i32 '+str(slot)+',',source)
  if not handle:raise ValueError('Missing donor normal binding '+str(slot))
  samples=re.findall(r'(%\w+) = call %dx.types.ResRet.f32 @dx.op.sample\w*.f32\(i32 \d+, %dx.types.Handle '+re.escape(handle[1])+',',source)
  changed=0
  for sample in samples:
   pattern=r'(  %\w+ = )extractvalue %dx.types.ResRet.f32 '+re.escape(sample)+r', ([0-3])'
   def flat(m):
    values=('5.000000e-01','5.000000e-01','1.000000e+00','1.000000e+00') if slot in (36,graphic-2) else (('5.000000e-01','5.000000e-01','0.000000e+00','1.000000e+00') if slot==35 else (('1.000000e+00','5.000000e-01','0.000000e+00','1.000000e+00') if slot==graphic-1 else ('1.000000e+00',)*4))
    return m[1]+'fadd float 0.000000e+00, '+values[int(m[2])]
   source,n=re.subn(pattern,flat,source);changed+=n
  if slot in (36,graphic-2,35,graphic-1) and changed<2:raise ValueError('Missing extracted surface channels at '+str(slot))
  count+=changed
 # Every exported G-buffer component may depend on the authored atlas only.
 defs={m[1]:m[2] for m in re.finditer(r'^\s*(%[\w]+) = (.*)$',source,re.M)}
 seen=set()
 def walk(name):
  if name in seen:return
  seen.add(name)
  for value in re.findall(r'%[\w]+',defs.get(name,'')):walk(value)
 for name in re.findall(r'storeOutput.f32\(i32 5, i32 [0-3], i32 0, i8 \d, float (%\w+)',source):walk(name)
 for name in seen:
  line=defs.get(name,'')
  if 'dx.op.sample' not in line:continue
  handle=re.search(r'%dx.types.Handle (%\w+)',line)[1]
  slot=int(re.search(r'i32 (\d+), i1 false',defs[handle])[1])
  if slot!=graphic:raise ValueError('Donor texture still reaches the output at t'+str(slot))
 return source
