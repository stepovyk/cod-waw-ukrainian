"""Витягує всі LocalizeEntry з усіх fastfile гри: data/strings_en.json (зона -> назва -> текст)."""
import json, pathlib, sys, collections

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from locwalk import zone_strings

from paths import GAME, original
DATA = pathlib.Path(__file__).parent.parent / 'data'


def main():
    DATA.mkdir(exist_ok=True)
    zones = {}
    for ff in sorted((GAME / 'zone' / 'english').glob('*.ff')):
        if ff.stem in ('localized_common', 'localized_ukrainian_mp'):
            continue  # українські архіви
        runs, expected, _ = zone_strings(original(f'zone/english/{ff.name}'))
        if not expected:
            continue
        picked = sorted(runs, key=len, reverse=True)[:len(expected)]
        if sorted(map(len, picked)) != sorted(expected):
            raise SystemExit(f'{ff.stem}: очікувано {expected}, знайдено {[len(r) for r in runs]}')
        picked.sort(key=lambda r: r[0]['pos'])
        entries = {}
        for run in picked:
            for e in run:
                if e['value'] is None and e['vp'] != 0:
                    raise SystemExit(f"{ff.stem}: нерозв'язане посилання {e['name']}")
                entries[e['name']] = (e['value'] or b'').decode('latin1')
        zones[ff.stem] = entries
        print(f'{ff.stem}: {len(entries)}')
    (DATA / 'strings_en.json').write_text(json.dumps(zones, ensure_ascii=False, indent=1), encoding='utf-8')

    merged, conflicts = {}, collections.defaultdict(set)
    for zone, entries in zones.items():
        for k, v in entries.items():
            if k in merged and merged[k] != v:
                conflicts[k].update({merged[k], v})
            merged.setdefault(k, v)
    print('усього унікальних назв:', len(merged), 'конфліктів:', len(conflicts))
    for k in list(conflicts)[:20]:
        print(' ', k, [c[:50] for c in conflicts[k]])


if __name__ == '__main__':
    main()
