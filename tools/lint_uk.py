"""Пошук типових огріхів у перекладі: велика літера посеред речення, подвійні пробіли, латиниця в українських словах тощо."""
import json, glob, re, pathlib

ROOT = pathlib.Path(__file__).parent.parent
src, uk = {}, {}
for f in glob.glob(str(ROOT / 'data/batches/*.json')):
    src.update({k: v['en'] for k, v in json.load(open(f, encoding='utf-8')).items()})
for f in glob.glob(str(ROOT / 'data/uk/*.json')):
    uk.update(json.load(open(f, encoding='utf-8')))

CHECKS = {
    'велика У/В посеред речення': re.compile(r'[а-яіїєґ] [УВІЙ] [а-яіїєґ]'),
    'змішані алфавіти в слові': re.compile(r'[а-яіїєґА-ЯІЇЄҐ][A-Za-z]|[A-Za-z][а-яіїєґА-ЯІЇЄҐ]'),
    'пробіл перед розділовим': re.compile(r' [,.!?:;](?!\.)'),
    'подвійне слово': re.compile(r'\b(\w+) \1\b', re.I),
    'англійські слова': re.compile(r'\b(the|and|you|press|to|of|your|enemy)\b'),
}
out = []
for k, t in uk.items():
    en = src[k]
    for name, rx in CHECKS.items():
        m = rx.search(t)
        if m and not rx.search(en):
            out.append(f'[{name}] {k}: {t}   (EN: {en[:80]})')
(ROOT / 'work/lint.txt').write_text('\n'.join(out), encoding='utf-8')
print(len(out))
