"""Шукає інструкції, де операнд містить задане число (адресу), і друкує контекст."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from re_xref import md, tcode, tva

needle = sys.argv[1].lower()
ctx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
hist = []
for ins in md.disasm(tcode, tva):
    hist.append(f'{ins.address:08x}  {ins.mnemonic:6} {ins.op_str}')
    hist = hist[-(ctx + 1):]
    if needle in ins.op_str:
        print('\n'.join(hist))
        print('--')
