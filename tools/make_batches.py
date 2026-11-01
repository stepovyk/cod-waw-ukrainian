"""Ділить усі рядки на тематичні партії для перекладу: data/batches/NN.json.

Ключ – назва рядка; якщо в різних архівах однакова назва має різний текст, ключ – «НАЗВА@архів».
"""
import json, pathlib, collections

DATA = pathlib.Path(__file__).parent.parent / 'data'
LIMIT = 24000  # символів англійського тексту на партію


def entries():
    zones = json.loads((DATA / 'strings_en.json').read_text(encoding='utf-8'))
    by_name = collections.defaultdict(dict)  # назва -> текст -> [архіви]
    for zone, d in zones.items():
        for name, value in d.items():
            by_name[name].setdefault(value, []).append(zone)
    out = {}
    for name, variants in by_name.items():
        if len(variants) == 1:
            (value, zs), = variants.items()
            out[name] = {'en': value, 'zones': zs}
        else:
            for value, zs in variants.items():
                for z in zs:
                    out[f'{name}@{z}'] = {'en': value, 'zones': [z]}
    return out


def group(key):
    name = key.split('@')[0]
    head = name.split('_')[0]
    if head in ('SUBTITLE', 'VIDSUBTITLES'):
        return 'dialog'
    if head in ('CREDITS',):
        return 'credits'
    if head in ('CHALLENGE', 'RANK', 'PERKS', 'CLASS', 'MP', 'MPUI', 'QUICKMESSAGE'):
        return 'mp'
    if head in ('ZOMBIE', 'PATCH'):
        return 'zombie'
    if head in ('MENU', 'PLATFORM', 'EXE', 'KEY', 'XBOXLIVE', 'MESSAGEBOX', 'CLANS', 'GAME', 'CGAME', 'DEBUG', 'NULL'):
        return 'ui'
    return 'game'  # місії, цілі, зброя, цитати, автозбереження, скрипти


def main():
    items = entries()
    groups = collections.defaultdict(list)
    for key in sorted(items):
        groups[group(key)].append(key)
    out_dir = DATA / 'batches'
    out_dir.mkdir(exist_ok=True)
    for old in out_dir.glob('*.json'):
        old.unlink()
    n = 0
    summary = []
    for g in ('ui', 'game', 'dialog', 'zombie', 'mp', 'credits'):
        batch, size = {}, 0
        for key in groups[g]:
            batch[key] = items[key]
            size += len(items[key]['en'])
            if size >= LIMIT:
                n += 1
                (out_dir / f'{n:02d}-{g}.json').write_text(json.dumps(batch, ensure_ascii=False, indent=1), encoding='utf-8')
                summary.append((f'{n:02d}-{g}', len(batch), size))
                batch, size = {}, 0
        if batch:
            n += 1
            (out_dir / f'{n:02d}-{g}.json').write_text(json.dumps(batch, ensure_ascii=False, indent=1), encoding='utf-8')
            summary.append((f'{n:02d}-{g}', len(batch), size))
    for s in summary:
        print(*s)
    print('ключів усього:', len(items))


if __name__ == '__main__':
    main()
