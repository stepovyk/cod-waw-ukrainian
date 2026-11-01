"""Нові ігрові шрифти з повною кирилицею.

Усі гліфи 7 ігрових шрифтів (латиниця, кирилиця Windows-1251 з і/ї/є/ґ, знаки) малюються наново однією
гарнітурою – Fira Sans Condensed (консоль – Fira Mono), тож текст рівний за товщиною й шириною.
Вужче накреслення обрано тому, що український текст у середньому на чверть довший за англійський.
Атлас gamefonts_pc має подвійну щільність (2 текселі на піксель шрифту) – чіткіше на сучасних роздільностях.
Метрики (висота великих літер, базова лінія, кількість і порядок гліфів) лишаються як в оригіналі, тож
таблиці гліфів у fastfile правляться на місці без зміни структури. Товщина штриха підбирається під
оригінальний шрифт автоматично. Службові коди 1-31 (піктограми) копіюються з оригінального атласу.
"""
import sys, re, struct, zlib, json, pathlib, zipfile
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / '.deps'))
sys.path.insert(0, str(ROOT / 'tools'))
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
import numpy as np
import iwi, dxt
from paths import GAME, OUT, original

GLYPH = struct.Struct('<HbbBBBxffff')
DENSITY = 2   # текселів атласу на піксель шрифту
SS = 4        # надвибірка відносно текселя
PAD = 4       # проміжок між гліфами в атласі (запас для білінійної фільтрації й мип-рівнів)
ATLAS_W = 2048
FONT_DIR = ROOT / 'fonts'
SANS_FAMILY = 'FiraSansCondensed'
SANS = {w: FONT_DIR / f'{SANS_FAMILY}-{w}.ttf' for w in ('Regular', 'Medium', 'SemiBold', 'Bold')}
MONO = {w: FONT_DIR / f'FiraMono-{w}.ttf' for w in ('Regular', 'Medium')}
GAMEFONTS = ['fonts/consoleFont', 'fonts/bigFont', 'fonts/smallFont', 'fonts/boldFont',
             'fonts/normalFont', 'fonts/extraBigFont', 'fonts/objectiveFont']
STEM_REF = 'Ilnmhu'


def load_orig_atlas():
    data = zipfile.ZipFile(GAME / 'main/localized_english_iw00.iwd').read('images/gamefonts_pc.iwi')
    o = struct.unpack_from('<4I', data, 12)
    assert data[4] == iwi.FMT_DXT5 and struct.unpack_from('<HH', data, 6) == (512, 512)
    return np.asarray(Image.fromarray(dxt.decode_dxt5(data[o[1]:o[0]], 512, 512), 'RGBA').split()[3], np.float32) / 255


def font_tables(raw):
    out = {}
    for m in re.finditer(rb'fonts/[A-Za-z]+\x00', raw):
        name = m.group()[:-1].decode()
        n0, ph, cnt, mat, glow, gl = struct.unpack_from('<iiiiii', raw, m.start() - 24)
        if n0 != -1 or gl != -1 or name not in GAMEFONTS:
            continue
        for p in range(m.end(), m.end() + 200000):
            if all(GLYPH.unpack_from(raw, p + i * 24)[0] == 32 + i for i in range(10)):
                out[name] = (ph, p, cnt)
                break
    return out


def read_glyphs(raw, start, cnt):
    return [list(GLYPH.unpack_from(raw, start + i * 24)) for i in range(cnt)]


def orig_bitmap(atlas, g):
    L, x0, y0, dx, pw, ph, s0, t0, s1, t1 = g
    x, y = round(s0 * 512 - 0.5), round(t0 * 512 - 0.5)
    return atlas[y:y + ph, x:x + pw]


def stem(a):
    """Середня сумарна товщина вертикальних штрихів у середній третині гліфа (у пікселях шрифту)."""
    if a.size == 0:
        return 0.0
    rows = a[a.shape[0] // 3: 2 * a.shape[0] // 3]
    return float(rows.sum(1).mean())


class Renderer:
    """Малює гліф у текселях атласу; метрики – у пікселях шрифту."""

    def __init__(self, ttf, cap_px, mono_adv=None):
        t = TTFont(ttf)
        capu = t['OS/2'].sCapHeight / t['head'].unitsPerEm
        self.cmap = t.getBestCmap()
        self.px = cap_px / capu                    # кегль у пікселях шрифту
        self.font = ImageFont.truetype(str(ttf), round(self.px * DENSITY * SS))
        self.mono_adv = mono_adv

    def has(self, ch):
        return ord(ch) in self.cmap

    def advance(self, ch):
        return self.mono_adv or self.font.getlength(ch) / (DENSITY * SS)

    def render(self, ch):
        """(текселі float 2D з розміром кратним DENSITY, x0, y0, pw, ph) – зсуви відносно пера й базової лінії."""
        f, K = self.font, DENSITY * SS
        l, t, r, b = f.getbbox(ch, anchor='ls')
        if r <= l or b <= t:
            return None
        # полотно вирівняне так, що перо й базова лінія лежать на межі пікселя шрифту
        ox = -(l // K) * K + K
        oy = -(t // K) * K + K
        w = ((r + ox + K - 1) // K + 1) * K
        h = ((b + oy + K - 1) // K + 1) * K
        im = Image.new('L', (w, h), 0)
        ImageDraw.Draw(im).text((ox, oy), ch, font=f, fill=255, anchor='ls')
        if self.mono_adv:  # центруємо в моноширинній клітинці
            shift = round(((self.mono_adv * K) - (r - l)) / 2 - l)
            im2 = Image.new('L', (w + K * 2, h), 0)
            im2.paste(im, (shift, 0))
            im, w = im2, w + K * 2
        tex = np.asarray(im.reduce(SS), np.float32) / 255           # текселі
        ys, xs = np.nonzero(tex > 0.01)
        if len(xs) == 0:
            return None
        # обрізаємо до цілих пікселів шрифту
        x1, x2 = (xs.min() // DENSITY) * DENSITY, ((xs.max() // DENSITY) + 1) * DENSITY
        y1, y2 = (ys.min() // DENSITY) * DENSITY, ((ys.max() // DENSITY) + 1) * DENSITY
        pen_x, base_y = ox // SS, oy // SS                               # у текселях
        return (tex[y1:y2, x1:x2], (x1 - pen_x) // DENSITY, (y1 - base_y) // DENSITY,
                (x2 - x1) // DENSITY, (y2 - y1) // DENSITY)


def fit(atlas, glyphs, mono):
    by = {g[0]: g for g in glyphs}
    cap = by[ord('H')][5]
    base = by[ord('H')][2] + by[ord('H')][5]      # базова лінія відносно точки шрифту
    target = np.mean([stem(orig_bitmap(atlas, by[ord(c)])) for c in STEM_REF])
    best = None
    for weight, ttf in (MONO if mono else SANS).items():
        r = Renderer(ttf, cap, by[ord('H')][3] if mono else None)
        s = np.mean([stem(r.render(c)[0]) / DENSITY for c in STEM_REF])  # текселі -> пікселі шрифту
        if best is None or abs(s - target) < best[0]:
            best = (abs(s - target), r, {'font': ttf.stem, 'cap': cap, 'stem_orig': round(float(target), 2),
                                         'stem_new': round(float(s), 2)})
    return best[1], base, best[2]


def pack(items, width):
    """Полиці за висотою. items: [(key, (h, w))] -> ({key: (x, y)}, висота)."""
    pos, x, y, shelf = {}, PAD, PAD, 0
    for key, (h, w) in sorted(items, key=lambda kv: (-kv[1][0], -kv[1][1])):
        if x + w + PAD > width:
            x, y, shelf = PAD, y + shelf + PAD, 0
        pos[key] = (x, y)
        x += w + PAD
        shelf = max(shelf, h)
    return pos, y + shelf + PAD


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    atlas = load_orig_atlas()
    zones = {z: zlib.decompress(original(f'zone/english/{z}.ff').read_bytes()[12:])
             for z in ('code_post_gfx', 'localized_code_post_gfx_mp')}
    tables = {z: font_tables(raw) for z, raw in zones.items()}
    sp = tables['code_post_gfx']
    for z, t in tables.items():
        for name, (ph, st, cnt) in t.items():
            assert read_glyphs(zones[z], st, cnt) == read_glyphs(zones['code_post_gfx'], *sp[name][1:]), z + name

    bitmaps, metrics, report = {}, {}, {}
    for name in GAMEFONTS:
        ph, st, cnt = sp[name]
        glyphs = read_glyphs(zones['code_post_gfx'], st, cnt)
        r, base, info = fit(atlas, glyphs, name == 'fonts/consoleFont')
        report[name] = info
        for g in glyphs:
            code = g[0]
            ch = bytes([code]).decode('cp1251', 'ignore') if code >= 32 and code != 127 else ''
            if ch and r.has(ch):
                adv = round(r.advance(ch))
                res = r.render(ch)
                if res is None:  # пробіл і подібні
                    metrics[(name, code)] = (0, 0, adv, 0, 0)
                    continue
                tex, x0, y0, pw, phh = res
                metrics[(name, code)] = (x0, y0 + base, adv, pw, phh)
            else:  # службові коди: оригінальне зображення, збільшене до нової щільності
                L, x0, y0, dx, pw, phh, *_ = g
                if not pw or not phh:
                    metrics[(name, code)] = (x0, y0, dx, 0, 0)
                    continue
                src = Image.fromarray((orig_bitmap(atlas, g) * 255).astype(np.uint8), 'L')
                tex = np.asarray(src.resize((pw * DENSITY, phh * DENSITY), Image.BICUBIC), np.float32) / 255
                metrics[(name, code)] = (x0, y0, dx, pw, phh)
            bitmaps[(name, code)] = tex

    pos, height = pack([(k, v.shape) for k, v in bitmaps.items()], ATLAS_W)
    H = 1 << (height - 1).bit_length()
    alpha = np.zeros((H, ATLAS_W), np.float32)
    for key, (x, y) in pos.items():
        a = bitmaps[key]
        alpha[y:y + a.shape[0], x:x + a.shape[1]] = a
    a8 = Image.fromarray(np.clip(alpha * 255 + 0.5, 0, 255).astype(np.uint8), 'L')
    white = Image.new('L', a8.size, 255)
    img = Image.merge('RGBA', (white, white, white, a8))
    img.save(OUT / 'gamefonts_pc.png')
    with zipfile.ZipFile(OUT / 'localized_english_iw07.iwd', 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('images/gamefonts_pc.iwi', iwi.write_argb32(img, flags=0xC1))

    for zname, raw in zones.items():
        buf = bytearray(raw)
        for name, (ph, st, cnt) in tables[zname].items():
            for i in range(cnt):
                code = GLYPH.unpack_from(buf, st + i * 24)[0]
                x0, y0, adv, pw, phh = metrics[(name, code)]
                if (name, code) in pos:
                    x, y = pos[(name, code)]
                    uv = (x / ATLAS_W, y / H, (x + pw * DENSITY) / ATLAS_W, (y + phh * DENSITY) / H)
                else:
                    uv = (0.0, 0.0, 0.0, 0.0)
                GLYPH.pack_into(buf, st + i * 24, code, x0, y0, min(adv, 255), pw, phh, *uv)
        (OUT / f'{zname}.ff').write_bytes(b'IWffu100' + struct.pack('<I', 0x183) + zlib.compress(bytes(buf), 9))

    report['_atlas'] = f'{ATLAS_W}x{H}, гліфів {len(bitmaps)}'
    (OUT / 'fonts_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
