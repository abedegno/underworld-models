"""Encodes pixels in UW1's run-length sprite format, so tests can build sprite files without the game's."""
import numpy as np


def pack(nibbles, bits):
    out, acc, n = bytearray(), 0, 0
    for v in nibbles:
        acc = (acc << bits) | int(v)
        n += bits
        while n >= 8:
            n -= 8
            out.append((acc >> n) & 0xFF)
    if n:
        out.append((acc << (8 - n)) & 0xFF)
    return bytes(out)


def encode_rle(pixels, bits=4):
    """Returns (bytes, nibble count): repeat records for runs of three or more equal pixels, run records otherwise,
    each count at most 15 so it fits one nibble."""
    p = [int(x) for x in np.asarray(pixels).ravel()]
    nib, i = [], 0
    while i < len(p):
        same = 1
        while i + same < len(p) and p[i + same] == p[i] and same < 15:
            same += 1
        if same >= 3:
            nib += [same, p[i]]   # a repeat record
            i += same
        else:
            nib.append(1)   # no repeat: a run record follows
        if i >= len(p):
            break
        j = i
        while j < len(p) and j - i < 15:
            if j + 2 < len(p) and p[j] == p[j + 1] == p[j + 2] and j > i:
                break
            j += 1
        nib += [j - i] + p[i:j]   # a run record
        i = j
    return pack(nib, bits), len(nib)
