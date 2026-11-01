"""Р”РёР·Р°СЃРµРјР±Р»СЋРІР°РЅРЅСЏ CoDWaW.exe: Р·РЅР°Р№С‚Рё С„СѓРЅРєС†С–С—, С‰Рѕ РїРѕСЃРёР»Р°СЋС‚СЊСЃСЏ РЅР° СЂСЏРґРѕРє, С– РїРѕРєР°Р·Р°С‚Рё РєРѕРґ."""
import sys, pathlib, struct
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / '.deps'))
import pefile, capstone

import os
EXE = os.environ.get('RE_EXE', r'C:\FOLDER\Games\Call-of-Duty-World-at-War-AnkerGames\CoDWaW.exe')
pe = pefile.PE(EXE)
base = pe.OPTIONAL_HEADER.ImageBase
data = open(EXE, 'rb').read()
text = next(s for s in pe.sections if s.Name.startswith(b'.text'))
tva = base + text.VirtualAddress
tcode = text.get_data()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.skipdata = True


def off2va(off):
    for s in pe.sections:
        if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData:
            return base + s.VirtualAddress + off - s.PointerToRawData


def str_va(s):
    off = data.find(s.encode() + b'\0')
    return off2va(off)


def xrefs(va):
    needle = struct.pack('<I', va)
    out, i = [], 0
    while (i := tcode.find(needle, i)) != -1:
        out.append(tva + i)
        i += 1
    return out


def func_start(va):
    """РќР°Р·Р°Рґ РґРѕ С‚РёРїРѕРІРѕРіРѕ РїСЂРѕР»РѕРіСѓ/РІРёСЂС–РІРЅСЋРІР°РЅРЅСЏ CC/90."""
    i = va - tva
    while i > 0:
        if tcode[i - 1] in (0xCC, 0x90, 0xC3) and tcode[i] in (0x55, 0x83, 0x81, 0x53, 0x56, 0x57, 0x8B, 0x6A, 0xA1, 0x51):
            if tcode[i - 1] != 0xC3 or tcode[i - 2] in (0xCC, 0x90):
                return tva + i
        i -= 1
    return tva


def dis(start, n=200):
    code = tcode[start - tva:start - tva + n * 8]
    lines = []
    for ins in md.disasm(code, start):
        lines.append(f'{ins.address:08x}  {ins.mnemonic:6} {ins.op_str}')
        if len(lines) >= n:
            break
    return '\n'.join(lines)


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'str':
        va = str_va(sys.argv[2].encode().decode('unicode_escape'))
        print('string va', hex(va))
        for x in xrefs(va):
            fs = func_start(x)
            print('xref', hex(x), 'func~', hex(fs))
    elif mode == 'dis':
        print(dis(int(sys.argv[2], 16), int(sys.argv[3]) if len(sys.argv) > 3 else 120))
    elif mode == 'calls':  # С…С‚Рѕ РІРёРєР»РёРєР°С” Р°РґСЂРµСЃСѓ
        target = int(sys.argv[2], 16)
        for ins in md.disasm(tcode, tva):
            if ins.mnemonic in ('call', 'jmp') and ins.op_str == hex(target):
                print(hex(ins.address))
