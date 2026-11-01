"""Збирає архіви з українськими рядками.

- localized_common.ff – кампанія, кооператив, зомбі, меню, титри (CoDWaW.exe);
- localized_ukrainian_mp.ff – мультиплеєр (CoDWaWmp.exe);
- рядки з однаковою назвою, але різним текстом на різних зомбі-картах, правляться на місці
  в архівах цих карт тим самим числом байтів (симетричне доповнення пробілами), тож структура не зсувається.
"""
import json, glob, struct, zlib, pathlib, sys, collections

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import ffwrite, locwalk

from paths import OUT, original


def is_mp(zone):
    return zone in ('localized_code_post_gfx_mp', 'localized_common_mp') or zone.startswith('mp_')


def encode(text, key):
    try:
        return text.encode('cp1251')
    except UnicodeEncodeError as e:
        raise SystemExit(f'{key}: символ поза шрифтом: {e}')


def load():
    src, uk = {}, {}
    for f in sorted(glob.glob(str(ROOT / 'data/batches/*.json'))):
        src.update(json.load(open(f, encoding='utf-8')))
    for f in sorted(glob.glob(str(ROOT / 'data/uk/*.json'))):
        uk.update(json.load(open(f, encoding='utf-8')))
    missing = set(src) - set(uk)
    if missing:
        raise SystemExit(f'бракує перекладів: {sorted(missing)[:10]}')
    return src, uk


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    src, uk = load()
    sp, mp = {}, {}
    per_zone = collections.defaultdict(dict)  # архів -> англ. текст -> укр. (для правок на місці)
    for key, item in src.items():
        name = key.split('@')[0]
        value = encode(uk[key], key)
        zones = item['zones']
        if '@' in key and not any(is_mp(z) for z in zones) and any('zombie' in z for z in zones):
            # рядок, що різниться між зомбі-картами: лише на місці
            for z in zones:
                per_zone[z][item['en']] = value
            continue
        if any(not is_mp(z) for z in zones):
            sp[name] = value
        if any(is_mp(z) for z in zones):
            mp[name] = value
    # назви, що мають варіанти лише в межах зомбі-карт, не повинні потрапити до загального архіву
    zombie_only = {k.split('@')[0] for k, it in src.items() if '@' in k and any('zombie' in z for z in it['zones'])}
    for n in zombie_only:
        sp.pop(n, None)

    ffwrite.write(OUT / 'localized_common.ff', sorted(sp.items()))
    ffwrite.write(OUT / 'localized_ukrainian_mp.ff', sorted(mp.items()))
    print('кампанія/зомбі:', len(sp), 'мультиплеєр:', len(mp))

    # системні вікна Windows (MessageBoxA – кодова сторінка 1251), закінчення рядків – як в оригіналі
    eol = b'\r\n' if b'\r\n' in original('localization.txt').read_bytes() else b'\n'
    text = (ROOT / 'data/localization_uk.txt').read_text(encoding='utf-8').replace('\r\n', '\n')
    (OUT / 'localization.txt').write_bytes(encode(text, 'localization.txt').replace(b'\n', eol))

    for zone, table in per_zone.items():
        data = original(f'zone/english/{zone}.ff').read_bytes()
        raw = bytearray(zlib.decompress(data[12:]))
        done = 0
        for run in locwalk.runs_of(bytes(raw)):
            for e in run:
                if e['vp'] not in (locwalk.INLINE, locwalk.SAVE) or e['value'] is None:
                    continue
                en = e['value'].decode('latin1')
                if en not in table:
                    continue
                new = table[en]
                old = e['value']
                if len(new) > len(old):
                    raise SystemExit(f'{zone}: «{new.decode("cp1251")}» довший за оригінал ({len(new)} > {len(old)})')
                pad = len(old) - len(new)
                new = b' ' * (pad // 2) + new + b' ' * (pad - pad // 2)
                p = e['pos'] + 8
                assert raw[p:p + len(old)] == old
                raw[p:p + len(old)] = new
                done += 1
        if done < len(table):
            raise SystemExit(f'{zone}: замінено {done} із {len(table)}')
        (OUT / f'{zone}.ff').write_bytes(data[:12] + zlib.compress(bytes(raw), 9))
        print(f'{zone}: замінено на місці {done}')


if __name__ == '__main__':
    main()
