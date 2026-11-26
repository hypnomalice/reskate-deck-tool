import ctypes as C,uuid,sys
from pathlib import Path
HRESULT=C.c_long;P=C.c_void_p;U=C.c_uint32
class GUID(C.Structure):_fields_=[('data',C.c_ubyte*16)]
def guid(s):return GUID((C.c_ubyte*16).from_buffer_copy(uuid.UUID(s).bytes_le))
dll=C.WinDLL(str(Path('work/dxc/dxcompiler.dll').resolve()))
create=dll.DxcCreateInstance;create.argtypes=[C.POINTER(GUID),C.POINTER(GUID),C.POINTER(P)];create.restype=HRESULT
refs=[]
def obj(clsid,iid):
 p=P();hr=create(C.byref(guid(clsid)),C.byref(guid(iid)),C.byref(p));assert hr>=0,hex(hr&0xffffffff);refs.append(p);return p

def fn(p,i,restype,*args):return C.WINFUNCTYPE(restype,P,*args)(C.cast(p,C.POINTER(C.POINTER(P))).contents[i])
def blob_bytes(p):return C.string_at(fn(p,3,P)(p),fn(p,4,C.c_size_t)(p))
def assemble(text):
 lib=obj('6245d6af-66e0-48fd-80b4-4d271796748c','e5204dc7-d18c-4c3c-bdfb-851673980fe7')
 raw=C.create_string_buffer(text.encode());blob=P();hr=fn(lib,6,HRESULT,P,U,U,C.POINTER(P))(lib,C.cast(raw,P),len(raw)-1,65001,C.byref(blob));assert hr>=0
 asm=obj('d728db68-f903-4f80-94cd-dccf76ec7151','091f7a26-1c1f-4948-904b-e6e3a8a771d5');result=P();hr=fn(asm,3,HRESULT,P,C.POINTER(P))(asm,blob,C.byref(result));assert hr>=0
 status=HRESULT();fn(result,3,HRESULT,C.POINTER(HRESULT))(result,C.byref(status))
 err=P();fn(result,5,HRESULT,C.POINTER(P))(result,C.byref(err))
 if err and blob_bytes(err):print(blob_bytes(err).decode(errors='replace'))
 if status.value<0:raise RuntimeError('Assembly failed '+hex(status.value&0xffffffff))
 compiled=P();fn(result,4,HRESULT,C.POINTER(P))(result,C.byref(compiled));return blob_bytes(compiled)
if __name__=='__main__':
 text=Path(sys.argv[1]).read_text(encoding='utf8');out=assemble(text);Path(sys.argv[2]).write_bytes(out);print('Assembled',len(out),'bytes.')
