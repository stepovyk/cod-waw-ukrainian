"""Власний декодер DXT5 (numpy) – для перевірки."""
import numpy as np


def _565(c):
    r = ((c >> 11) & 31) * 255 // 31
    g = ((c >> 5) & 63) * 255 // 63
    b = (c & 31) * 255 // 31
    return np.stack([r, g, b], -1).astype(np.int32)


def decode_dxt5(buf, w, h):
    bw, bh = w // 4, h // 4
    blk = np.frombuffer(buf[:bw * bh * 16], np.uint8).reshape(bh * bw, 16)
    a0 = blk[:, 0].astype(np.int32)
    a1 = blk[:, 1].astype(np.int32)
    abits = np.zeros(len(blk), np.uint64)
    for i in range(6):
        abits |= blk[:, 2 + i].astype(np.uint64) << np.uint64(8 * i)
    alut = np.zeros((len(blk), 8), np.int32)
    alut[:, 0], alut[:, 1] = a0, a1
    gt = a0 > a1
    for i in range(1, 7):
        alut[:, i + 1] = np.where(gt, ((7 - i) * a0 + i * a1) // 7, 0)
    for i in range(1, 5):
        alut[:, i + 1] = np.where(gt, alut[:, i + 1], ((5 - i) * a0 + i * a1) // 5)
    alut[:, 6] = np.where(gt, alut[:, 6], 0)
    alut[:, 7] = np.where(gt, alut[:, 7], 255)
    c0 = blk[:, 8].astype(np.int32) | (blk[:, 9].astype(np.int32) << 8)
    c1 = blk[:, 10].astype(np.int32) | (blk[:, 11].astype(np.int32) << 8)
    cbits = blk[:, 12].astype(np.uint32) | (blk[:, 13].astype(np.uint32) << 8) | \
        (blk[:, 14].astype(np.uint32) << 16) | (blk[:, 15].astype(np.uint32) << 24)
    p0, p1 = _565(c0), _565(c1)
    clut = np.stack([p0, p1, (2 * p0 + p1) // 3, (p0 + 2 * p1) // 3], 1)
    out = np.zeros((bh * bw, 16, 4), np.uint8)
    idx = np.arange(len(blk))
    for px in range(16):
        ai = ((abits >> np.uint64(3 * px)) & np.uint64(7)).astype(np.int64)
        ci = ((cbits >> np.uint32(2 * px)) & np.uint32(3)).astype(np.int64)
        out[:, px, :3] = clut[idx, ci]
        out[:, px, 3] = alut[idx, ai]
    out = out.reshape(bh, bw, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(h, w, 4)
    return out
