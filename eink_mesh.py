"""Attach an item-private board mesh with explicit rim UVs; no stock mesh override."""
from pathlib import Path
import struct,uuid
from fbmod_compat import Archive,unpack,pack
from deck_archive import ebx_edit,descriptor_parts,resource,texture_rid,lookup_add
from ebx_tools import Ebx

def attach(data, names, glitch_names=()):
    a=Archive(data);seed=Archive((Path(__file__).parent/'assets/eink-rim-mesh.fbmod').read_bytes())
    seen=set()
    for i in range(len(seed.blobs)):
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
    selected=[i for i in range(10,26) if i!=20]
    for title in names:
        ns=uuid.uuid5(uuid.NAMESPACE_URL,'sdec/eink-rim/'+title.casefold())
        token=uuid.uuid5(uuid.NAMESPACE_URL,'reskate/lenticular/deck/'+title.casefold()).hex
        target_item='items/board_bottomart/own_lenticular_'+token
        target_tex=next(i for i in range(len(a.blobs)) if a.key(i)==(1,'characters/customization/reskate/board_bottomart/lenticular_'+token+'_color'))
        target_recipe=next(i for i in range(len(a.blobs)) if a.key(i)==(2,'characters/maincharacters/reskate/shaders/lenticular_'+token))
        recipe=unpack(a.blobs[target_recipe]);target_key=struct.unpack_from('<Q',recipe,16)[0]
        if title in glitch_names:
            target_key=5194086253280732641
            changed=bytearray(recipe);struct.pack_into('<Q',changed,16,target_key);a.replace(target_recipe,changed)
        gmap={};rmap={rid(seed,20):rid(a,target_recipe),7035016294165725071:target_key};nmap={seed.key(20)[1]:a.key(target_recipe)[1],seed.key(26)[1]:a.key(target_tex)[1]}
        for i in selected:
            k,n=seed.key(i)
            nmap[n]=n.replace('d3467b69-f212-560d-b104-091e3dc19e01',ns.hex)
            if k==1:
                e=Ebx(unpack(seed.blobs[i]));gmap[e.f[:16]]=uuid.uuid5(ns,'file/'+n).bytes_le
            elif k==3:gmap[uuid.UUID(n).bytes_le]=uuid.uuid5(ns,'chunk/'+n).bytes_le;nmap[n]=str(uuid.UUID(bytes_le=gmap[uuid.UUID(n).bytes_le]))
            elif k==2:rmap[rid(seed,i)]=texture_rid(nmap[n])
        oldtex=Ebx(unpack(seed.blobs[26]));newtex=Ebx(unpack(a.blobs[target_tex]))
        gmap[oldtex.f[:16]]=newtex.f[:16]
        # Both texture imports name different exported instances of the same file.
        for old,new in zip(oldtex.inst[:oldtex.ne],newtex.inst[:newtex.ne]):gmap[oldtex.data[old-16:old]]=newtex.data[new-16:new]
        for i in selected:
            k,n=seed.key(i);raw=unpack(seed.blobs[i]);d=seed.descriptors[i];sha,end,tail=descriptor_parts(d)
            tag=bytes(d[sha+33:end]).decode().replace('items/board_bottomart/own_sdec_clear_case_hazy_teal',target_item)
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
        helper=Path(__file__).parent.parent/'clear-case-test/fix_lookup.exe'
        if not helper.exists():raise RuntimeError('Private mesh registration helper unavailable; do not export an unregistered mesh')
        with tempfile.TemporaryDirectory() as folder:
            f=Path(folder);(f/'data').write_bytes(lr);(f/'meta').write_bytes(lm)
            (f/'pairs').write_text(''.join(x+'\t'+y+'\n' for x,y in pairs),encoding='utf8')
            subprocess.run([str(helper),str(f/'data'),str(f/'meta'),str(f/'pairs'),str(f/'out'),str(f/'outmeta')],check=True,capture_output=True)
            lr=(f/'out').read_bytes();lm=(f/'outmeta').read_bytes()
        # Bundle table contains appearance routes; shader keys belong to the shared shader database.
        ti=a.find(2,'characters/customization/configs/cas_main_bundlereftable')
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
        new=seed.key(25)[1].replace('d3467b69-f212-560d-b104-091e3dc19e01',ns.hex).rsplit('/',1)[-1]
        item=a.find(1,'items/board_bottomart/own_lenticular_'+token)
        raw=ebx_edit(unpack(a.blobs[item]),None,None,{}, {old.encode():new.encode()}, {})
        raw=raw.replace(struct.pack('<I',hash_key(old)),struct.pack('<I',hash_key(new)))
        a.replace(item,raw)
    # Custom-mesh content needs the canonical loader even with a shared runtime.
    if a.find(*seed.key(29)) is None:
        desc=bytearray(seed.descriptors[29]);struct.pack_into('<I',desc,1,len(a.blobs))
        a.descriptors.append(desc);a.blobs.append(seed.blobs[29])
    return a.bytes()
