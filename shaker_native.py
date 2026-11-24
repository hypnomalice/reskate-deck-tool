"""Content-only native contracts for SDEC's shared shaker renderer."""
from pathlib import Path
import struct,uuid,json
import shaker_effect

def attach(data,projects):
    selected=[p for p in projects if p.get('_shaker_prepared')]
    if not selected:return data
    from fbmod_compat import Archive,unpack
    from deck_archive import texture_rid
    archive=Archive(data);old=struct.pack('<Q',1598490372409386545);new=struct.pack('<Q',texture_rid(shaker_effect.MATERIAL))
    tokens={uuid.uuid5(uuid.NAMESPACE_URL,prefix+p['name'].casefold()).hex for p in selected for prefix in ('sdec/eink-rim/','reskate/lenticular/deck/')}
    for i in range(len(archive.blobs)):
        kind,name=archive.key(i)
        if kind==2 and (name.endswith('_mesh') or '/shaders/lenticular_' in name) and any(t in name for t in tokens):
            raw=unpack(archive.blobs[i]);changed=raw.replace(old,new)
            if changed!=raw:archive.replace(i,changed)
    return archive.bytes()

def write_materials(projects,folder):
    selected=[p for p in projects if p.get('mode')=='shaker']
    if not selected:return
    target=Path(folder)/'reskate-materials.json'
    doc=json.loads(target.read_text()) if target.exists() else {'schema':1,'materials':[]}
    for p in selected:
        from creator_engine import validate_name
        item='Own_'+validate_name(p['name']).replace(' ','_')
        doc['materials']=[m for m in doc['materials'] if item not in m['items']]
        doc['materials'].append(dict(part='deck',items=[item],parameters=shaker_effect.parameters(shaker_effect.prepare(p))))
    if len(doc['materials'])>32:raise ValueError('A native pack supports at most 32 declared effect decks. Export a smaller selection.')
    text=json.dumps(doc,indent=2)+'\n'
    if len(text.encode('utf8'))>64*1024:raise ValueError('This pack contains too much detailed shaker data. Export fewer decks together so ReSkate can read all their settings.')
    target.write_text(text)
