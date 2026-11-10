"""Attach an item-private board mesh with explicit rim UVs; no stock mesh override."""
from pathlib import Path
import struct,uuid
from fbmod_compat import Archive,unpack,pack
from deck_archive import ebx_edit,descriptor_parts,resource,texture_rid,lookup_add
from ebx_tools import Ebx

def merge_registrations(current, added):
    """Union routes by bundle name, preserving every existing hash and route."""
    def inspect(raw):
        pool, bundles, lookups = (struct.unpack_from('<Q',raw,q)[0] for q in (16,24,8))
        def text(token):
            if token == 0xffffffff:return ''
            at=pool+(token&0x7fffff);length=token>>24
            start=at+4 if token&0x800000 else pool+struct.unpack_from('<I',raw,at+4)[0]
            return text(struct.unpack_from('<I',raw,at)[0])+raw[start:start+length].decode()
        names=['']+[text(struct.unpack_from('<I',raw,bundles+i*8)[0]) for i in range(1,struct.unpack_from('<I',raw,76)[0])]
        rows=[struct.unpack_from('<QII',raw,lookups+i*16) for i in range(struct.unpack_from('<I',raw,72)[0])]
        return pool,bundles,lookups,names,[(h,names[b],text(t),b,t) for h,b,t in rows]
    pool,bundles,lookups,names,left=inspect(current)
    *_,right=inspect(added)
    rows={h:(h,b,t) for h,_,_,b,t in left};routes={h:(n,p) for h,n,p,_,_ in left}
    extra=bytearray();tokens={p:t for _,_,p,_,t in left}
    for h,n,p,_,_ in right:
        if h in rows:
            if routes[h] != (n,p):raise ValueError('Conflicting private mesh registration: '+p)
            continue
        if n not in names:raise ValueError('Private mesh requires an unavailable bundle: '+n)
        if p not in tokens:
            encoded=p.encode();tokens[p]=(bundles+len(extra)-pool)|0x800000|(len(encoded)<<24)
            block=struct.pack('<I',0xffffffff)+encoded;extra+=block+bytes((-len(block))%16)
        rows[h]=(h,names.index(n),tokens[p])
    out=bytearray(current[:bundles])+extra+current[bundles:lookups]
    out+=b''.join(struct.pack('<QII',*rows[h]) for h in sorted(rows))+current[-20:]
    struct.pack_into('<Q',out,8,lookups+len(extra));struct.pack_into('<Q',out,24,bundles+len(extra));struct.pack_into('<I',out,72,len(rows))
    return bytes(out),struct.pack('<IIQ',len(out)-20,20,0)

def attach(data, names, glitch_names=(), *, shared_runtime=False, case_names=()):
    ordinary=[n for n in names if n not in glitch_names and n not in case_names]
    glitches=[n for n in names if n in glitch_names]
    if ordinary:data=_attach(data,ordinary,'eink-rim-mesh.fbmod')
    if glitches:data=_attach(data,glitches,'glitch-opaque-mesh.fbmod',True)
    cases=[n for n in names if n in case_names]
    if cases:data=_attach(data,cases,'case-shell-mesh.fbmod',is_case=True)
    return data

def _attach(data,names,seed_file,is_glitch=False,is_case=False):
    a=Archive(data);seed=Archive((Path(__file__).parent/'assets'/seed_file).read_bytes())
    seed_identity=seed.key(13)[1].rsplit('/',1)[-1].removesuffix('_mesh')
    source_key=struct.unpack_from('<Q',unpack(seed.blobs[20]),16)[0]
    seen=set()
    for i in ([] if is_glitch or is_case else range(len(seed.blobs))):
        if seed.key(i)[0]!=2 or not seed.key(i)[1].endswith('_mesh'):continue
        p=unpack(seed.blobs[i]);U=lambda q:struct.unpack_from('<I',p,q)[0];P=lambda q:struct.unpack_from('<Q',p,q)[0]+16
        for li in range(6):
            l=P(48+li*8);ci=seed.find(3,str(uuid.UUID(bytes_le=p[l+116:l+132])))
            if ci in seen:continue
            seen.add(ci);raw=bytearray(unpack(seed.blobs[ci]));sec=P(l+12)
            for si in range(U(l+8)):
                at=sec+384*si;d=at+112;cur=U(at+40);nv=U(at+44)
                for st in range(p[d+97]):
                    stride=p[d+64+st*2]
                    for ei in range(p[d+96]):
                        usage,fmt,off,stream=p[d+ei*4:d+ei*4+4]
                        if usage==0x21 and stream==st:
                            for j in range(nv):
                                q=cur+off+j*stride;u,v=struct.unpack_from('<2e',raw,q)
                                if u<.5:struct.pack_into('<2e',raw,q,1.25,v)
                    cur+=nv*stride
            seed.replace(ci,raw)
    def rid(ar,i):return struct.unpack_from('<Q',ar.descriptors[i],descriptor_parts(ar.descriptors[i])[2]+4)[0]
    selected=([4,5,6] if is_glitch or is_case else [])+[i for i in range(10,26) if i!=20]
    registration_pairs=[]
    for title in names:
        ns=uuid.uuid5(uuid.NAMESPACE_URL,'sdec/eink-rim/'+title.casefold())
        token=uuid.uuid5(uuid.NAMESPACE_URL,'reskate/lenticular/deck/'+title.casefold()).hex
        target_item='items/board_bottomart/own_lenticular_'+token
        target_tex=next(i for i in range(len(a.blobs)) if a.key(i)==(1,'characters/customization/reskate/board_bottomart/lenticular_'+token+'_color'))
        target_recipe=next(i for i in range(len(a.blobs)) if a.key(i)==(2,'characters/maincharacters/reskate/shaders/lenticular_'+token))
        recipe=unpack(a.blobs[target_recipe]);target_key=struct.unpack_from('<Q',recipe,16)[0]
        if is_glitch or is_case:
            # Native mesh permutations must retain their matching native key.
            # The generated public key resolves to a different vertex layout.
            target_key=source_key
            changed=bytearray(recipe);struct.pack_into('<Q',changed,16,target_key);a.replace(target_recipe,changed)
        gmap={};rmap={rid(seed,20):rid(a,target_recipe),source_key:target_key};nmap={seed.key(20)[1]:a.key(target_recipe)[1],seed.key(26)[1]:a.key(target_tex)[1]}
        for i in selected:
            k,n=seed.key(i)
            nmap[n]=n.replace(seed_identity,ns.hex)
            if (is_glitch or is_case) and i in (4,5):nmap[n]=nmap[n]+'_'+ns.hex
            if k==1:
                e=Ebx(unpack(seed.blobs[i]));gmap[e.f[:16]]=uuid.uuid5(ns,'file/'+n).bytes_le
            elif k==3:gmap[uuid.UUID(n).bytes_le]=uuid.uuid5(ns,'chunk/'+n).bytes_le;nmap[n]=str(uuid.UUID(bytes_le=gmap[uuid.UUID(n).bytes_le]))
            elif k==2:rmap[rid(seed,i)]=texture_rid(nmap[n])
        oldtex=Ebx(unpack(seed.blobs[26]));newtex=Ebx(unpack(a.blobs[target_tex]))
        gmap[oldtex.f[:16]]=newtex.f[:16]
        # Both texture imports name different exported instances of the same file.
        for old,new in zip(oldtex.inst[:oldtex.ne],newtex.inst[:newtex.ne]):gmap[oldtex.data[old-16:old]]=newtex.data[new-16:new]
        if is_glitch or is_case:
            # The native vertex/pixel permutation requires the seed's complete
            # parameter layout. Changing only the key of a stock recipe loses
            # native bindings even though the mesh and lookup routes are valid.
            raw=unpack(seed.blobs[20])
            for old,new in gmap.items():raw=raw.replace(old,new)
            for old,new in rmap.items():raw=raw.replace(struct.pack('<Q',old),struct.pack('<Q',new))
            sd=seed.descriptors[20];_,_,st=descriptor_parts(sd)
            size=struct.unpack_from('<I',sd,st+12)[0]
            desc,payload=resource(dict(descriptor=sd.hex()),target_recipe,a.key(target_recipe)[1],raw,pack,
                tag='reskate-cosmetic-dependency:v1',rid=rid(a,target_recipe),meta=bytes(sd[st+16:st+16+size]))
            a.descriptors[target_recipe]=desc;a.blobs[target_recipe]=payload
        for i in selected:
            k,n=seed.key(i);raw=unpack(seed.blobs[i]);d=seed.descriptors[i];sha,end,tail=descriptor_parts(d)
            tag=bytes(d[sha+33:end]).decode().replace(seed.key(8)[1],target_item)
            if k==1:
                e=Ebx(raw);strings={}
                for field in e.ptr:
                    at=field+struct.unpack_from('<q',e.data,field)[0]
                    if 0<=at<len(e.data):
                        stop=e.data.find(0,at)
                        if stop>=0:
                            old=e.data[at:stop];new=old
                            for x,y in nmap.items():new=new.replace(x.encode(),y.encode())
                            if new!=old:strings[old]=new
                raw=ebx_edit(raw,None,None,gmap,strings,rmap)
            else:
                for x,y in gmap.items():raw=raw.replace(x,y)
                for x,y in rmap.items():raw=raw.replace(struct.pack('<Q',x),struct.pack('<Q',y))
            meta=None
            if k==2:
                size=struct.unpack_from('<I',d,tail+12)[0];meta=bytes(d[tail+16:tail+16+size])
            desc,payload=resource(dict(descriptor=d.hex()),len(a.blobs),nmap[n],raw,pack,tag=tag,rid=rmap.get(rid(seed,i)) if k==2 else None,meta=meta)
            a.descriptors.append(desc);a.blobs.append(payload)
        # Register the cloned geometry and appearance names. Copying mesh records
        # alone leaves their new names absent from the native bundle lookup table.
        import tempfile,subprocess
        lookup=seed.find(2,'characters/customization/configs/cas_main_bundlereftable')
        ld=seed.descriptors[lookup];_,_,lt=descriptor_parts(ld)
        ln=struct.unpack_from('<I',ld,lt+12)[0]
        lm=bytes(ld[lt+16:lt+16+ln]);lr=unpack(seed.blobs[lookup])
        pairs=[(x,y) for x,y in nmap.items() if x.endswith(('_ap','_geometry','_geometry_other'))]
        oldap=seed.key(7)[1]
        newap='characters/customization/reskate/board_bottomart/lenticular_'+token+'_ap'
        pairs.append((oldap,newap))
        registration_pairs.extend(pairs)
        helper=Path(__file__).parent/'assets/mesh-register.exe'
        if not helper.exists():raise RuntimeError('Private mesh registration helper unavailable; do not export an unregistered mesh')
        with tempfile.TemporaryDirectory() as folder:
            f=Path(folder);(f/'data').write_bytes(lr);(f/'meta').write_bytes(lm)
            (f/'pairs').write_text(''.join(x+'\t'+y+'\n' for x,y in registration_pairs),encoding='utf8')
            subprocess.run([str(helper),str(f/'data'),str(f/'meta'),str(f/'pairs'),str(f/'out'),str(f/'outmeta')],check=True,capture_output=True)
            lr=(f/'out').read_bytes();lm=(f/'outmeta').read_bytes()
        # Bundle table contains appearance routes; shader keys belong to the shared shader database.
        ti=a.find(2,'characters/customization/configs/cas_main_bundlereftable')
        lr,lm=merge_registrations(unpack(a.blobs[ti]),lr)
        td=a.descriptors[ti];_,_,tt=descriptor_parts(td)
        desc,payload=resource(dict(descriptor=td.hex()),ti,a.key(ti)[1],lr,pack,tag=bytes(td[descriptor_parts(td)[0]+33:descriptor_parts(td)[1]]).decode(),rid=rid(a,ti),meta=lm)
        a.descriptors[ti]=desc;a.blobs[ti]=payload
    # The ownable must select the cloned mesh appearance, not the stock deck AP.
    # Merely registering geometry does not connect it to the selected item.
    from deck_archive import hash_key
    for title in names:
        token=uuid.uuid5(uuid.NAMESPACE_URL,'reskate/lenticular/deck/'+title.casefold()).hex
        ns=uuid.uuid5(uuid.NAMESPACE_URL,'sdec/eink-rim/'+title.casefold())
        old='lenticular_'+token+'_ap'
        new=seed.key(25)[1].replace(seed_identity,ns.hex).rsplit('/',1)[-1]
        item=a.find(1,'items/board_bottomart/own_lenticular_'+token)
        raw=ebx_edit(unpack(a.blobs[item]),None,None,{}, {old.encode():new.encode()}, {})
        raw=raw.replace(struct.pack('<I',hash_key(old)),struct.pack('<I',hash_key(new)))
        a.replace(item,raw)
    # Custom-mesh content needs the canonical loader even with a shared runtime.
    if a.find(*seed.key(29)) is None:
        desc=bytearray(seed.descriptors[29]);struct.pack_into('<I',desc,1,len(a.blobs))
        a.descriptors.append(desc);a.blobs.append(seed.blobs[29])
    return a.bytes()
