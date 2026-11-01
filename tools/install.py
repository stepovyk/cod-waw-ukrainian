"""Встановлення зібраної локалізації (work/out) у гру. Оригінали змінюваних файлів зберігаються в backup/.

python tools/install.py            – встановити
python tools/install.py --remove   – повернути оригінальну англійську версію
"""
import os, sys, shutil, hashlib, pathlib, subprocess
from paths import GAME, BACKUP, REPLACED, ADDED, built


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def game_running():
    out = subprocess.run(['tasklist', '/fo', 'csv', '/nh'], capture_output=True, text=True).stdout.lower()
    return 'codwaw.exe' in out or 'codwawmp.exe' in out


PROFILES = pathlib.Path(os.environ.get('LOCALAPPDATA', '')) / 'Activision/CoDWaW/players/profiles'
CLASS_EN = 'Custom {}'
CLASS_UK = 'Свій клас {}'


def profile_class_names(to_uk):
    """Назви своїх класів зберігаються в профілі гравця під час його створення (seta customclassN).
    Міняємо лише незмінені стандартні назви, перейменовані гравцем не чіпаємо."""
    src, dst = (CLASS_EN, CLASS_UK) if to_uk else (CLASS_UK, CLASS_EN)
    for cfg in sorted(PROFILES.glob('*/config*.cfg')):
        data = cfg.read_bytes()
        new = data
        for n in range(1, 11):
            old_line = f'seta customclass{n} "{src.format(n)}"'.encode('cp1251')
            new_line = f'seta customclass{n} "{dst.format(n)}"'.encode('cp1251')
            new = new.replace(old_line, new_line)
        if new != data:
            cfg.write_bytes(new)
            print('профіль:', cfg.parent.name, cfg.name)


def install():
    for rel in REPLACED + ADDED:
        if not built(rel).exists():
            sys.exit(f'немає {built(rel)} – спершу python tools/build.py')
    for rel in REPLACED:
        b = BACKUP / rel
        if not b.exists():
            b.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(GAME / rel, b)
            print('резервна копія:', rel)
    for rel in REPLACED + ADDED:
        dst = GAME / rel
        shutil.copyfile(built(rel), dst)
        if sha(dst) != sha(built(rel)):
            sys.exit(f'не вдалося записати {rel}')
        print('встановлено:', rel)
    profile_class_names(True)


def remove():
    for rel in REPLACED:
        b = BACKUP / rel
        if not b.exists():
            sys.exit(f'немає резервної копії {rel} – відновлення неможливе')
    for rel in REPLACED:
        shutil.copyfile(BACKUP / rel, GAME / rel)
        print('відновлено:', rel)
    for rel in ADDED:
        p = GAME / rel
        if p.exists():
            p.unlink()
            print('прибрано:', rel)
    profile_class_names(False)


if __name__ == '__main__':
    if game_running():
        sys.exit('закрий гру й запусти ще раз')
    remove() if '--remove' in sys.argv[1:] else install()
    print('готово')
