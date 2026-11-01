"""Повне збирання локалізації в work/out з оригінальних файлів гри: шрифти, рядки, пропатчені exe."""
import sys, shutil, pathlib, subprocess
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from paths import OUT, REPLACED, ADDED, original, built
import exepatch

TOOLS = ROOT / 'tools'


def run(script, *args):
    print(f'== {script} {" ".join(args)}')
    subprocess.run([sys.executable, str(TOOLS / script), *args], check=True, cwd=ROOT)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in sorted((ROOT / 'data' / 'uk').glob('*.json')):
        run('check_batch.py', f.stem.split('-')[0])
    run('build_fonts.py')
    run('build_strings.py')
    run('build_menus.py')
    for exe in ('CoDWaW.exe', 'CoDWaWmp.exe'):
        shutil.copyfile(original(exe), OUT / exe)
        exepatch.apply(OUT / exe)
        print('== exe', exe)
    missing = [r for r in REPLACED + ADDED if not built(r).exists()]
    if missing:
        sys.exit('не зібрано: ' + ', '.join(missing))
    print('готово:', OUT)


if __name__ == '__main__':
    main()
