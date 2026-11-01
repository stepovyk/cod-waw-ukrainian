"""Пакет для гравців WaW-Ukrainian-<версія>.zip:
  WaW-Ukrainian-Setup.cmd – запуск інсталятора;
  WaW-Ukrainian.ps1       – сам інсталятор, звичайний відкритий скрипт PowerShell;
  WaW-Ukrainian.Zone.ps1  – його функції для зон гри (.ff);
  WaW-Ukrainian.dat       – латки до файлів гри (без самих файлів Activision) + власні файли локалізації.
Без exe: свіжозібрану програму без цифрового підпису частина антивірусів помилково вважає шкідником.
Зони окремим файлом з тієї ж причини: евристика Bitdefender чіпляється до читання даних і розпакування в одному скрипті.

WaW-Ukrainian.dat:
  b'WAWUA1' u32 кількість_записів, далі записи:
  u8 тип, u16 довжина шляху, шлях (utf-8, відносно теки гри)
    тип 0 – латка сирого файлу (exe), тип 1 – латка розпакованої зони (.ff):
        u32 кількість латок, далі [u32 зсув, u32 довжина, старі байти, нові байти]
    тип 2 – новий файл (у грі його немає): u32 розмір, дані
    тип 3 – заміна файлу з резервною копією (localization.txt): u32 розмір, дані
    тип 4 – ресурс самого інсталятора (banner.png, icon.png), у гру не ставиться: u32 розмір, дані
Латки зберігають і старі байти: інсталятор перевіряє, що латає саме ту версію гри, а видалення
повертає старі байти назад без резервних копій великих файлів.

python tools/make_release.py   (після tools/build.py і tools/make_art.py)"""
import sys, struct, zlib, pathlib, zipfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from paths import ROOT, REPLACED, ADDED, original, built

REL = ROOT / 'work' / 'release'
SRC = ROOT / 'tools' / 'installer'
VERSION = '1.0.2'
GAP = 16  # латки, ближчі за стільки байтів, зливаються


def diff(a, b):
    assert len(a) == len(b), 'розмір змінився – латка неможлива'
    out, i, n = [], 0, len(a)
    while i < n:
        if a[i] == b[i]:
            i += 1
            continue
        j = i
        last = i
        while j < n and (a[j] != b[j] or j - last < GAP):
            if a[j] != b[j]:
                last = j
            j += 1
        end = last + 1
        out.append((i, a[i:end], b[i:end]))
        i = end
    return out


def unzone(data):
    return data[:12], zlib.decompress(data[12:])


def record(kind, name, body):
    name = name.encode()
    return struct.pack('<BH', kind, len(name)) + name + body


def pack():
    records = []
    for rel in REPLACED:
        orig, new = original(rel).read_bytes(), built(rel).read_bytes()
        if rel.endswith('.exe'):
            patches, kind = diff(orig, new), 0
        elif rel.endswith('.ff'):
            ho, ro = unzone(orig)
            hn, rn = unzone(new)
            assert ho == hn
            patches, kind = diff(ro, rn), 1
        else:
            records.append(record(3, rel, struct.pack('<I', len(new)) + new))
            print(f'заміна   {rel}')
            continue
        body = b''.join(struct.pack('<II', off, len(o)) + o + n for off, o, n in patches)
        records.append(record(kind, rel, struct.pack('<I', len(patches)) + body))
        print(f'латка    {rel}: {len(patches)} місць, {sum(len(o) for _, o, _ in patches)} байтів')
    for rel in ADDED:
        data = built(rel).read_bytes()
        records.append(record(2, rel, struct.pack('<I', len(data)) + data))
        print(f'новий    {rel}: {len(data)} байтів')
    for name in 'banner.png', 'icon.png':
        data = (SRC / name).read_bytes()
        records.append(record(4, name, struct.pack('<I', len(data)) + data))
    return b'WAWUA1' + struct.pack('<I', len(records)) + b''.join(records)


def main():
    REL.mkdir(parents=True, exist_ok=True)
    for old in REL.glob('*'):
        old.unlink()
    (REL / 'WaW-Ukrainian.dat').write_bytes(pack())
    # PowerShell 5 читає скрипт без BOM як ANSI, а cmd любить CRLF
    for name in 'WaW-Ukrainian.ps1', 'WaW-Ukrainian.Zone.ps1':
        script = (SRC / name).read_text(encoding='utf-8-sig').replace('\r\n', '\n')
        (REL / name).write_bytes(script.replace('\n', '\r\n').encode('utf-8-sig'))
    launcher = (SRC / 'WaW-Ukrainian-Setup.cmd').read_text(encoding='ascii').replace('\r\n', '\n')
    (REL / 'WaW-Ukrainian-Setup.cmd').write_bytes(launcher.replace('\n', '\r\n').encode('ascii'))
    readme = (SRC / 'ПРОЧИТАЙ.txt').read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    (REL / 'ПРОЧИТАЙ.txt').write_bytes(readme.replace('\n', '\r\n').encode('utf-8-sig'))
    zpath = REL / f'WaW-Ukrainian-{VERSION}.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in 'WaW-Ukrainian-Setup.cmd', 'WaW-Ukrainian.ps1', 'WaW-Ukrainian.Zone.ps1', 'WaW-Ukrainian.dat', 'ПРОЧИТАЙ.txt':
            z.write(REL / name, name)
    print('готово:', zpath.name, zpath.stat().st_size)


if __name__ == '__main__':
    main()
