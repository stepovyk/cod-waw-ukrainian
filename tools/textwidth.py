"""Ширина рядка в пікселях шрифту гри: англійський оригінал (оригінальний шрифт) проти українського (новий шрифт).
Для підбору коротших варіантів там, де текст не влазить. Використання:
python tools/textwidth.py fonts/normalFont "1/4 Players" "Гравці: 1/4" "Гравці 1/4"
Перший рядок міряється оригінальним шрифтом, решта – новим (work/out)."""
import sys, zlib, re, pathlib
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / '.deps')); sys.path.insert(0, str(ROOT / 'tools'))
from build_fonts import font_tables, read_glyphs
from paths import OUT, original


def widths(raw, font):
    return {g[0]: g[3] for g in read_glyphs(raw, *font_tables(raw)[font][1:])}


def width(text, table):
    text = re.sub(r'\^\d|&&\d|\[\{[^}]*\}\]', '', text)
    return sum(table.get(b, 0) for b in text.encode('cp1251', 'replace'))


if __name__ == '__main__':
    font, en, *uk = sys.argv[1:]
    wo = widths(zlib.decompress(original('zone/english/code_post_gfx.ff').read_bytes()[12:]), font)
    wn = widths(zlib.decompress((OUT / 'code_post_gfx.ff').read_bytes()[12:]), font)
    base = width(en, wo)
    print(f'{base:5d}  100%  {en}')
    for t in uk:
        w = width(t, wn)
        print(f'{w:5d} {round(100 * w / base):4d}%  {t}')
