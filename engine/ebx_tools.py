from pathlib import Path
import struct, sys

class Ebx:

    def __init__(self, b):
        self.b = b
        self.chunks = {}
        o = 12
        while o < len(b):
            k = b[o:o + 4]
            n = struct.unpack_from('<I', b, o + 4)[0]
            self.chunks[k] = (o + 8, b[o + 8:o + 8 + n])
            o += 8 + n + (n & 1)
        start, d = self.chunks[b'EBXD']
        self.start = start + 15 & ~15
        self.data = b[self.start:start + len(d)]
        _, f = self.chunks[b'EFIX']
        self.f = f
        self.o = 16
        nt = self.u(f)
        self.tg = [self.take(f, 16) for _ in range(nt)]
        ns = self.u(f)
        self.ts = [self.u(f) for _ in range(ns)]
        self.ne = self.u(f)
        ni = self.u(f)
        self.inst = [self.u(f) for _ in range(ni)]
        self.ptr = self.arr(f)
        self.res = self.arr(f)
        nc = self.u(f)
        self.import_start = self.o
        self.imports = [self.take(f, 32) for _ in range(nc)]
        self.imp = self.arr(f)
        self.typ = self.arr(f)
        _, r = self.chunks.get(b'RFL2', self.chunks.get(b'REFL'))
        self.o = 0
        nr = self.u(r)
        ids = [(self.take(r, 16), self.u(r)) for _ in range(nr)]
        nt = self.u(r)
        self.types = []
        for i in range(nt):
            x = struct.unpack_from('<IiHHHH', r, self.o)
            self.o += 16
            self.types.append(dict(name=x[0], first=x[1], count=x[2], typ=x[3] >> 1, size=x[4], align=x[5], id=ids[i] if i < len(ids) else None))
        nf = self.u(r)
        self.fields = []
        for _ in range(nf):
            n, off, t, ref = struct.unpack_from('<IIHH', r, self.o)
            self.o += 12
            self.fields.append(dict(name=n, off=off, typ=t >> 1, ref=ref))
        ng = self.u(r)
        self.o += 12 * ng
        nm = self.u(r)
        self.o += 8 * nm
        if b'RFL2' in self.chunks:
            nn = self.u(r)
            names = {}
            for _ in range(nn):
                n = self.u(r)
                names[n] = self.u(r)
        else:
            names = {x['name']: x['name'] for x in self.types + self.fields}
        strs = self.o
        for x in self.types + self.fields:
            at = strs + names[x['name']]
            x['name'] = r[at:r.index(0, at)].decode()

    def take(self, b, n):
        x = b[self.o:self.o + n]
        self.o += n
        return x

    def u(self, b):
        return struct.unpack('<I', self.take(b, 4))[0]

    def arr(self, b):
        return [self.u(b) for _ in range(self.u(b))]

    def dump(self):
        print('imports', [(i, x.hex()) for i, x in enumerate(self.imports)])
        for off in self.inst:
            fix = struct.unpack_from('<H', self.data, off)[0]
            ti = next((i for i, t in enumerate(self.types) if t['id'] == (self.tg[fix], self.ts[fix])))
            print('INSTANCE', off, self.types[ti]['name'])
            self.obj(ti, off, 0)

    def obj(self, ti, off, depth):
        if depth > 4:
            return
        t = self.types[ti]
        for f in self.fields[t['first']:t['first'] + t['count']]:
            at = off + f['off']
            typ = f['typ'] >> 4 & 31
            print(' ' * depth, f['name'], 'type', typ, 'at', at, 'ref', f['ref'], 'hex', self.data[at:at + 16].hex())
            if typ in [0, 2]:
                self.obj(f['ref'], at, depth + 1)
if __name__ == '__main__':
    Ebx(Path(sys.argv[1]).read_bytes()).dump()
