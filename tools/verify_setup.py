"""Перевірка інсталятора на справжній грі: стан файлів після /install або /remove.
python tools/verify_setup.py installed|original"""
import sys, zlib, hashlib, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from paths import GAME, BACKUP, REPLACED, ADDED, built

state = sys.argv[1]


def content(path):
    data = path.read_bytes()
    return zlib.decompress(data[12:]) if path.suffix == '.ff' else data


bad = 0
for rel in REPLACED:
    want = content(built(rel) if state == 'installed' else BACKUP / rel)
    got = content(GAME / rel)
    ok = hashlib.sha256(want).digest() == hashlib.sha256(got).digest()
    bad += not ok
    print('ok ' if ok else 'НЕ', rel)
for rel in ADDED:
    exists = (GAME / rel).exists()
    ok = (exists and (GAME / rel).read_bytes() == built(rel).read_bytes()) if state == 'installed' else not exists
    bad += not ok
    print('ok ' if ok else 'НЕ', rel)
leftover = [p.name for p in GAME.rglob('*.ukr-tmp')] + ([str(GAME / 'ukrainian_backup')] if state == 'original' and (GAME / 'ukrainian_backup').exists() else [])
if leftover:
    bad += 1
    print('НЕ зайве:', leftover)
print('усе збігається' if not bad else f'розбіжностей: {bad}')
sys.exit(1 if bad else 0)
