import unittest,struct,uuid
import numpy as np
from PIL import Image,ImageDraw
from pathlib import Path
import crystal_finish,eink_mesh
from effect_preview import AtlasPreview
from fbmod_compat import Archive,unpack

class NativeGripTests(unittest.TestCase):
 def test_bare_top_is_static_and_mirrored(self):
  art=Image.new('RGB',(512,1984),'#203040');draw=ImageDraw.Draw(art);draw.rectangle((0,0,120,1983),fill='#e09020');draw.rectangle((350,500,511,1200),fill='#3075dc')
  p=AtlasPreview(crystal_finish.pack(art,dict(grip_tape=False,tint='#ffffff')),'crystal')
  u=(np.arange(40)[None,:]+.5)/40;v=(np.arange(80)[:,None]+.5)/80
  a=np.asarray(crystal_finish.preview(p,-1,u,v,top=True));b=np.asarray(crystal_finish.preview(p,1,u,v,top=True))
  np.testing.assert_array_equal(a,b)
  from effect_preview import display
  expected=np.asarray(display(p.sample(1-u,64/4096+v*1984/4096)))
  np.testing.assert_array_equal(a,expected)
  self.assertFalse(np.array_equal(a,np.asarray(display(p.sample(u,64/4096+v*1984/4096)))))
 def test_native_grip_is_not_generated_in_preview(self):
  p=AtlasPreview(crystal_finish.pack(Image.new('RGB',(512,1984),'red'),dict(grip_tape=True)),'crystal')
  im=crystal_finish.preview(p,.6,np.zeros((1,4)),np.zeros((8,1)),top=True)
  self.assertEqual(im.mode,'RGBA');self.assertEqual(im.getchannel('A').getextrema(),(0,0))
 def test_all_lods_select_native_slot_without_adding_textures(self):
  assets=Path(eink_mesh.__file__).parent/'assets';a=Archive((assets/'case-shell-mesh.fbmod').read_bytes());normal=Archive((assets/'eink-rim-mesh.fbmod').read_bytes())
  title='Test Native Grip';token=uuid.uuid5(uuid.NAMESPACE_URL,'sdec/eink-rim/'+title.casefold()).hex
  indices=[]
  for i in range(len(a.blobs)):
   k,name=a.key(i)
   if k==2 and name.endswith(('_mesh','_mesh_other')):
    suffix='_mesh_other' if name.endswith('_mesh_other') else '_mesh';d=a.descriptors[i];end=d.index(0,5);a.descriptors[i]=d[:5]+('characters/maincharacters/reskate/'+token+suffix).encode()+d[end:];indices.append(i)
  before=list(a.blobs);allowed=set(indices)
  mesh=unpack(a.blobs[13])
  for lod in range(6):
   at=struct.unpack_from('<Q',mesh,48+lod*8)[0]+16
   allowed.add(a.find(3,str(uuid.UUID(bytes_le=mesh[at+116:at+132]))))
  result=Archive(eink_mesh.equipped_grip(a.bytes(),[title]))
  self.assertEqual(len(result.blobs),len(before))
  for i in range(len(before)):
   if i not in allowed:self.assertEqual(result.blobs[i],before[i])
  for i in indices:
   p=unpack(result.blobs[i]);q=unpack(before[i]);other=result.key(i)[1].endswith('_mesh_other');donor=unpack(normal.blobs[21])
   for lod in range(6):
    at=struct.unpack_from('<Q',p,48+lod*8)[0]+16;s=struct.unpack_from('<Q',p,at+12)[0]+16
    if not other:
     dl=struct.unpack_from('<Q',donor,48+lod*8)[0]+16;ds=struct.unpack_from('<Q',donor,dl+12)[0]+16
     self.assertEqual(struct.unpack_from('<I',p,s+32)[0],struct.unpack_from('<I',donor,ds+32)[0]);self.assertEqual(p[s+28],0)
    else:self.assertEqual(struct.unpack_from('<I',p,s+32)[0],0)
    # Native top is routed in the main mesh; the unused other top remains hidden.
    self.assertEqual(p[s+28],0)
