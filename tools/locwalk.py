"""Точний розбір LocalizeEntry у зоні T4: послідовні записи, розв'язання посилань на рядки."""
import re, struct, collections, sys, zlib, pathlib, itertools, contextlib, io

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from fftypes import header

INLINE = 0xFFFFFFFF
SAVE = 0xFFFFFFFE  # вбудовано + адреса зберігається в окремій комірці, на яку потім посилаються
NAME_RE = re.compile(rb'^[A-Z0-9_][\x20-\x7e]*_[\x20-\x7e]*$')
SEEDS = [
    # перекривні збіги (?=...), щоб попередній 0xFFFFFFFF не «з'їв» початок першого запису
    re.compile(rb'(?=(?:\xff\xff\xff\xff|\x00\x00\x00\x00)\xff\xff\xff\xff[^\x00]*\x00[A-Z0-9_][\x20-\x7e]*_[\x20-\x7e]*\x00)'),
    re.compile(rb'(?=[\x00-\xff]{3}[\x80-\x9f]\xff\xff\xff\xff[A-Z0-9_][\x20-\x7e]*_[\x20-\x7e]*\x00)'),
]


def cstr(raw, p):
    e = raw.index(b'\0', p)
    return raw[p:e], e + 1


def is_ref(v):
    return v not in (0, INLINE, 0xFFFFFFFE) and (v - 1) >> 29 == 4


def memoff(v):
    return (v - 1) & 0x1FFFFFFF


def walk(raw, p):
    out = []
    while p + 8 <= len(raw):
        vp, np = struct.unpack_from('<II', raw, p)
        if not ((vp in (0, INLINE, SAVE) or is_ref(vp)) and np == INLINE):
            break
        q = p + 8
        value = None
        if vp in (INLINE, SAVE):
            value, q = cstr(raw, q)
            if len(value) > 8192 or value.startswith(b'\xff\xff\xff\xff'):
                break
        name, q = cstr(raw, q)
        if not NAME_RE.match(name):
            break
        out.append({'pos': p, 'end': q, 'vp': vp, 'value': value, 'name': name.decode('ascii')})
        p = q
    return out


def runs_of(raw):
    seen = {}
    for rx in SEEDS:
        for m in rx.finditer(raw):
            if m.start() in seen:
                continue
            for e in walk(raw, m.start()):
                if e['pos'] in seen:
                    break
                seen[e['pos']] = e
    ents = [seen[k] for k in sorted(seen)]
    runs = []
    for e in ents:
        if runs and runs[-1][-1]['end'] == e['pos']:
            runs[-1].append(e)
        else:
            runs.append([e])
    return runs


def layout(run):
    """Відносні адреси рядків у пам'яті: заголовки записів ідуть в інший блок, рядки лежать впритул."""
    mem = 0
    strings = {}
    for e in run:
        if e['vp'] in (INLINE, SAVE):
            strings[mem] = e['value']
            mem += len(e['value']) + 1
        mem += len(e['name']) + 1
    return strings


def resolve(runs):
    """Для кожного прогону шукає базову адресу, за якою посилання влучають на початки рядків."""
    lay = [layout(r) for r in runs]
    bases = [None] * len(runs)
    for i, run in enumerate(runs):
        votes = collections.Counter()
        refs = [memoff(e['vp']) for e in run if is_ref(e['vp'])]
        for m in refs:
            for r in lay[i]:
                b = m - r
                if b >= 0:
                    votes[b] += 1
        if votes:
            b, n = votes.most_common(1)[0]
            if n >= 2 or len(refs) == 1:
                bases[i] = b
    table = {}
    for i, b in enumerate(bases):
        if b is not None:
            for r, s in lay[i].items():
                table[b + r] = s
    unresolved = 0
    for run in runs:
        for e in run:
            if is_ref(e['vp']):
                v = table.get(memoff(e['vp']))
                if v is None:
                    unresolved += 1
                e['value'] = v
    return unresolved


def zone_strings(path):
    data = pathlib.Path(path).read_bytes()
    raw = zlib.decompress(data[12:])
    with contextlib.redirect_stdout(io.StringIO()):
        _, _, assets, _ = header(raw)
    expected = [n for t, n in ((t, len(list(g))) for t, g in itertools.groupby(assets)) if t == 23]
    runs = runs_of(raw)
    unresolved = resolve(runs)
    return runs, expected, unresolved


if __name__ == '__main__':
    runs, expected, unresolved = zone_strings(sys.argv[1])
    print('expected runs', expected, 'sum', sum(expected))
    print('found runs', [len(r) for r in runs], 'sum', sum(len(r) for r in runs), 'unresolved', unresolved)
