from pathlib import Path
import hashlib
import json
import re
import struct
import uuid

import deck_archive
from ebx_tools import Ebx


class UnsupportedMod(ValueError):
    pass


def unpack(blob):
    data = bytearray()
    offset = 0
    while offset < len(blob):
        if offset + 8 > len(blob):
            raise UnsupportedMod('The FBMOD contains a truncated texture or resource.')
        size, kind, length = struct.unpack_from('>IHH', blob, offset)
        if kind != 0 or size != length or offset + 8 + length > len(blob):
            raise UnsupportedMod('This updater supports uncompressed Deck Tool exports. Re-export this pack from its project instead.')
        data.extend(blob[offset + 8:offset + 8 + length])
        offset += 8 + length
    return bytes(data)


def pack(data):
    return b''.join(struct.pack('>IHH', len(part), 0, len(part)) + part
                    for pos in range(0, len(data), 32768) for part in [data[pos:pos + 32768]])


class Archive:
    def __init__(self, data):
        if len(data) < 24:
            raise UnsupportedMod('This is not a supported FBMOD.')
        table, count = struct.unpack_from('<QI', data, 12)
        if not 24 <= table <= len(data) or count > 100000 or table + count * 16 > len(data):
            raise UnsupportedMod('The FBMOD resource table is invalid.')
        head = data[:table]
        payload = data[table + count * 16:]
        self.blobs = []
        starts = []
        for index in range(count):
            offset, length = struct.unpack_from('<QQ', data, table + index * 16)
            if offset + length > len(payload):
                raise UnsupportedMod('The FBMOD resource data is truncated.')
            self.blobs.append(payload[offset:offset + length])
            found = []
            for kind in (1, 2, 3):
                token = bytes([kind]) + struct.pack('<I', index)
                start = head.find(token)
                while start >= 0:
                    end = head.find(b'\0', start + 5)
                    if end > start + 15 and all(32 <= v < 127 for v in head[start + 5:end]):
                        found.append(start)
                    start = head.find(token, start + 1)
            if len(found) != 1:
                raise UnsupportedMod('The FBMOD uses an unsupported resource layout.')
            starts.append(found[0])
        if not starts:
            raise UnsupportedMod('The FBMOD has no deck resources.')
        self.prefix = bytearray(head[:min(starts)])
        self.descriptors = []
        for start in starts:
            end = min((p for p in starts if p > start), default=len(head))
            self.descriptors.append(bytearray(head[start:end]))

    def key(self, index):
        d = self.descriptors[index]
        return d[0], bytes(d[5:d.index(0, 5)]).decode('ascii')

    def find(self, kind, name):
        return next((i for i in range(len(self.blobs)) if self.key(i) == (kind, name)), None)

    def replace(self, index, raw):
        encoded = pack(raw)
        self.blobs[index] = encoded
        d = self.descriptors[index]
        sha, _, _ = deck_archive.descriptor_parts(d)
        d[sha:sha + 20] = hashlib.sha1(encoded).digest()
        struct.pack_into('<Q', d, sha + 20, len(raw))

    def bytes(self):
        prefix = bytearray(self.prefix)
        at = prefix.index(b'\0\xff\xff\xff\xffIcon') - 4
        # Metadata entries have no payload-table slot, but still count as resources.
        metadata = prefix.count(b'\0\xff\xff\xff\xff')
        if metadata != 5:
            raise UnsupportedMod('The FBMOD metadata layout is not supported.')
        struct.pack_into('<I', prefix, at, len(self.blobs) + metadata)
        head = prefix + b''.join(self.descriptors)
        struct.pack_into('<QI', head, 12, len(head), len(self.blobs))
        table = []
        offset = 0
        for blob in self.blobs:
            table.append(struct.pack('<QQ', offset, len(blob)))
            offset += len(blob)
        return bytes(head) + b''.join(table) + b''.join(self.blobs)


def compatible(data):
    archive = Archive(data)
    assets = deck_archive.ROOT.parent / 'assets/sticker-compat'
    resources = json.loads((assets / 'manifest.json').read_text())
    presets = [i for i in range(len(archive.blobs)) if archive.key(i)[0] == 1
               and re.fullmatch(r'characters/customization/reskate/board_bottomart/lenticular_[0-9a-f]+_ap', archive.key(i)[1])]
    if not presets:
        raise UnsupportedMod('No supported Deck Tool decks were found in this FBMOD.')
    # Validate the complete renderer before changing any resources.
    for record in resources[:6]:
        i = archive.find(record['kind'], record['name'])
        if i is None or hashlib.sha256(unpack(archive.blobs[i])).hexdigest() not in record['supported']:
            raise UnsupportedMod('This pack has an unrecognised renderer. Re-export it from its project instead.')
    for index in presets:
        ap = Ebx(unpack(archive.blobs[index]))
        c = next((i for i, pair in enumerate(ap.imports) if pair[:16].hex() == 'edac44d32a9e164a86d6a2929ff84fc7'), None)
        rgb = next((i for i, pair in enumerate(ap.imports) if pair[:16].hex() == '3a23765f0263f4468bc407b3b5e91d99'), None)
        values = {}
        for n in range(21):
            at = 104 + n * 40
            param = struct.unpack_from('<I', ap.data, at + 16)[0] >> 1
            if param in (c, rgb):
                target = at + 8 + struct.unpack_from('<q', ap.data, at + 8)[0]
                values[param] = struct.unpack_from('<I', ap.data, target)[0] >> 1
        if c is None or rgb is None or set(values) != {c, rgb}:
            raise UnsupportedMod('A deck uses an unsupported material layout.')
        imports = bytearray(ap.f)
        target = ap.import_start + values[rgb] * 32
        imports[target:target + 32] = ap.imports[values[c]]
        archive.replace(index, deck_archive.riff(ap, {b'EFIX': imports}))
        colour_pair = ap.imports[values[c]]
        colour_index = next((i for i in range(len(archive.blobs)) if archive.key(i)[0] == 1
                             and archive.key(i)[1].endswith('_color')
                             and (lambda a: a.f[:16] + a.data[:16])(Ebx(unpack(archive.blobs[i]))) == colour_pair), None)
        if colour_index is None:
            raise UnsupportedMod('The deck artwork texture is missing.')
        name = archive.key(colour_index)[1]
        header_index = archive.find(2, name)
        if header_index is None:
            raise UnsupportedMod('The deck artwork texture header is missing.')
        header = bytearray(unpack(archive.blobs[header_index]))
        if len(header) != 180:
            raise UnsupportedMod('The deck uses an unsupported texture header.')
        width, height = struct.unpack_from('<HH', header, 22)
        size = struct.unpack_from('<I', header, 56)[0]
        chunk_index = archive.find(3, str(uuid.UUID(bytes_le=bytes(header[40:56]))))
        if chunk_index is None or size != max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * 16:
            raise UnsupportedMod('The artwork texture layout is not supported.')
        pixels = unpack(archive.blobs[chunk_index])
        if len(pixels) < size:
            raise UnsupportedMod('The artwork texture is truncated.')
        archive.replace(chunk_index, pixels[:size])
        d = archive.descriptors[chunk_index]
        _, _, tail = deck_archive.descriptor_parts(d)
        struct.pack_into('<II', d, tail + 8, 0, size)
        struct.pack_into('<I', d, tail + 20, 0)
        struct.pack_into('<H', header, 20, 1)
        header[30:34] = bytes((1, 0, 0, 1))
        struct.pack_into('<I', header, 36, 0)
        struct.pack_into('<15I', header, 56, size, *([0] * 14))
        struct.pack_into('<I', header, 116, size)
        archive.replace(header_index, header)
        asset = Ebx(unpack(archive.blobs[colour_index]))
        raw = bytearray(asset.b)
        for offset, value in ((58, width), (62, height), (64, width), (66, height)):
            struct.pack_into('<H', raw, asset.start + offset, value)
        archive.replace(colour_index, raw)
    for record in resources:
        i = archive.find(record['kind'], record['name'])
        if i is None:
            if record['name'] != 'characters/lua/luaskateboardcompositor':
                raise UnsupportedMod('The pack is missing a shared Deck Tool dependency.')
            i = len(archive.blobs)
            archive.blobs.append(b'')
            archive.descriptors.append(bytearray())
        descriptor = bytearray.fromhex(record['descriptor'])
        if record['kind'] == 1 and record['name'].endswith('/lenticular_black_rgb'):
            descriptor = archive.descriptors[i]
        if record in resources[:6]:
            _, _, new_tail = deck_archive.descriptor_parts(descriptor)
            existing = archive.descriptors[i]
            _, _, old_tail = deck_archive.descriptor_parts(existing)
            if struct.unpack_from('<I', existing, old_tail + 12)[0] != 16:
                raise UnsupportedMod('The shader metadata layout is not supported.')
            existing[old_tail + 16:old_tail + 32] = descriptor[new_tail + 16:new_tail + 32]
            descriptor = existing
        struct.pack_into('<I', descriptor, 1, i)
        archive.descriptors[i] = descriptor
        archive.replace(i, (assets / record['file']).read_bytes())
    return archive.bytes(), len(presets)


def update_file(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination:
        raise ValueError('Choose a separate filename; the original pack is kept unchanged.')
    if destination.exists():
        raise ValueError('The destination already exists. Choose another name or folder.')
    result, decks = compatible(source.read_bytes())
    # Exclusive creation also protects against two selected files sharing a name.
    with destination.open('xb') as output:
        output.write(result)
    return decks
