"""Збирає fastfile (T4, PC, непідписаний) лише з LocalizeEntry."""
import struct, zlib, pathlib

MAGIC = b'IWffu100'
VERSION = 0x183
ASSET_LOCALIZE = 23
PTR_INLINE = 0xFFFFFFFF


def build_localize_zone(entries):
    """entries: список (name: str, value: bytes) – value вже в ігровому кодуванні."""
    body = bytearray()
    body += struct.pack('<IIiI', 0, 0, len(entries), PTR_INLINE)  # scriptStrings: count, ptr; assets: count, ptr
    for _ in entries:
        body += struct.pack('<iI', ASSET_LOCALIZE, PTR_INLINE)
    for name, value in entries:
        body += struct.pack('<II', PTR_INLINE, PTR_INLINE)
        body += value + b'\0' + name.encode('ascii') + b'\0'
    size = len(body)
    blocks = [size, 0, 0, 0, size, 0, 0]
    raw = struct.pack('<II7I', size, 0, *blocks) + body
    return MAGIC + struct.pack('<I', VERSION) + zlib.compress(bytes(raw), 9)


def write(path, entries):
    pathlib.Path(path).write_bytes(build_localize_zone(entries))
