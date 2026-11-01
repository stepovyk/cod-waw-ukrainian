"""Латки CoDWaW.exe / CoDWaWmp.exe (версія 1.7) для української локалізації.

1. Пріоритет архіву з українськими рядками. Рушій лишає новий рядок, лише коли пріоритет (allocFlags)
   нового архіву >= пріоритету старого. Прапор мусить бути одним бітом (він же визначає розподіл пам'яті),
   тож беремо 0x200 – як у штатного patch – і вантажимо український архів останнім.
   - CoDWaW.exe: стартовий архів localized_common (у англійській версії відсутній) отримує 0x200 замість 1
     і міняється місцями з patch у черзі завантаження.
   - CoDWaWmp.exe: вільного слота нема, тож вставка в кінці секції коду додає до стартового списку
     архів localized_ukrainian_mp (після patch_mp; мод-архіви працюють як раніше).
2. Пул рядків (LocalizeEntry) розширено з 10 240 до 24 576 записів: оригінальні рядки лишаються в пам'яті
   як «перекриті», тож без цього пул переповнюється. Новий пул – у доданій порожній секції .ukr.
Кожна латка перевіряє оригінальні байти; повторний запуск нічого не змінює.
"""
import sys, struct, pathlib

PRIORITY = 0x200
POOL_COUNT = 24576
SECTION = b'.ukr\0\0\0\0'
SECTION_SIZE = 0x50000  # пул: 4 + 24576*8 = 196612 байт (до 0x30004); черга g_copyInfo – 0x40000..0x50000
ASSET_LOCALIZE = 23

COPYINFO_OFFSET, COPYINFO_COUNT = 0x40000, 0x4000  # черга відкладених перекриттів: 3072 -> 16384

CONFIG = {
    'codwaw.exe': {'pools': 0x8DC828, 'sizes': 0x8DC5D0, 'old_pool': 0xBF0090,
                   'copyinfo': 0xAD1DD8, 'copyinfo_refs': (0x48D665, 0x48D750, 0x48E613), 'copyinfo_cmp': 0x48D73C},
    'codwawmp.exe': {'pools': 0x8D0958, 'sizes': 0x8D06E8, 'old_pool': 0x1401FE8,
                     'copyinfo': 0x12E3D30, 'copyinfo_refs': (0x4B9BE5, 0x4BA85A, 0x4BABA3), 'copyinfo_cmp': 0x4BA846},
}


class PE:
    def __init__(self, data):
        self.d = data
        self.pe = struct.unpack_from('<I', data, 0x3C)[0]
        self.nsec_off = self.pe + 6
        self.opt = self.pe + 24
        self.base = struct.unpack_from('<I', data, self.opt + 28)[0]
        self.sec_table = self.opt + struct.unpack_from('<H', data, self.pe + 20)[0]

    def sections(self):
        n = struct.unpack_from('<H', self.d, self.nsec_off)[0]
        out = []
        for i in range(n):
            off = self.sec_table + i * 40
            vsize, vaddr, rsize, raddr = struct.unpack_from('<IIII', self.d, off + 8)
            out.append({'name': bytes(self.d[off:off + 8]), 'hdr': off, 'vsize': vsize, 'vaddr': vaddr,
                        'rsize': rsize, 'raddr': raddr})
        return out

    def off(self, va):
        for s in self.sections():
            if s['vaddr'] <= va - self.base < s['vaddr'] + s['rsize']:
                return va - self.base - s['vaddr'] + s['raddr']
        raise ValueError(hex(va))

    def add_bss_section(self, name, size):
        """Порожня (неініціалізована) секція RW у кінці образу. Повертає її VA."""
        for s in self.sections():
            if s['name'] == name:
                return self.base + s['vaddr']
        secs = self.sections()
        hdr = self.sec_table + len(secs) * 40
        first_raw = min(s['raddr'] for s in secs if s['raddr'])
        if hdr + 40 > first_raw or any(self.d[hdr:hdr + 40]):
            raise SystemExit('нема місця для заголовка секції')
        align = struct.unpack_from('<I', self.d, self.opt + 32)[0]
        end = max(s['vaddr'] + max(s['vsize'], s['rsize']) for s in secs)
        vaddr = (end + align - 1) & ~(align - 1)
        struct.pack_into('<8sIIIIIIHHI', self.d, hdr, name, size, vaddr, 0, 0, 0, 0, 0, 0, 0xC0000080)
        struct.pack_into('<H', self.d, self.nsec_off, len(secs) + 1)
        struct.pack_into('<I', self.d, self.opt + 56, vaddr + ((size + align - 1) & ~(align - 1)))  # SizeOfImage
        return self.base + vaddr


def patch(pe, va, old, new):
    off = pe.off(va)
    cur = bytes(pe.d[off:off + len(old)])
    if cur == new:
        return
    if cur != old:
        raise SystemExit(f'несподівані байти за {hex(va)}: {cur.hex()} (очікувано {old.hex()})')
    pe.d[off:off + len(old)] = new


def priority_sp(pe):
    # mov dword ptr [esp+ecx+8], 1 – allocFlags слота localized_common у списку стартових архівів
    patch(pe, 0x6D56CE, bytes.fromhex('C7440C0801000000'), bytes.fromhex('C7440C08') + struct.pack('<I', PRIORITY))
    # Порядок: ui, localized_common, common, patch. Міняємо місцями назви patch і localized_common
    # у таблиці стартових архівів (обидва слоти тепер з пріоритетом 0x200), тож український архів
    # вантажиться останнім і за рівного пріоритету перекриває й patch.
    for va, imm in ((0x644ED9, 0x2C), (0x644FA0, 0x24)):   # mov [esp+imm], "patch"
        patch(pe, va, bytes([0xC7, 0x44, 0x24, imm]) + struct.pack('<I', 0x88A558),
              bytes([0xC7, 0x44, 0x24, imm]) + struct.pack('<I', 0x88A560))
    for va, imm in ((0x644EF9, 0x3C), (0x644FC0, 0x34)):   # mov [esp+imm], "localized_common"
        patch(pe, va, bytes([0xC7, 0x44, 0x24, imm]) + struct.pack('<I', 0x88A560),
              bytes([0xC7, 0x44, 0x24, imm]) + struct.pack('<I', 0x88A558))


def priority_mp(pe):
    text = next(s for s in pe.sections() if s['name'].startswith(b'.text'))
    cave = 0x7E5560  # вільне місце після коду (оригінальний VirtualSize .text = 0x3E454F)
    assert cave + 80 <= pe.base + text['vaddr'] + text['rsize']
    hook, ret = 0x6AAC81, 0x6AAC87
    code = bytearray()
    code += bytes.fromhex('8D0C40')        # lea ecx, [eax+eax*2]
    code += bytes.fromhex('C1E102')        # shl ecx, 2         ; ecx = індекс * sizeof(XZoneInfo)
    code += bytes.fromhex('C7440C04') + struct.pack('<I', cave + 48)  # name
    code += bytes.fromhex('C7440C08') + struct.pack('<I', PRIORITY)   # allocFlags
    code += bytes.fromhex('C7440C0C') + struct.pack('<I', 0)          # freeFlags
    code += bytes.fromhex('40')            # inc eax
    code += bytes.fromhex('56508D44240C')  # push esi; push eax; lea eax,[esp+0xC] – витерті інструкції
    code += b'\xE9' + struct.pack('<i', ret - (cave + len(code) + 5))
    code += b'\xCC' * (48 - len(code)) + b'localized_ukrainian_mp\0'
    patch(pe, cave, bytes(len(code)), bytes(code))
    patch(pe, hook, bytes.fromhex('56508D44240C'), b'\xE9' + struct.pack('<i', cave - (hook + 5)) + b'\x90')
    need = cave + len(code) - pe.base - text['vaddr']
    if need > text['vsize']:
        struct.pack_into('<I', pe.d, text['hdr'] + 8, need)


def enlarge_pool(pe, cfg):
    va = pe.add_bss_section(SECTION, SECTION_SIZE)
    patch(pe, cfg['pools'] + 4 * ASSET_LOCALIZE, struct.pack('<I', cfg['old_pool']), struct.pack('<I', va))
    patch(pe, cfg['sizes'] + 4 * ASSET_LOCALIZE, struct.pack('<I', 10240), struct.pack('<I', POOL_COUNT))
    # g_copyInfo: під час завантаження пакета архівів перекриття стають у чергу на 3072 місця;
    # український архів перекриває ~2700 рядків меню, а ui – ще ~2200, тож черга переповнюється
    new = struct.pack('<I', va + COPYINFO_OFFSET)
    for ref in cfg['copyinfo_refs']:
        patch(pe, ref, struct.pack('<I', cfg['copyinfo']), new)
    patch(pe, cfg['copyinfo_cmp'], bytes.fromhex('3D000C0000'), b'\x3D' + struct.pack('<I', COPYINFO_COUNT))


def apply(path):
    path = pathlib.Path(path)
    key = path.name.lower()
    pe = PE(bytearray(path.read_bytes()))
    (priority_sp if key == 'codwaw.exe' else priority_mp)(pe)
    enlarge_pool(pe, CONFIG[key])
    path.write_bytes(pe.d)


if __name__ == '__main__':
    for p in sys.argv[1:]:
        apply(p)
        print('ok', p)
