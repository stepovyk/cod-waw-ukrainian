"""Однаковий англійський текст (поза діалогами) -> різні переклади: звіт у work/consistency.txt."""
import json, glob, collections, pathlib

ROOT = pathlib.Path(__file__).parent.parent
src, uk = {}, {}
for f in sorted(glob.glob(str(ROOT / 'data/batches/*.json'))):
    for k, v in json.load(open(f, encoding='utf-8')).items():
        src[k] = v['en']
for f in sorted(glob.glob(str(ROOT / 'data/uk/*.json'))):
    uk.update(json.load(open(f, encoding='utf-8')))
by = collections.defaultdict(lambda: collections.defaultdict(list))
for k, en in src.items():
    if not k.startswith('SUBTITLE_'):
        by[en][uk[k]].append(k)
out = []
for en, variants in sorted(by.items(), key=lambda x: len(x[0])):
    if len(variants) > 1:
        out.append(f'EN: {en}')
        for t, keys in variants.items():
            out.append(f'   {t}   <- {", ".join(keys[:4])}')
(ROOT / 'work/consistency.txt').write_text('\n'.join(out), encoding='utf-8')
print(sum(1 for l in out if l.startswith('EN:')))
