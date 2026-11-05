"""Скріншоти для сторінок мода (docs/images): з work/shots у work/art.
Обкладинка (docs/images/cover.jpg), банер і значок інсталятора (tools/installer/banner.png, icon.png) – з фірмового
набору Stepovyk, тут не малюються.
python tools/make_art.py"""
import sys, pathlib
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / '.deps'))
from PIL import Image

SHOTS = ROOT / 'work' / 'shots'
ART = ROOT / 'work' / 'art'


def main():
    ART.mkdir(parents=True, exist_ok=True)
    shots = ['01-menu', 'mission-44', 'mission-52', '04-missions', '02-settings', '05-zombies', '06-mp-team', '07-mp-class']
    for i, name in enumerate(shots, 1):
        Image.open(SHOTS / f'{name}.png').convert('RGB').save(ART / f'screen-{i:02d}.jpg', quality=92)
    full = Image.open(SHOTS / 'dialog_full.png').convert('RGB')
    full.crop((760, 425, 1160, 650)).save(ART / 'screen-09-windows.png')
    print('готово:', ART)


if __name__ == '__main__':
    main()
