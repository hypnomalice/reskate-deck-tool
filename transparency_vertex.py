"""Optical settings stored in existing mesh chunks, without material overrides."""
import struct,uuid
import transparency_finish
from PIL import ImageColor

def constants(mode,value=None):
    c=transparency_finish.settings(mode,value)
    haze=0. if mode=='case' and c['finish']=='glossy' else c['haze']
    return (*[x/255 for x in ImageColor.getrgb(c['tint'])],c['tint_strength'],
            haze,c['roughness'],c['reflection_strength'],c['thickness'],
            c.get('cuts',140),0.,0.,c.get('rim_mm',1.) if mode=='glass' and c['finish']=='liquid' else 1.)

def patch_mesh(archive,index,mode,value=None):
    """Add one 24-byte stream to shell sections; retain all original streams.

    Native opaque insert and index bytes are preserved. Both the normal and
    duplicate GPU vertex offsets must move when a preceding section grows.
    """
    from fbmod_compat import unpack
    from deck_archive import descriptor_parts
    mesh=bytearray(unpack(archive.blobs[index]))
    u32=lambda at:struct.unpack_from('<I',mesh,at)[0]
    ptr=lambda at:struct.unpack_from('<Q',mesh,at)[0]+16
    record=struct.pack('<12e',*constants(mode,value))
    reports=[]
    for lod_index in range(6):
        lod=ptr(48+8*lod_index);sections=ptr(lod+12);vertex_bytes=u32(lod+92)
        chunk=archive.find(3,str(uuid.UUID(bytes_le=bytes(mesh[lod+116:lod+132]))))
        if chunk is None:raise ValueError('Missing optical mesh chunk')
        before=unpack(archive.blobs[chunk]);insertions=[];old_sections=[]
        for n in range(u32(lod+8)):
            section=sections+384*n;declaration=section+112
            count=mesh[declaration+96];streams=mesh[declaration+97]
            offset=u32(section+40);vertices=u32(section+44)
            old_sections.append((section,offset))
            if n not in (0,1):continue
            if mesh[declaration:declaration+100]!=mesh[declaration+100:declaration+200]:
                raise ValueError('Native optical vertex declarations disagree')
            if count!=6 or streams!=6:raise ValueError('Unsupported optical mesh declaration')
            if any(mesh[declaration+4*i] in (35,36,37) for i in range(count)):
                raise ValueError('Optical stream is already present')
            end=offset+vertices*sum(mesh[declaration+64+2*s] for s in range(streams))
            if end>vertex_bytes:raise ValueError('Optical vertex range exceeds chunk')
            insertions.append((end,record*vertices))
            for k in range(3):mesh[declaration+4*(count+k):declaration+4*(count+k+1)]=bytes((35+k,8,8*k,6))
            mesh[declaration+64+2*streams:declaration+66+2*streams]=bytes((24,0))
            mesh[declaration+96:declaration+98]=bytes((9,7))
            # The section stores two native declarations. Leaving the second
            # one at six streams was found in the missing-shell candidate.
            mesh[declaration+100:declaration+200]=mesh[declaration:declaration+100]
        insertions.sort()
        out=bytearray();cursor=0
        for at,data in insertions:
            if at<cursor:raise ValueError('Overlapping optical streams')
            out+=before[cursor:at];out+=data;cursor=at
        out+=before[cursor:]
        added=sum(len(data) for _,data in insertions)
        for section,old in old_sections:
            updated=old+sum(len(data) for at,data in insertions if at<=old)
            if u32(section+0x54)!=old:raise ValueError('Inconsistent native vertex offsets')
            struct.pack_into('<I',mesh,section+40,updated)
            struct.pack_into('<I',mesh,section+0x54,updated)
        struct.pack_into('<I',mesh,lod+92,vertex_bytes+added)
        assert out[vertex_bytes+added:]==before[vertex_bytes:],'Index data changed'
        archive.replace(chunk,out)
        _,_,tail=descriptor_parts(archive.descriptors[chunk])
        struct.pack_into('<II',archive.descriptors[chunk],tail+8,0,len(out))
        reports.append(dict(lod=lod_index,added_bytes=added,index_bytes_unchanged=True))
    archive.replace(index,mesh)
    return reports
