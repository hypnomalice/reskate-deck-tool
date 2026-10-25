"""Explicit, opt-in separation of a validated renderer from deck content.

ABI 1 preserves existing atlas markers and material keys. This module does not
merge arbitrary third-party shaders or claim that shared program IDs are private.
"""
from pathlib import Path
import hashlib
import json
import struct
import os
import shutil
import tempfile

import deck_archive
from fbmod_compat import Archive, UnsupportedMod, compatible, pack

ABI = 1
FEATURES = ('three-plane-parallax', 'metallic-flakes', 'ink-flow', 'impossible-window','liquid-bottle','multi-image-lenticular','neon-mask','ghost-finish-areas')
RUNTIME_NAME = 'SDEC - Sofis Deck Effect Core'
COMPOSITOR = {
    (1, 'items/cust_board_stickers/skateboardstickercompositetextureset'),
    (1, 'characters/customization/board/loaders/cas_skateboard_sticker_compositor_prefab'),
}


def _runtime_updates():
    assets = deck_archive.ROOT.parent / 'assets/effects-runtime'
    records = json.loads((assets / 'manifest.json').read_text())
    updates = []
    for record in records:
        payload = (assets / record['file']).read_bytes()
        if hashlib.sha256(payload).hexdigest() != record['sha256']:
            raise UnsupportedMod('A runtime resource failed its integrity check.')
        updates.append((record, payload))
    return updates


def shared_keys():
    assets = deck_archive.ROOT.parent / 'assets/sticker-compat'
    records = json.loads((assets / 'manifest.json').read_text())
    return ({(r['kind'], r['name']) for r in records} | COMPOSITOR
            | {(r['kind'], r['name']) for r, _ in _runtime_updates()
               if '_bundlereftable' not in r['name']})


def _subset(archive, indices, title=None):
    result = Archive(archive.bytes())
    result.blobs = [archive.blobs[i] for i in indices]
    result.descriptors = [bytearray(archive.descriptors[i]) for i in indices]
    for index, descriptor in enumerate(result.descriptors):
        struct.pack_into('<I', descriptor, 1, index)
    if title:
        at = 25 + result.prefix[24] + 4
        end = result.prefix.index(0, result.prefix.index(0, at) + 1)
        result.prefix = (result.prefix[:at] + title.encode('utf8') + b'\0IdolRiot\0'
                         + result.prefix[end + 1:])
    return result.bytes()


def build_runtime():
    """Build the full runtime independently of which effects a pack contains."""
    seed = deck_archive.build([
        dict(name='Runtime build seed', mode='classic', texture=bytes(2097152),
             texture_size=(512, 4096), texture_mips=1, resident=True,
             thumb_small=bytes(65536), thumb_large=bytes(589824))
    ], pack, RUNTIME_NAME, 'IdolRiot', independent_shader=True)
    normalized, _ = compatible(seed)
    archive = Archive(normalized)
    shared = (shared_keys() - COMPOSITOR) | {
        (r['kind'], r['name']) for r, _ in _runtime_updates()}
    updates = _runtime_updates()
    for record, payload in updates:
        key = (record['kind'], record['name'])
        index = archive.find(*key)
        if index is None:
            index = len(archive.blobs)
            archive.blobs.append(payload)
            archive.descriptors.append(bytearray())
        archive.blobs[index] = payload
        descriptor = bytearray.fromhex(record['descriptor'])
        struct.pack_into('<I', descriptor, 1, index)
        archive.descriptors[index] = descriptor
    indices = [i for i in range(len(archive.blobs)) if archive.key(i) in shared]
    if {archive.key(i) for i in indices} != shared:
        raise UnsupportedMod('The runtime build is missing a required resource.')
    return _subset(archive, indices, RUNTIME_NAME)


def split_pack(data):
    """Return content, runtime, contract; reject unsupported renderers first."""
    normalized, count = compatible(data)
    archive = Archive(normalized)
    shared = shared_keys()
    runtime_indices = [i for i in range(len(archive.blobs)) if archive.key(i) in shared]
    content_indices = [i for i in range(len(archive.blobs)) if archive.key(i) not in shared]
    # All common shader, empty-texture and Lua resources must be supplied once.
    legacy = json.loads((deck_archive.ROOT.parent / 'assets/sticker-compat/manifest.json').read_text())
    mandatory = {(r['kind'], r['name']) for r in legacy}
    present = {archive.key(i) for i in runtime_indices}
    if not mandatory <= present:
        raise UnsupportedMod('The pack is missing a runtime dependency.')
    content = _subset(archive, content_indices)
    # Keep compositor resolution native; only the runtime owns background
    # residency and tagged deck-foil suppression. Existing content stays valid.
    runtime = build_runtime()
    runtime_archive = Archive(runtime)
    contract = {
        'runtime': RUNTIME_NAME, 'abi': ABI, 'decks': count,
        'runtime_features': list(FEATURES),
        'content_sha256': hashlib.sha256(content).hexdigest(),
        'runtime_resources': [dict(kind=k, name=n) for k, n in sorted(
            runtime_archive.key(i) for i in range(len(runtime_archive.blobs)))],
        'shared_program_ids': True,
        'third_party_compatibility_verified': False,
    }
    return content, runtime, contract


def migrate_file(source, destination, runtime_destination):
    """Write separate new outputs; never replace the input or an existing file."""
    source, destination, runtime_destination = map(
        lambda p: Path(p).resolve(), (source, destination, runtime_destination))
    contract_path = destination.with_suffix('.runtime.json')
    outputs = (destination, runtime_destination, contract_path)
    if source in outputs or len(set(outputs)) != len(outputs):
        raise ValueError('Use separate filenames for the original, content and runtime.')
    if any(p.exists() for p in outputs):
        raise FileExistsError('An output already exists; originals are preserved.')
    content, runtime, contract = split_pack(source.read_bytes())
    created = []
    try:
        for path, data in ((destination, content), (runtime_destination, runtime),
                           (contract_path, json.dumps(contract, indent=2).encode('utf8'))):
            with path.open('xb') as stream:
                created.append(path)
                stream.write(data)
    except Exception:
        for path in created:
            path.unlink()
        raise
    return contract


def write_runtime_export(data, destination, *, overwrite=False):
    """Save content with its runtime and contract, rolling back partial writes."""
    destination = Path(destination).resolve()
    runtime_path = destination.parent / (RUNTIME_NAME + '.fbmod')
    contract_path = destination.with_suffix('.runtime.json')
    if destination == runtime_path:
        raise ValueError('Give your deck pack a different name from the effects runtime.')
    if not overwrite and (destination.exists() or contract_path.exists()):
        raise FileExistsError('The destination already exists; choose another filename.')
    content, runtime, contract = split_pack(data)
    if runtime_path.exists() and runtime_path.read_bytes() != runtime:
        raise ValueError('This folder contains a different effects runtime. Save in a new folder, '
                         'or update it using Effects runtime setup first.')
    payloads = [(runtime_path, runtime),
                (contract_path, json.dumps(contract, indent=2).encode('utf8')),
                (destination, content)]
    committed = []
    with tempfile.TemporaryDirectory(prefix='.reskate-export-', dir=destination.parent) as folder:
        staging = Path(folder)
        originals = {}
        for index, (target, payload) in enumerate(payloads):
            (staging / str(index)).write_bytes(payload)
            if target.exists():
                backup = staging / (str(index) + '.previous')
                shutil.copyfile(target, backup)
                originals[target] = backup
        try:
            for index, (target, _) in enumerate(payloads):
                os.replace(staging / str(index), target)
                committed.append(target)
        except Exception:
            for target in reversed(committed):
                if target in originals:
                    os.replace(originals[target], target)
                else:
                    target.unlink()
            raise
    return contract


def write_content_export(data, destination, *, overwrite=False):
    """Export only artwork/settings; SDEC is installed separately."""
    target=Path(destination).resolve()
    if target.exists() and not overwrite:raise FileExistsError('Choose another filename.')
    content,_,contract=split_pack(data)
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix='.deck-',suffix='.partial',dir=target.parent,delete=False) as file:
        temp=Path(file.name);file.write(content)
    try:os.replace(temp,target)
    finally:
        if temp.exists():temp.unlink()
    return contract
