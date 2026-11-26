"""Build per-layer Pearl resources from preserved inputs; never touches a live game."""
from pathlib import Path
import re,struct,json,subprocess,zipfile,argparse,hashlib

class IR:
 def __init__(self):self.n=0;self.lines=[]
 def val(self,x):return x if isinstance(x,str) else '0x'+struct.pack('>d',struct.unpack('<f',struct.pack('<f',float(x)))[0]).hex().upper()
 def emit(self,s):
  self.n+=1;v='%selective_holo_'+str(self.n);self.lines.append('  '+v+' = '+s);return v
 def op(self,k,a,b):return self.emit(k+' float '+self.val(a)+', '+self.val(b))
 def add(self,a,b):return self.op('fadd',a,b)
 def sub(self,a,b):return self.op('fsub',a,b)
 def mul(self,a,b):return self.op('fmul',a,b)
 def unary(self,k,a):return self.emit(f'call float @dx.op.unary.f32(i32 {k}, float {self.val(a)})')
 def sat(self,a):return self.unary(7,a)
 def cmp(self,k,a,b):return self.emit('fcmp '+k+' float '+self.val(a)+', '+self.val(b))
 def both(self,a,b):return self.emit('and i1 '+a+', '+b)
 def select(self,g,a,b):return self.emit('select i1 '+g+', float '+self.val(a)+', float '+self.val(b))
 def maximum(self,a,b):return self.emit('call float @dx.op.binary.f32(i32 35, float '+self.val(a)+', float '+self.val(b)+')')
 def channel(self,a,c):return self.emit(f'extractvalue %dx.types.ResRet.f32 {a}, {c}')
 def sample(self,h,s,u,v):return self.emit(f'call %dx.types.ResRet.f32 @dx.op.sampleLevel.f32(i32 62, %dx.types.Handle {h}, %dx.types.Handle {s}, float {self.val(u)}, float {self.val(v)}, float undef, float undef, i32 0, i32 0, i32 undef, float 0.000000e+00)')

def dxil(raw):
 at=raw.index(b'DXBC');return raw[at:at+struct.unpack_from('<I',raw,at+24)[0]]

def wrap(raw,meta,code):
 at=raw.index(b'DXBC');oldend=struct.unpack_from('<I',raw,16)[0];end=(at+len(code)+15)&~15
 head=bytearray(raw[:at]);struct.pack_into('<I',head,12,at+len(code)-32);struct.pack_into('<I',head,16,end);struct.pack_into('<I',head,at-4,len(code))
 meta=bytearray(meta);struct.pack_into('<I',meta,0,end)
 return bytes(head)+code+bytes(end-at-len(code))+raw[oldend:],bytes(meta)

IR.div=lambda self,a,b:self.op('fdiv',a,b)
IR.minimum=lambda self,a,b:self.emit('call float @dx.op.binary.f32(i32 36, float '+self.val(a)+', float '+self.val(b)+')')
uniform=bytearray(80)
for offset,values in [(0,(.637597,1,1)),(16,(.5,.5,.5)),(32,(1,1,1)),(48,(1,1,1)),(64,(1,1))]:struct.pack_into('<'+'f'*len(values),uniform,offset,*values)
for offset,value in [(12,2),(44,2),(76,1)]:struct.pack_into('<I',uniform,offset,value)
for offset,value in [(28,.25),(60,.25),(72,1)]:struct.pack_into('<f',uniform,offset,value)
def inline_kernel(source):
 ir=IR();ir.n=9000000
 handles={}
 for m in re.finditer(r'(%\w+) = call %dx.types.Handle @dx.op.createHandle\(i32 57, i8 (\d+), i32 (\d+), i32 (\d+), i1 false\)',source):handles[(int(m[2]),int(m[4]))]=(int(m[3]),m[1])
 # Recognize the same per-texture atlas marker as the accepted first test.
 # Scan the existing artwork slots, including the material's base colour.
 samplerrange,_=handles[(3,0)]
 sampler=ir.emit(f'call %dx.types.Handle @dx.op.createHandle(i32 57, i8 3, i32 {samplerrange}, i32 0, i1 false)')
 atlas_handles=[]
 for m in re.finditer(r'^!(\d+) = !\{i32 (\d+), %"class.Texture2D<vector<float, 4> >"\* undef, !"", i32 0, i32 (\d+), i32 1, i32 2,',source,re.M):
  rid,reg=int(m[2]),int(m[3]);atlas_handles.append(ir.emit(f'call %dx.types.Handle @dx.op.createHandle(i32 57, i8 0, i32 {rid}, i32 {reg}, i1 false)'))
 assert atlas_handles
 active=None
 for h in atlas_handles:
  mark=ir.sample(h,sampler,.875,43/4096);c=[ir.channel(mark,j) for j in range(2)]
  yes=ir.both(ir.both(ir.cmp('ogt',c[0],.852),ir.cmp('olt',c[0],.868)),ir.both(ir.cmp('ogt',c[1],.182),ir.cmp('olt',c[1],.198)))
  flag=ir.sample(h,sampler,.125,56/4096)
  yes=ir.both(yes,ir.both(ir.cmp('olt',ir.channel(flag,0),.6),ir.cmp('ogt',ir.channel(flag,1),.9)))
  active=yes if active is None else ir.emit('or i1 '+active+', '+yes)
 entry='\n'.join(ir.lines)+f'\n  br i1 {active}, label %donor_native_entry, label %donor_native_skip\n\ndonor_native_entry:\n'
 body=kernel
 instanced=bool(re.search(r'@dx.op.loadInput.i32\(i32 4, i32 0,',source))
 split_uv=bool(re.search(r'; TEXCOORD +'+str(0+int(instanced))+r' +xyz ',source))
 offset=int(instanced)
 def input_mapping(m):
  sig,col=int(m[1]),int(m[2]);target=sig+offset
  if split_uv and sig in (0,1) and col==3:target,col=4+offset,(3 if sig==0 else 1)
  return '@dx.op.loadInput.f32(i32 4, i32 '+str(target)+', i32 0, i8 '+str(col)+', '
 body=re.sub(r'@dx.op.loadInput.f32\(i32 4, i32 ([0-3]), i32 0, i8 ([0-3]), ',input_mapping,body)
 extra_array=bool(re.search(r'2darray +T\d+ +t34 ',source))
 body=body.replace('trunc i32 %247 to i4','and i32 %247, 15').replace('lshr i4 -3, %250','lshr i32 13, %250').replace('and i4 %251, 1','and i32 %251, 1').replace('icmp ne i4 %252, 0','icmp ne i32 %252, 0')
 # Reuse only resource registers already declared by the current permutation.
 for m in list(re.finditer(r'(%\w+) = call %dx.types.Handle @dx.op.createHandle\(i32 57, i8 (\d+), i32 (\d+), i32 (\d+), i1 false\)',body)):
  cls,reg=int(m[2]),int(m[4])
  if cls==0:
   if reg<3:reg+=offset
   elif reg in (35,36) and extra_array:reg+=1
  assert (cls,reg) in handles,(cls,reg)
  rid,_=handles[(cls,reg)]
  body=body.replace(m[0],m[0].replace('i8 '+m[2]+', i32 '+m[3]+', i32 '+m[4]+',','i8 '+m[2]+', i32 '+str(rid)+', i32 '+str(reg)+','),1)
 # Original donor material CB1 is handle %10 in this preserved permutation.
 # Replace its loads with typed constants before the other register layouts
 # can reinterpret them. Frame/global constants and texture arrays stay native.
 pattern=r'^  (%\d+) = call %dx.types.CBufRet\.(f32|i32) @dx.op.cbufferLoadLegacy\.(?:f32|i32)\(i32 59, %dx.types.Handle %10, i32 (\d+)\).*$'
 loads={}
 def constant(m):
  name,kind,reg=m[1],m[2],int(m[3]);assert reg*16+16<=len(uniform)
  loads[name]=(kind,struct.unpack_from('<'+('4f' if kind=='f32' else '4i'),uniform,reg*16))
  return ''
 body,n=re.subn(pattern,constant,body,flags=re.M);assert n>=8
 def scalar(m):
  name,kind,parent,channel=m.groups()
  if parent not in loads:return m[0]
  actual,values=loads[parent];assert actual==kind
  value=values[int(channel)]
  return '  '+name+' = '+('fadd float 0.000000e+00, '+ir.val(value) if kind=='f32' else 'add i32 0, '+str(value))
 body=re.sub(r'^  (%\d+) = extractvalue %dx.types.CBufRet\.(f32|i32) (%\d+), ([0-3])$',scalar,body,flags=re.M)
 body=body.replace('@.hca.1','@donor_pearl_palette')
 body=re.sub(r'%([0-9]+)\b',lambda m:'%donor_native_entry' if m[1]=='0' else '%donor_native_'+m[1],body)
 body=re.sub(r'^\s*; <label>:(\d+).*$',lambda m:'donor_native_'+m[1]+':',body,flags=re.M)
 join='''
  br label %donor_native_join
donor_native_skip:
  br label %donor_native_join
donor_native_join:
  %donor_colour_0 = phi float [ %donor_native_366, %donor_native_356 ], [ 0.000000e+00, %donor_native_skip ]
  %donor_colour_1 = phi float [ %donor_native_367, %donor_native_356 ], [ 0.000000e+00, %donor_native_skip ]
  %donor_colour_2 = phi float [ %donor_native_368, %donor_native_356 ], [ 0.000000e+00, %donor_native_skip ]
  br label %donor_base_entry
donor_base_entry:
'''
 # Keep the old implicit entry block's incoming edges pointing at its new name.
 begin=source.index('define void @');function_start=source.index('{',begin)+1;function_end=source.index('\n}',function_start)
 original=source[function_start:function_end]
 original=re.sub(r'%0\b','%donor_base_entry',original)
 source=source[:begin]+palette+'\n\n'+source[begin:function_start]+'\n'+entry+body+'\n'+join+original+source[function_end:]
 # All declarations used by the native code must remain present.
 for declaration in re.findall(r'^declare .+$',native,re.M):
  fn=re.search(r'@([^ (]+)',declaration)[1]
  if not re.search(r'^declare [^\n]*@'+re.escape(fn)+r'\(',source,re.M):
   at=source.index('\nattributes #');source=source[:at]+declaration+'\n'+source[at:]
 return source

def numeric(value):
 try:return struct.unpack('>d',bytes.fromhex(value[2:]))[0] if value.startswith('0x') else float(value)
 except ValueError:return None

def layer_coat(source):
 ir=IR();ir.n=11000000
 definitions=dict(re.findall(r'^  (%\w+) = (.+)$',source,re.M));samples=[]
 pattern=r'^  (%\w+) = call %dx.types.ResRet.f32 @dx.op.sample(?:Level|Grad).f32\(i32 \d+, %dx.types.Handle (%\w+), %dx.types.Handle (%\w+), float (%\w+), float (%\w+),.*$'
 for m in re.finditer(pattern,source,re.M):
  key=None;three=False
  two=re.fullmatch(r'%art_sample_(a_)?\d+',m[1])
  if two:
   key='foreground' if two[1] else 'background';u='%direct_front_u' if two[1] else '%direct_back_u';v='%art_v'
  else:
   add=re.fullmatch(r'fadd float ([^,]+), (%\w+)',definitions.get(m[5],''))
   mul=re.fullmatch(r'fmul float (%\w+), ([^,]+)',definitions.get(add[2],'')) if add else None
   if add and mul:
    pairs={(64/4096,960/4096):'foreground',(.25,.25):'middle',(.5,.25):'background'}
    key=pairs.get((numeric(add[1]),numeric(mul[2])));u=m[4];v=mul[1];three=True
  if key:samples.append((m,key,u,v,three))
 counts={'foreground':0,'middle':0,'background':0,'two_plane':0,'three_plane':0}
 for m,key,u,v,three in reversed(samples):
  name,h,s=m.group(1,2,3);ir.lines=[]
  tag=ir.sample(h,s,.875,43/4096);t=[ir.channel(tag,j) for j in range(3)]
  gate=ir.both(ir.both(ir.cmp('ogt',t[0],.852),ir.cmp('olt',t[0],.868)),ir.both(ir.cmp('ogt',t[1],.182),ir.cmp('olt',t[1],.198)))
  flags=ir.sample(h,s,.875,46/4096);fl=[ir.channel(flags,j) for j in range(3)]
  modern=ir.both(ir.both(ir.cmp('ogt',fl[0],.902),ir.cmp('olt',fl[0],.918)),ir.both(ir.cmp('ogt',fl[1],.302),ir.cmp('olt',fl[1],.318)))
  modern=ir.both(modern,ir.both(ir.cmp('ogt',fl[2],.4 if three else .15),ir.cmp('olt',fl[2],.6 if three else .35)))
  if three:
   mode=ir.sample(h,s,.125,56/4096)
   gate=ir.both(gate,ir.both(modern,ir.both(ir.cmp('ogt',ir.channel(mode,0),.15),ir.cmp('ogt',ir.channel(mode,1),.9))))
  else:gate=ir.both(gate,'%direct_mode')
  strength=t[2]
  if key!='background':
   cfg=ir.sample(h,s,.875,(30 if key=='middle' else 26)/4096);c=[ir.channel(cfg,j) for j in range(3)]
   expected=(.88,.23) if key=='middle' else (.87,.21)
   for value,target in zip(c[:2],expected):gate=ir.both(gate,ir.both(ir.cmp('ogt',value,target-.008),ir.cmp('olt',value,target+.008)))
   strength=c[2];gate=ir.both(gate,modern)
  # These fresh extracts leave the original coverage/composition instructions intact.
  raw=[ir.channel(name,j) for j in range(3)]
  alpha=1
  if three:
   layer={'foreground':0,'middle':1,'background':2}[key];left,right=((0,170),(170,341),(341,512))[layer]
   masku=ir.div(ir.add(left+.5,ir.mul(u,right-left-1)),512)
   maskv=ir.add(.75,ir.mul(v,.25));mask=ir.channel(ir.sample(h,s,masku,maskv),2)
   if key!='background':alpha=ir.channel(ir.sample(h,s,u,maskv),layer)
  else:
   maskv=ir.add(2754/4096,ir.mul(v,1340/4096));masks=ir.sample(h,s,u,maskv)
   mask=ir.channel(masks,1 if key=='foreground' else 2)
   if key=='foreground':alpha=ir.channel(masks,0)
   else:
    legacy=ir.sat(ir.mul(ir.sub(ir.maximum(ir.maximum(raw[0],raw[1]),raw[2]),.004),20))
    mask=ir.select(modern,mask,legacy)
  native=['%donor_colour_'+str(j) for j in range(3)]
  peak=ir.maximum(ir.maximum(native[0],native[1]),native[2]);safe=ir.maximum(peak,.0001)
  amount=ir.mul(ir.mul(mask,strength),ir.sat(ir.mul(peak,3)));output=[]
  for j in range(3):
   tint=ir.div(native[j],safe)
   foil=ir.minimum(alpha,ir.sat(ir.add(ir.mul(raw[j],ir.add(.12,ir.mul(tint,2.2))),ir.mul(ir.mul(native[j],.03),alpha))))
   output.append(ir.add(raw[j],ir.mul(ir.sub(foil,raw[j]),amount)))
  # Replace only pre-existing extract uses, before inserting private extracts.
  for j in range(3):
   pat=r'^(  %\w+ = )extractvalue %dx.types.ResRet.f32 '+re.escape(name)+', '+str(j)+r'$'
   source,n=re.subn(pat,lambda e:e[1]+'select i1 '+gate+', float '+output[j]+', float '+raw[j],source,flags=re.M)
   assert n>=1,(name,j)
  # The sample's original line still exists once; source offsets may have moved.
  anchor=source.index(m[0])+len(m[0]);source=source[:anchor]+'\n'+'\n'.join(ir.lines)+source[anchor:]
  counts[key]+=1;counts['three_plane' if three else 'two_plane']+=1
 assert counts['two_plane']>=16 and counts['three_plane']>=3,counts
 return source,counts

def main():
 global kernel,palette,native
 parser=argparse.ArgumentParser();parser.add_argument('--dxc',required=True,type=Path);parser.add_argument('--assembler',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
 args=parser.parse_args();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
 inputs=zipfile.ZipFile(Path(__file__).with_name('baseline.zip'));native=inputs.read('native-pearl.ll').decode().replace('\r\n','\n')
 kernel=native.split('define void @ShaderDomain_Ps() {',1)[1];kernel=kernel[:re.search(r'^  %368 = .*$',kernel,re.M).end()]
 palette=re.search(r'^@\.hca\.1 = .*$',native,re.M)[0].replace('@.hca.1','@donor_pearl_palette')
 assembler=args.assembler.read_text().replace("Path('work/dxc/dxcompiler.dll').resolve()",repr(str(args.dxc/'dxcompiler.dll')));env={'__name__':'layer_assembler'};exec(assembler,env)
 rows=json.loads(inputs.read('resources.json'));resources=[];reports=[]
 for i,(name,_,rid,stem) in enumerate(rows):
  raw=inputs.read(stem+'.bin');meta=inputs.read(stem+'.meta');code=output/(stem+'-before.dxil');code.write_bytes(dxil(raw))
  before=subprocess.check_output([str(args.dxc/'dxc.exe'),'-dumpbin',str(code)]).decode().replace('\r\n','\n')
  source=inline_kernel(before);source,counts=layer_coat(source)
  assert [l for l in before.splitlines() if '@dx.op.storeOutput' in l]==[l for l in source.splitlines() if '@dx.op.storeOutput' in l]
  p=output/stem;p.with_suffix('.ll').write_text(source);p.with_suffix('.unsigned').write_bytes(env['assemble'](source))
  result=subprocess.run([str(args.dxc/'dxv.exe'),'-o='+str(p.with_suffix('.dxil')),str(p.with_suffix('.unsigned'))],capture_output=True,text=True)
  (output/(stem+'-validation.log')).write_text(result.stdout+result.stderr);assert result.returncode==0,(result.stdout+result.stderr)[:3000]
  payload,metadata=wrap(raw,meta,p.with_suffix('.dxil').read_bytes());(output/(stem+'.bin')).write_bytes(payload);(output/(stem+'.meta')).write_bytes(metadata)
  resources.append([name,name,rid,stem]);reports.append(dict(shader=name,**counts,output_stores_unchanged=True))
  print('Validated per-layer native Pearl variant',i,counts,flush=True)
 (output/'resources.tsv').write_text('\n'.join('\t'.join(r) for r in resources)+'\n');(output/'preservation.json').write_text(json.dumps(reports,indent=2))
if __name__=='__main__':main()
