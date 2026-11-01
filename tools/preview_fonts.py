"""Превʼю: текст складається з гліфів нового атласу так само, як у грі (масштаб SCALE, білий на темному)."""
import sys, zlib, pathlib
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / '.deps'))
sys.path.insert(0, str(ROOT / 'tools'))
from PIL import Image
from build_fonts import font_tables, read_glyphs, GAMEFONTS

TEXT = sys.argv[1] if len(sys.argv) > 1 else 'КАМПАНІЯ  Зброя MP40: «Ґудзик» їжак, Єва, № 5 - Опції'
SCALE = int(sys.argv[2]) if len(sys.argv) > 2 else 2
DEST = sys.argv[3] if len(sys.argv) > 3 else 'work/preview.png'

raw = zlib.decompress((ROOT / 'work/out/code_post_gfx.ff').read_bytes()[12:])
atlas = Image.open(ROOT / 'work/out/gamefonts_pc.png').split()[3]
W, H = atlas.size
tables = font_tables(raw)
rows = []
data = TEXT.encode('cp1251')
for name in GAMEFONTS:
    ph, st, cnt = tables[name]
    g = {x[0]: x for x in read_glyphs(raw, st, cnt)}
    width = (sum(g[b][3] for b in data if b in g) + 20) * SCALE
    im = Image.new('L', (width, (ph + 12) * SCALE), 24)
    x = 10
    for b in data:
        L, x0, y0, dx, pw, phh, s0, t0, s1, t1 = g[b]
        if pw and phh:
            crop = atlas.crop((round(s0 * W), round(t0 * H), round(s1 * W), round(t1 * H)))
            crop = crop.resize((pw * SCALE, phh * SCALE), Image.BILINEAR)
            im.paste(255, ((x + x0) * SCALE, (ph + 6 + y0) * SCALE), crop)
        x += dx
    rows.append(im)
out = Image.new('L', (max(r.size[0] for r in rows), sum(r.size[1] for r in rows)), 24)
y = 0
for r in rows:
    out.paste(r, (0, y)); y += r.size[1]
out.save(ROOT / DEST)
