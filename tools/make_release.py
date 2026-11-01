"""Пакет для гравців: латки до файлів гри (без самих файлів Activision) + власні файли локалізації,
вшиті в інсталятор WaW-Ukrainian-Setup.exe.

payload.bin:
  b'WAWUA1' u32 кількість_записів, далі записи:
  u8 тип, u16 довжина шляху, шлях (utf-8, відносно теки гри)
    тип 0 – латка сирого файлу (exe), тип 1 – латка розпакованої зони (.ff):
        u32 кількість латок, далі [u32 зсув, u32 довжина, старі байти, нові байти]
    тип 2 – новий файл (у грі його немає): u32 розмір, дані
    тип 3 – заміна файлу з резервною копією (localization.txt): u32 розмір, дані
Латки зберігають і старі байти: інсталятор перевіряє, що латає саме ту версію гри, а видалення
повертає старі байти назад без резервних копій великих файлів.

python tools/make_release.py   (після tools/build.py)"""
import sys, struct, zlib, pathlib, subprocess, shutil, zipfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from paths import ROOT, OUT, REPLACED, ADDED, original, built

REL = ROOT / 'work' / 'release'
VERSION = '1.0'
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


def pack():
    records = []
    for rel in REPLACED:
        orig, new = original(rel).read_bytes(), built(rel).read_bytes()
        name = rel.encode()
        if rel.endswith('.exe'):
            patches, kind = diff(orig, new), 0
        elif rel.endswith('.ff'):
            ho, ro = unzone(orig)
            hn, rn = unzone(new)
            assert ho == hn
            patches, kind = diff(ro, rn), 1
        else:
            records.append(struct.pack('<BH', 3, len(name)) + name + struct.pack('<I', len(new)) + new)
            print(f'заміна   {rel}')
            continue
        body = b''.join(struct.pack('<II', off, len(o)) + o + n for off, o, n in patches)
        records.append(struct.pack('<BH', kind, len(name)) + name + struct.pack('<I', len(patches)) + body)
        print(f'латка    {rel}: {len(patches)} місць, {sum(len(o) for _, o, _ in patches)} байтів')
    for rel in ADDED:
        data, name = built(rel).read_bytes(), rel.encode()
        records.append(struct.pack('<BH', 2, len(name)) + name + struct.pack('<I', len(data)) + data)
        print(f'новий    {rel}: {len(data)} байтів')
    return b'WAWUA1' + struct.pack('<I', len(records)) + b''.join(records)


def main():
    REL.mkdir(parents=True, exist_ok=True)
    payload = REL / 'payload.bin'
    payload.write_bytes(pack())
    print('payload:', payload.stat().st_size)
    csc = pathlib.Path(r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe')
    src = ROOT / 'tools' / 'installer'
    exe = REL / 'WaW-Ukrainian-Setup.exe'
    cmd = [str(csc), '/nologo', '/codepage:65001', '/target:winexe', '/optimize+', '/platform:anycpu', f'/out:{exe}',
           f'/win32manifest:{src / "app.manifest"}', f'/win32icon:{src / "icon.ico"}',
           f'/resource:{payload},payload.bin', f'/resource:{src / "banner.png"},banner.png',
           '/r:System.Windows.Forms.dll', '/r:System.Drawing.dll', str(src / 'Installer.cs')]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='cp866', errors='replace')
    if r.returncode:
        sys.exit(r.stdout + r.stderr)
    zpath = REL / f'WaW-Ukrainian-{VERSION}.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(exe, exe.name)
        z.write(src / 'ПРОЧИТАЙ.txt', 'ПРОЧИТАЙ.txt')
    print('готово:', exe.stat().st_size, zpath.name, zpath.stat().st_size)


if __name__ == '__main__':
    main()
