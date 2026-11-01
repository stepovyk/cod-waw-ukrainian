"""Читання/запис IWI v6 (CoD WaW): DXT5/DXT1/ARGB32 <-> RGBA-зображення Pillow."""
import io, struct, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / '.deps'))
from PIL import Image
import numpy as np

FMT_ARGB32, FMT_RGB24, FMT_GA, FMT_A8, FMT_DXT1, FMT_DXT3, FMT_DXT5 = 1, 2, 3, 4, 0xB, 0xC, 0xD
FOURCC = {FMT_DXT1: b'DXT1', FMT_DXT3: b'DXT3', FMT_DXT5: b'DXT5'}


def read(data):
    assert data[:3] == b'IWi' and data[3] == 6, data[:4]
    fmt, flags = data[4], data[5]
    w, h, depth = struct.unpack_from('<HHH', data, 6)
    offsets = struct.unpack_from('<4I', data, 12)
    # мип-рівні йдуть від найменшого до найбільшого; offsets[i] – КІНЕЦЬ рівня i (0 – найбільший)
    top = data[offsets[1]:offsets[0]] if offsets[1] != offsets[0] else data[28:offsets[0]]
    if fmt in FOURCC:
        dds = struct.pack('<4sIIIIIII44sIIII20sI16x', b'DDS ', 124, 0x1007, h, w, len(top), 0, 1, b'\0' * 44,
                          32, 4, struct.unpack('<I', FOURCC[fmt])[0], 0, b'\0' * 20, 0x1000)
        img = Image.open(io.BytesIO(dds + top))
        img.load()
        return img.convert('RGBA'), fmt, flags
    if fmt == FMT_ARGB32:
        a = np.frombuffer(top[:w * h * 4], np.uint8).reshape(h, w, 4)[:, :, [2, 1, 0, 3]]  # BGRA
        return Image.fromarray(a, 'RGBA'), fmt, flags
    raise ValueError(f'формат {fmt}')


def write_argb32(img, flags=0x01):
    """IWI ARGB32 з повним ланцюжком мип-рівнів (без втрат – для шрифтів найкраще)."""
    img = img.convert('RGBA')
    w, h = img.size
    levels = []
    cur = img
    while True:
        a = np.asarray(cur, np.uint8)[:, :, [2, 1, 0, 3]]
        levels.append(a.tobytes())
        if cur.size == (1, 1):
            break
        cur = cur.resize((max(1, cur.size[0] // 2), max(1, cur.size[1] // 2)), Image.LANCZOS)
    header_len = 28
    # порядок у файлі: від найменшого до найбільшого; offsets[i] – кінець рівня i (0 – найбільший)
    body = b''.join(reversed(levels))
    ends, pos = [], header_len
    for lv in reversed(levels):
        pos += len(lv)
        ends.append(pos)
    offs = list(reversed(ends))[:4]
    while len(offs) < 4:
        offs.append(offs[-1])
    return b'IWi' + bytes([6, FMT_ARGB32, flags]) + struct.pack('<HHH', w, h, 1) + struct.pack('<4I', *offs) + body


if __name__ == '__main__':
    img, fmt, flags = read(pathlib.Path(sys.argv[1]).read_bytes())
    print('format', hex(fmt), 'flags', hex(flags), img.size)
    img.save(sys.argv[2])
