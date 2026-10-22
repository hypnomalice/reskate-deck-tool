from pathlib import Path
import struct,json,uuid,hashlib,sys
from ebx_tools import Ebx

ROOT=Path(sys._MEIPASS)/'engine' if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
PER_DECK=[0,1,2,3,4,5,6,7,8,11,12,13,14,17]

def u32(b,p):return struct.unpack_from('<I',b,p)[0]
def u64(b,p):return struct.unpack_from('<Q',b,p)[0]
def hash_key(s):
    h=5381
    for v in s.encode('utf8'):h=((h*33)^v)&0xffffffff
    return h
def fnv(s):
    h=0xcbf29ce484222325
    for v in s.lower().encode():h=((h*0x100000001b3)^v)&0xffffffffffffffff
    return h
def guid(identity,role):return uuid.uuid5(identity,role).bytes_le

def texture_rid(name):
    rid=int.from_bytes(hashlib.sha256(name.encode()).digest()[:8],'little')
    # Tag 10 is interpreted as a pointer. Leave all other IDs unchanged.
    return rid | 1 if rid & 3 == 2 else rid
def riff(e,changes):
    body=b'EBX\0'+b''.join(k+struct.pack('<I',len(changes.get(k,v[1])))+changes.get(k,v[1])+bytes(len(changes.get(k,v[1]))&1) for k,v in e.chunks.items())
    return b'RIFF'+struct.pack('<I',len(body))+body
def ebx_edit(raw,identity,role,guidmap,strings,ridmap):
    e=Ebx(raw);d=bytearray(e.data);f=bytearray(e.f)
    # Export identities are stored immediately before each exported instance.
    for a,z in guidmap.items():
        d=d.replace(a,z);f=f.replace(a,z)
    for field in e.ptr:
        at=field+struct.unpack_from('<q',e.data,field)[0]
        if not 0<=at<len(e.data):continue
        end=e.data.find(0,at)
        if end<0:continue
        old=e.data[at:end]
        if old not in strings:continue
        new=strings[old]
        while len(d)%8:d.append(0)
        dest=len(d);d.extend(new+b'\0');struct.pack_into('<q',d,field,dest-field)
    for field in e.res:
        value=u64(d,field)
        if value in ridmap:struct.pack_into('<Q',d,field,ridmap[value])
    padding=e.start-e.chunks[b'EBXD'][0]
    return riff(e,{b'EBXD':bytes(padding)+d,b'EFIX':bytes(f)})

def descriptor_parts(d):
    end=d.index(0,5);sha=end+1;tagend=d.index(0,sha+33)
    q=tagend+1;tail=q+4+4*u32(d,q)
    return sha,tagend,tail
def resource(template,index,name,raw,cas,tag=None,rid=None,meta=None,chunk_sizes=None,first_mip=None):
    d=bytearray.fromhex(template['descriptor']);oldend=d.index(0,5)
    d=d[:5]+name.encode()+b'\0'+d[oldend+1:]
    struct.pack_into('<I',d,1,index)
    sha,tagend,tail=descriptor_parts(d)
    if tag is not None:
        d=d[:sha+33]+tag.encode()+b'\0'+d[tagend+1:]
        sha,tagend,tail=descriptor_parts(d)
    encoded=cas(raw);d[sha:sha+20]=hashlib.sha1(encoded).digest();struct.pack_into('<Q',d,sha+20,len(raw))
    if rid is not None:struct.pack_into('<Q',d,tail+4,rid)
    if meta is not None:
        assert u32(d,tail+12)==len(meta)
        d[tail+16:tail+16+len(meta)]=meta
    if chunk_sizes is not None:
        if first_mip is not None:
            struct.pack_into('<I',d,tail+20,first_mip)
        first=u32(d,tail+20)
        struct.pack_into('<II',d,tail+8,sum(chunk_sizes[:first]),sum(chunk_sizes[first:]))
    return bytes(d),encoded

def collection(raw,items):
    e=Ebx(raw);d=bytearray(e.data);f=bytearray(e.f)
    # Replace the original custom item's import; append other pack items.
    olditem=Ebx((ROOT/'template-data/17.bin').read_bytes())
    oldpair=olditem.f[:16]+olditem.data[:16]
    i=e.imports.index(oldpair);at=e.import_start+i*32;f[at:at+32]=items[0]
    if len(items)==1:return riff(e,{b'EFIX':bytes(f)})
    target=56+struct.unpack_from('<q',d,56)[0];count=u32(d,target-4);insert=target+count*8
    growth=8*(len(items)-1);first=len(e.imports)
    d[insert:insert]=b''.join(struct.pack('<Q',(first+j)*2+1) for j in range(len(items)-1))
    struct.pack_into('<I',d,target-4,count+len(items)-1)
    for field in e.ptr:
        dest=field+struct.unpack_from('<q',e.data,field)[0]
        if dest>=insert:struct.pack_into('<q',d,field,dest+growth-field)
    after=e.import_start+len(e.imports)*32;nimp=u32(f,after);end=after+4+nimp*4
    imports=[bytes(f[e.import_start+j*32:e.import_start+(j+1)*32]) for j in range(len(e.imports))]+items[1:]
    offsets=e.imp+[insert+8*j for j in range(len(items)-1)]
    f=f[:e.import_start-4]+struct.pack('<I',len(imports))+b''.join(imports)+struct.pack('<I',len(offsets))+b''.join(struct.pack('<I',v) for v in offsets)+f[end:]
    section=e.import_start+len(imports)*32+4+len(offsets)*4
    section+=4+u32(f,section)*4
    for p in [section,section+4,section+8]:
        if u32(f,p)>=insert:struct.pack_into('<I',f,p,u32(f,p)+growth)
    xx=bytearray(e.chunks[b'EBXX'][1]);assert u32(xx,8)==target
    struct.pack_into('<I',xx,12,count+len(items)-1)
    return riff(e,{b'EBXD':bytes(e.start-e.chunks[b'EBXD'][0])+d,b'EFIX':bytes(f),b'EBXX':bytes(xx)})

def bundle_add(raw,paths):
    pool=u64(raw,16);bundles=u64(raw,24);lookups=u64(raw,8);count=u32(raw,72)
    def text(token):
        if token==0xffffffff:return ''
        at=pool+(token&0x7fffff);length=token>>24
        start=at+4 if token&0x800000 else pool+u32(raw,at+4)
        return text(u32(raw,at))+raw[start:start+length].decode()
    rows=[struct.unpack_from('<QII',raw,lookups+i*16) for i in range(count)]
    donor=next(b for _,b,t in rows if text(t).lower()=='characters/skateboard/licensed/deck/common/primitive/graphic/deck_primitive_graphic_00001/2026/deck_primitive_graphic_00001_ap')
    keys={v[0] for v in rows};extra=bytearray()
    for path in paths:
        offset=bundles+len(extra)-pool;encoded=path.encode()
        token=offset|0x800000|(len(encoded)<<24)
        block=struct.pack('<I',0xffffffff)+encoded;extra+=block+bytes((-len(block))%16)
        for value in [path,path.rsplit('/',1)[-1]]:
            key=fnv(value)
            if key not in keys:rows.append((key,donor,token));keys.add(key)
    out=bytearray(raw[:bundles])+extra+raw[bundles:lookups]
    newbundles=bundles+len(extra);newlookups=lookups+len(extra)
    out+=b''.join(struct.pack('<QII',*r) for r in sorted(rows))+raw[-20:]
    struct.pack_into('<Q',out,8,newlookups);struct.pack_into('<Q',out,24,newbundles);struct.pack_into('<I',out,72,len(rows))
    return bytes(out),struct.pack('<IIQ',len(out)-20,20,0)

def lookup_add(raw,meta,keys,oldkey,replace_old=False):
    start=u32(meta,0)+u32(meta,4);at=start;rows={};count=u32(raw,at);at+=4
    for _ in range(count):
        key=u64(raw,at);n=u32(raw,at+8);at+=12;rows[key]=raw[at:at+n*4];at+=n*4
    assert at==len(raw)
    source=rows[oldkey]
    if replace_old:del rows[oldkey]
    for key in keys:rows[key]=source
    tail=struct.pack('<I',len(rows))+b''.join(struct.pack('<QI',k,len(v)//4)+v for k,v in sorted(rows.items()))
    m=bytearray(meta);struct.pack_into('<I',m,8,len(tail))
    return raw[:start]+tail,bytes(m)

def build(decks,cas,title,author,*,independent_shader=False):
    template=ROOT/'depth-template' if any(d.get('mode')=='depth' for d in decks) else ROOT
    manifest=json.loads((template/'template-manifest.json').read_text());ts=manifest['resources']
    base=[(template/'template-data'/f'{i}.bin').read_bytes() for i in range(len(ts))]
    descriptors=[];blobs=[];pairs=[];presets=[];keys=[];recipeold=u64(base[11],16)
    def add(i,name,raw,**kwargs):
        d,b=resource(ts[i],len(blobs),name,raw,cas,**kwargs);descriptors.append(d);blobs.append(b)
    for number,deck in enumerate(decks):
        texture_size=deck.get('texture_size',(512,4096))
        levels=deck.get('texture_mips') or max(texture_size).bit_length()-1
        sizes=[max(1,((texture_size[0]>>n)+3)//4)*max(1,((texture_size[1]>>n)+3)//4)*16 for n in range(levels)]
        if len(deck['texture'])!=sum(sizes):
            raise ValueError('Deck texture size does not match its mip data.')
        identity=uuid.uuid5(uuid.NAMESPACE_URL,'reskate/lenticular/deck/'+deck['name'].casefold())
        token=identity.hex;gmap={};names={};ridmap={};names_by_index={}
        names_by_index[0]=f'characters/customization/reskate/board_bottomart/lenticular_{token}_ap'
        names_by_index[17]=f'items/board_bottomart/own_lenticular_{token}'
        names_by_index[11]=f'characters/maincharacters/reskate/shaders/lenticular_{token}'
        for a,b,suffix in [(1,2,''),(5,6,'_lrg')]:
            names_by_index[a]=names_by_index[b]=f'thumbnail/tool/own_lenticular_{token}{suffix}'
        names_by_index[4]=f'thumbnail/cdn/img_own_lenticular_{token}'
        names_by_index[8]=f'thumbnail/cdn/img_own_lenticular_{token}_lrg'
        names_by_index[12]=names_by_index[13]=f'characters/customization/reskate/board_bottomart/lenticular_{token}_color'
        for i in [3,7,14]:names_by_index[i]=str(uuid.UUID(bytes_le=guid(identity,f'chunk/{i}')))
        for i in PER_DECK:
            names[ts[i]['name'].encode()]=names_by_index[i].encode()
            if ts[i]['kind']==1:
                e=Ebx(base[i]);gmap[e.f[:16]]=guid(identity,f'file/{i}')
                for off in e.inst:gmap[e.data[off-16:off]]=guid(identity,f'export/{i}/{off}')
        for i in [2,6,13]:
            _,_,tail=descriptor_parts(bytearray.fromhex(ts[i]['descriptor']))
            old=u64(bytes.fromhex(ts[i]['descriptor']),tail+4)
            ridmap[old]=texture_rid(names_by_index[i])
        if deck.get('wood_texture'):
            wood_source=Ebx((ROOT.parent/'assets/board-wood.ebx').read_bytes())
            wood_name=f'characters/customization/reskate/board_bottomart/lenticular_{token}_wood'
            wood_file=guid(identity,'wood/file');wood_export=guid(identity,'wood/export')
            wood_chunk=guid(identity,'wood/chunk');wood_rid=texture_rid(wood_name)
            assert wood_source.f[:16]+wood_source.data[:16] in Ebx(base[0]).imports
            gmap[wood_source.f[:16]]=wood_file
            gmap[wood_source.data[:16]]=wood_export
        names[b'lenticular_input3_probe_ap']=names_by_index[0].rsplit('/',1)[-1].encode()
        item=Ebx(base[17]);at=72+struct.unpack_from('<q',item.data,72)[0];oldkey=item.data[at:item.data.index(0,at)]
        newkey=('Own_'+deck['name'].replace(' ','_')).encode();names[oldkey]=newkey
        key=recipeold if number==0 and not independent_shader else int.from_bytes(guid(identity,'shader-key')[:8],'little');keys.append(key)
        for i in PER_DECK:
            raw=base[i];rid=None
            if ts[i]['kind']==1:
                raw=ebx_edit(raw,identity,str(i),gmap,names,ridmap)
                if i==17:
                    e=Ebx(raw);edit=bytearray(raw);struct.pack_into('<I',edit,e.start+88,hash_key(newkey.decode()));raw=bytes(edit)
                    pairs.append(e.f[:16]+e.data[:16])
                elif i in [4,8]:
                    e=Ebx(raw);edit=bytearray(raw)
                    struct.pack_into('<I',edit,e.start+76,hash_key(names_by_index[i]))
                    edit[e.start+56:e.start+76]=hashlib.sha1(deck['thumb_small' if i==4 else 'thumb_large']).digest()
                    raw=bytes(edit)
            elif i in [2,6,13]:
                raw=bytearray(raw)
                chunkindex={2:3,6:7,13:14}[i]
                oldchunk=uuid.UUID(ts[chunkindex]['name']).bytes_le
                assert raw.count(oldchunk)==1
                raw=bytes(raw).replace(oldchunk,uuid.UUID(names_by_index[chunkindex]).bytes_le)
                if i==13 and (tuple(texture_size)!=(512,4096) or deck.get('resident')):
                    raw=bytearray(raw)
                    struct.pack_into('<HH',raw,22,*texture_size)
                    raw[30]=levels
                    struct.pack_into('<15I',raw,56,*(sizes+[0]*(15-levels)))
                    struct.pack_into('<I',raw,116,sum(sizes))
                    raw=bytes(raw)
                if i==13 and deck.get('resident'):
                    raw=bytearray(raw)
                    raw[31]=0
                    raw[32]=0
                    raw[33]=levels
                    struct.pack_into('<I',raw,36,0)
                    # Resident single-mip atlases use the proven non-streamed
                    # header. Setting bit 8 makes these graphics load as wood.
                    struct.pack_into('<H',raw,20,struct.unpack_from('<H',raw,20)[0]&~8)
                    raw=bytes(raw)
                _,_,tail=descriptor_parts(bytearray.fromhex(ts[i]['descriptor']));rid=ridmap[u64(bytes.fromhex(ts[i]['descriptor']),tail+4)]
            elif i==3:raw=deck['thumb_small']
            elif i==7:raw=deck['thumb_large']
            elif i==14:raw=deck['texture']
            elif i==11:
                for a,z in gmap.items():raw=raw.replace(a,z)
                raw=raw.replace(struct.pack('<Q',recipeold),struct.pack('<Q',key))
                _,_,tail=descriptor_parts(bytearray.fromhex(ts[i]['descriptor']))
                rid=int.from_bytes(guid(identity,'recipe-rid')[:8],'little')
            tag=ts[i]['tag'].replace(ts[17]['name'],names_by_index[17]).replace(f'|key={recipeold}|',f'|key={key}|')
            if i==11:
                # These programs are compiled already; there is no board mesh to rebuild.
                tag='reskate-cosmetic-dependency:v1'
            add(i,names_by_index[i],raw,tag=tag,rid=rid,chunk_sizes=sizes if i==14 else None,first_mip=0 if i==14 and deck.get('resident') else None)
        presets.append(names_by_index[0])
        if deck.get('wood_texture'):
            wood_names={}
            for field in wood_source.ptr:
                at=field+struct.unpack_from('<q',wood_source.data,field)[0]
                value=wood_source.data[at:wood_source.data.index(0,at)]
                if value.lower().endswith(b'/deck_gen_popsicle_c'):
                    wood_names[value]=wood_name.encode()
            assert wood_names
            wood_map={wood_source.f[:16]:wood_file,wood_source.data[:16]:wood_export}
            wood_rids={u64(wood_source.data,field):wood_rid for field in wood_source.res}
            wood_raw=ebx_edit(wood_source.b,identity,'wood',wood_map,wood_names,wood_rids)
            wood_asset=Ebx(wood_raw);wood_raw=bytearray(wood_raw)
            struct.pack_into('<HH',wood_raw,wood_asset.start+64,1024,2048)
            add(12,wood_name,bytes(wood_raw))
            wood_header=bytearray(base[13])
            # Base textures need flag 1; the artwork flags make the wood load black.
            struct.pack_into('<H',wood_header,20,1)
            struct.pack_into('<HH',wood_header,22,1024,2048)
            wood_sizes=[max(1,((1024>>n)+3)//4)*max(1,((2048>>n)+3)//4)*16 for n in range(12)]
            assert len(deck['wood_texture'])==sum(wood_sizes)
            wood_header[30:34]=bytes((12,0,0,12))
            struct.pack_into('<I',wood_header,36,0)
            wood_header[40:56]=wood_chunk
            struct.pack_into('<15I',wood_header,56,*(wood_sizes+[0]*3))
            struct.pack_into('<I',wood_header,116,len(deck['wood_texture']))
            add(13,wood_name,bytes(wood_header),rid=wood_rid)
            add(14,str(uuid.UUID(bytes_le=wood_chunk)),deck['wood_texture'],chunk_sizes=wood_sizes,first_mip=0)
    for i in range(len(ts)):
        if i in PER_DECK:continue
        raw=base[i];meta=None
        if i==9:raw=collection(raw,pairs)
        elif i==10:raw,meta=bundle_add(raw,presets)
        elif i==15:
            _,_,tail=descriptor_parts(bytearray.fromhex(ts[i]['descriptor']))
            oldmeta=bytes.fromhex(ts[i]['descriptor'])[tail+16:tail+32]
            raw,meta=lookup_add(raw,oldmeta,keys if independent_shader else keys[1:],recipeold,independent_shader)
        elif i==16:
            rows=dict(struct.unpack_from('<QQ',raw,p) for p in range(0,len(raw),16))
            if recipeold in rows:
                source=rows[recipeold]
                if independent_shader:del rows[recipeold]
                for key in (keys if independent_shader else keys[1:]):rows[key]=source
                raw=b''.join(struct.pack('<QQ',k,v) for k,v in sorted(rows.items()))
        tag='reskate-cosmetic-dependency:v1' if i in [15,16] else None
        add(i,ts[i]['name'],raw,meta=meta,tag=tag)
    if any(deck.get('resident') for deck in decks):
        raw=bytearray((ROOT.parent/'assets/board-compositor.ebx').read_bytes())
        compositor=Ebx(bytes(raw))
        # The stock sticker pass shrinks the whole atlas to 512x2048.
        assert struct.unpack_from('<4I',compositor.data,72)==(128,256,512,512)
        assert struct.unpack_from('<4I',compositor.data,56)==(512,1024,2048,2048)
        struct.pack_into('<4I',raw,compositor.start+72,2048,2048,2048,2048)
        struct.pack_into('<4I',raw,compositor.start+56,16384,16384,16384,16384)
        overrides=[('items/cust_board_stickers/skateboardstickercompositetextureset',bytes(raw))]
        raw=bytearray((ROOT.parent/'assets/board-compositor-prefab.ebx').read_bytes())
        prefab=Ebx(bytes(raw))
        compositor_type=next(t for t in prefab.types if t['name']=='TextureCompositorEntityData')
        instances=[off for off in prefab.inst if (prefab.tg[struct.unpack_from('<H',prefab.data,off)[0]],prefab.ts[struct.unpack_from('<H',prefab.data,off)[0]])==compositor_type['id']]
        assert len(instances)==1
        fields=prefab.fields[compositor_type['first']:compositor_type['first']+compositor_type['count']]
        for name in ('ForceUncompressed','GenerateMipMaps'):
            field=next(f for f in fields if f['name']==name)
            at=prefab.start+instances[0]+field['off']
            assert raw[at]==1
            raw[at]=0
        overrides.append(('characters/customization/board/loaders/cas_skateboard_sticker_compositor_prefab',bytes(raw)))
        levels=('bam_levelroot/bam_levelroot','dingolevel_ftue_island/dingolevel_ftue_island',
                'dingolevel_isle_of_grom/dingolevel_isle_of_grom','dingolevel_mpr/dingolevel_mpr',
                'dingolevel_sdm/dingolevel_sdm_int_001/dingolevel_sdm_int_001',
                'dingolevel_sdm/dingolevel_sdm_int_002/dingolevel_sdm_int_002')
        bundles=[hash_key('win32/levels/game/'+level) for level in levels]
        for name,raw in overrides:
            descriptor,encoded=resource(ts[0],len(blobs),name,raw,cas,tag='')
            descriptor=bytearray(descriptor)
            _,tagend,tail=descriptor_parts(descriptor)
            descriptor=descriptor[:tagend+1]+struct.pack('<I',len(bundles))+b''.join(struct.pack('<I',b) for b in bundles)+descriptor[tail:]
            descriptors.append(descriptor);blobs.append(encoded)
    prefix=bytearray.fromhex(manifest['prefix']);countat=prefix.index(b'\0\xff\xff\xff\xffIcon')-4
    struct.pack_into('<I',prefix,countat,u32(prefix,countat)+len(blobs)-len(ts))
    profile_end=25+prefix[24];at=profile_end+4;end=prefix.index(0,prefix.index(0,at)+1)
    prefix=prefix[:at]+title.encode()+b'\0'+author.encode()+b'\0'+prefix[end+1:]
    head=prefix+b''.join(descriptors);struct.pack_into('<QI',head,12,len(head),len(blobs))
    table=[];off=0
    for b in blobs:table.append(struct.pack('<QQ',off,len(b)));off+=len(b)
    return bytes(head)+b''.join(table)+b''.join(blobs)
