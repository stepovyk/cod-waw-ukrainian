import sys, struct, pathlib, collections

def header(raw):
    vals = struct.unpack_from('<9I', raw, 0)
    p = 36
    sc, sp, ac, ap = struct.unpack_from('<iiii', raw, p); p += 16
    strings = []
    if sc:
        p += 4 * sc
        for _ in range(sc):
            e = raw.index(b'\0', p)
            strings.append(raw[p:e].decode('latin1'))
            p = e + 1
        base = p
        for d in range(-4, 8):
            q = base + d
            ok = all(0 <= struct.unpack_from('<i', raw, q + 8*i)[0] < 64 and struct.unpack_from('<i', raw, q + 8*i + 4)[0] == -1 for i in range(min(ac, 50)))
            if ok:
                p = q
                print('align delta', d)
                break
    assets = []
    for _ in range(ac):
        t, ptr = struct.unpack_from('<ii', raw, p); p += 8
        assets.append(t)
    return vals, strings, assets, p

if __name__ == '__main__':
    raw = pathlib.Path(sys.argv[1]).read_bytes()
    vals, strings, assets, p = header(raw)
    print('hdr', [hex(v) for v in vals])
    print('strings', len(strings), strings[:10])
    print('assets', len(assets), 'data@', hex(p))
    print('order', assets[:80])
    print(sorted(collections.Counter(assets).items()))
