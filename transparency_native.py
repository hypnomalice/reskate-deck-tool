"""Transparent mesh export and legacy runtime dependency validation."""
from pathlib import Path
import json
import transparency_finish
from PIL import ImageColor

# The native forward (80 byte) and insert (128 byte) material bindings both put
# the original four RGB values at b1 byte offsets 0, 16, 32 and 48.
# These are typed native identities, not arbitrary UUIDs: bytes 8..15
# contain the native colour type and flags and must remain unchanged.
# The private shell binding replaces their keys with these optical identities,
# so optical defaults do not change the inset artwork material or springs.
COLOUR_GUIDS=(
    '5fbdb69cae8bb35b59ff5e880100facd',
    '19c09c5cb6a3d05659ff5e88010042d4',
    '7f637614c9bdc65b59ff5e880100e616',
    '942b7a097841ec5c59ff5e880100548c',
)
AUTHORING_MARKER=.917
PRIVATE_SHARED_DATA={
    'expressionshader/permutationshareddata/4934996381106885165',
    'expressionshader/permutationshareddata/8966678930247011693',
}


def validate_parameter_ids(identities=COLOUR_GUIDS):
    import struct
    for identity in identities:
        raw=bytes.fromhex(identity)
        if len(raw)!=16 or struct.unpack_from('<I',raw,8)[0]!=0x885eff59:
            raise ValueError('Optical parameter identity must retain the native ColorRgb type')


def validate_optical_binding(raw):
    validate_parameter_ids()
    if any(raw.count(bytes.fromhex(identity))!=1 for identity in COLOUR_GUIDS):
        raise ValueError('Optical binding is missing its typed native colour identities')


def validate_runtime_dependencies(updates, base_dependencies=None):
    """A shipped permutation must not depend on another bundle being loaded."""
    import struct,uuid
    from fbmod_compat import unpack
    from deck_archive import descriptor_parts
    if base_dependencies is None:
        import deck_archive
        contract=deck_archive.ROOT.parent/'assets/effects-runtime/base-dependencies.json'
        base_dependencies=json.loads(contract.read_text())['resources'] if contract.exists() else {}
    resources={record['name']:(record,payload) for record,payload in updates if record['kind']==2}
    missing=[]
    for name,(record,payload) in resources.items():
        if not name.startswith('expressionshader/permutation'):continue
        raw=unpack(payload)
        require_shipped=name in PRIVATE_SHARED_DATA
        if name.startswith('expressionshader/permutationshareddata/'):
            fields=((0,'passbinding'),(8,'bindingsignature'),(0x18,'bindingset'),
                    (0x20,'bindingset'),(0x28,'bindingset'),(0x38,'rootslotinitdata'))
            dependencies=['expressionshader/'+kind+'/'+str(struct.unpack_from('<Q',raw,at)[0])
                          for at,kind in fields if struct.unpack_from('<Q',raw,at)[0]]
        else:
            descriptor=bytes.fromhex(record['descriptor']);_,_,tail=descriptor_parts(descriptor)
            if struct.unpack_from('<I',descriptor,tail)[0]!=3565812427:continue
            dependencies=['expressionshader/permutationshareddata/'+str(struct.unpack_from('<Q',raw,0)[0]),
                          'expressionshader/inputlayout/'+str(struct.unpack_from('<Q',raw,16)[0])]
            require_shipped=dependencies[0] in PRIVATE_SHARED_DATA
            meta=descriptor[tail+16:tail+32];size=struct.unpack_from('<I',meta)[0]
            dependencies += ['shaders/bytecode/'+str(uuid.UUID(bytes_le=raw[at:at+16]))
                             for at in range(32,size,16) if any(raw[at:at+16])]
        missing.extend((name,dep) for dep in dependencies
                       if dep not in resources and (require_shipped or dep not in base_dependencies))
    if missing:
        raise ValueError('Incomplete native shader dependencies: '+repr(missing[:8]))


def parameter_values(mode,value=None):
    validate_parameter_ids()
    c=transparency_finish.settings(mode,value)
    tint=[v/255 for v in ImageColor.getrgb(c['tint'])]
    haze=0. if mode=='case' and c['finish']=='glossy' else c['haze']
    return [tint,[c['tint_strength'],haze,c['roughness']],
            [c['reflection_strength']/2,c['thickness']/.03,c['art_depth']],
            [c['border']/.025,c.get('cuts',140)/400,AUTHORING_MARKER]]


def write_materials(projects,folder):
    """Validate optics without adding overrides that could affect other passes.

    Current optical controls travel in the shell's vertex stream. Spring and
    other declarations already written to this folder must remain unchanged.
    """
    projects=[p for p in projects if p.get('mode') in transparency_finish.MODES]
    for project in projects:
        cfg=transparency_finish.settings(project['mode'],project.get(project['mode']))
        if project['mode']=='glass' and cfg['finish']=='liquid':
            path=Path(folder)/'reskate-materials.json'
            data=json.loads(path.read_text()) if path.exists() else dict(schema=1,materials=[])
            item='Own_'+project['name'].replace(' ','_')
            data['materials']=[m for m in data['materials'] if m.get('items')!=[item]]
            data['materials'].append(dict(part='deck',items=[item],parameters=[
                dict(guid='f2750d14eec871a459ff5e8801001713',type='colour',default=[cfg['opacity'],cfg['viscosity'],1]),
                dict(guid='b2c04e2f74b5671559ff5e880100e616',type='colour',default=[.5,.5,.625+.125*cfg['opacity']]),
                dict(guid='e2a9184b35cd468c59ff5e880100548c',type='colour',default=[.5,.5,0])]))
            path.write_text(json.dumps(data,indent=2))


def patch_recipe(raw,mode,value=None):
    """Bake defaults into the native recipe as well as the runtime declaration."""
    import struct
    result=bytearray(raw)
    for guid,colour in zip(COLOUR_GUIDS,parameter_values(mode,value)):
        key=bytes.fromhex(guid)
        if result.count(key)!=1:
            raise ValueError('The shell recipe has an unexpected optical parameter layout')
        at=result.index(key)
        if struct.unpack_from('<I',result,at+16)[0]!=1:
            raise ValueError('The shell optical parameter is not a native colour value')
        struct.pack_into('<3f',result,at+20,*colour)
    return bytes(result)


def attach(data,projects):
    """Attach the selected private transparent shell and contained interior."""
    import uuid
    import eink_mesh
    import transparency_vertex
    from fbmod_compat import Archive,unpack
    selected=[p for p in projects if p.get('mode') in transparency_finish.MODES]
    if not selected:return data
    for project in selected:
        mode=project['mode'];cfg=transparency_finish.settings(mode,project.get(mode))
        profile=(cfg['finish'] if cfg['finish'] in ('water','liquid') else 'glass') if mode=='glass' else ('case-pcb' if cfg['interior']=='pcb' else 'case') if mode=='case' else 'crystal'
        seed='transparency/vertex-'+profile+'-transparent-mesh.fbmod'
        data=eink_mesh._attach(data,[project['name']],seed,is_case=True,extra_indices=(30,))
        archive=Archive(data)
        token=uuid.uuid5(uuid.NAMESPACE_URL,'sdec/eink-rim/'+project['name'].casefold()).hex
        name='characters/maincharacters/reskate/shaders/'+token+'_transparent_shell'
        index=archive.find(2,name)
        if index is None:raise ValueError('The exported deck is missing its private shell recipe')
        expected=json.loads((Path(__file__).resolve().parent/'assets/transparency/vertex-material-keys.json').read_text())
        import struct
        kind='pcb' if profile=='case-pcb' else profile
        if struct.unpack_from('<Q',unpack(archive.blobs[index]),16)[0]!=expected[kind]:
            raise ValueError('Optical mesh template does not match the shared SDEC shader contract')
        mesh=archive.find(2,'characters/maincharacters/reskate/'+token+'_mesh')
        if mesh is None:raise ValueError('The exported deck is missing its optical mesh')
        transparency_vertex.patch_mesh(archive,mesh,mode,cfg)
        data=archive.bytes()
        if cfg['grip_tape']:data=eink_mesh.equipped_grip(data,[project['name']])
    return data
