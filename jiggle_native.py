"""Content-only material routing and authored settings for spring decks."""
from pathlib import Path
import json,struct,uuid
from fbmod_compat import Archive,unpack,pack
from deck_archive import resource
import jiggle_effect



def attach(data,names):
    if not names:return data
    import eink_mesh
    data=eink_mesh._attach(data,names,'glitch-opaque-mesh.fbmod',is_glitch=True)
    data=eink_mesh.equipped_grip(data,names)
    a=Archive(data);tokens=[]
    for name in names:
        tokens.extend([uuid.uuid5(uuid.NAMESPACE_URL,'reskate/lenticular/deck/'+name.casefold()).hex,
                       uuid.uuid5(uuid.NAMESPACE_URL,'sdec/eink-rim/'+name.casefold()).hex])
    for i,d in enumerate(a.descriptors):
        kind,name=a.key(i)
        if kind not in (1,2) or not any(token in name for token in tokens):continue
        raw=unpack(a.blobs[i]);updated=raw.replace(struct.pack('<Q',5194086253280732641),struct.pack('<Q',jiggle_effect.MATERIAL_KEY))
        if updated!=raw:
            desc,payload=resource({'descriptor':bytes(d).hex()},i,name,updated,pack);a.descriptors[i]=bytearray(desc);a.blobs[i]=payload
    return a.bytes()


def write_materials(projects,folder):
    projects=[p for p in projects if p.get('mode')=='jiggle']
    if not projects:return
    folder=Path(folder);declarations=[]
    for p in projects:
        name=p['name'];item='Own_'+name.replace(' ','_');c=jiggle_effect.settings(p.get('jiggle'))
        declarations.append(dict(part='deck',items=[item],parameters=[
            dict(guid='b2c04e2f74b5671559ff5e880100e616',type='colour',default=[.5,.5,0 if c['attachment']=='top' else 1]),
            dict(guid='e2a9184b35cd468c59ff5e880100548c',type='colour',default=[.5,.5,1]),
            dict(guid='da67cf6aaedcc99459ff5e8801001701',type='colour',default=[c['amount']/100,c['stiffness']/100,1 if c['attachment']=='both' else 0])]))
    (folder/'reskate-materials.json').write_text(json.dumps(dict(schema=1,materials=declarations),indent=2))
