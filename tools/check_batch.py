"""Перевіряє переклад партії: усі ключі, коди, символи, переноси. Використання: python tools/check_batch.py 07"""
import json, re, sys, pathlib

ROOT = pathlib.Path(__file__).parent.parent
ALLOWED = set(chr(c) for c in range(0x20, 0x7F)) | set('\n\t') | \
    set('абвгґдеєжзиіїйклмнопрстуфхцчшщьюяАБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ«»№°©®±·§¤¦')
TOKENS = [
    re.compile(r'\^[0-9]'),
    re.compile(r'&&\d'),
    re.compile(r'\[\{[^}]*\}\]'),
    re.compile(r'%[-+ #0]*\d*(?:\.\d+)?[sdifcxXu%]'),
]


def tokens(s, rx):
    return sorted(rx.findall(s))


def check(src, dst):
    errors = []
    missing = [k for k in src if k not in dst]
    extra = [k for k in dst if k not in src]
    if missing:
        errors.append(f'бракує ключів: {len(missing)}, напр. {missing[:5]}')
    if extra:
        errors.append(f'зайві ключі: {extra[:5]}')
    for k, item in src.items():
        if k not in dst:
            continue
        en, uk = item['en'], dst[k]
        if not isinstance(uk, str):
            errors.append(f'{k}: не рядок')
            continue
        bad = sorted(set(ch for ch in uk if ch not in ALLOWED))
        if bad:
            errors.append(f'{k}: недозволені символи {bad}')
        for rx in TOKENS:
            if tokens(en, rx) != tokens(uk, rx):
                errors.append(f'{k}: коди {rx.pattern} {tokens(en, rx)} != {tokens(uk, rx)}')
        if en.count('\n') != uk.count('\n'):
            errors.append(f'{k}: переносів {en.count(chr(10))} != {uk.count(chr(10))}')
        if en.strip() and not uk.strip():
            errors.append(f'{k}: порожній переклад')
        if en.startswith(' ') != uk.startswith(' ') or en.endswith(' ') != uk.endswith(' '):
            errors.append(f'{k}: пробіли на краях не збігаються')
        if re.search('[ыэъёЫЭЪЁ]', uk):
            errors.append(f'{k}: російські літери')
    return errors


def main():
    n = sys.argv[1]
    srcf = next((ROOT / 'data' / 'batches').glob(f'{n}-*.json'))
    dstf = ROOT / 'data' / 'uk' / srcf.name
    src = json.loads(srcf.read_text(encoding='utf-8'))
    dst = json.loads(dstf.read_text(encoding='utf-8'))
    errors = check(src, dst)
    for e in errors:
        print(e)
    print(f'{srcf.name}: {len(dst)}/{len(src)} ключів, помилок: {len(errors)}')
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
