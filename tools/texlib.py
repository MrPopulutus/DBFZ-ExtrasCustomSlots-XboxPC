import struct
def parse_mips(uexp):
    """Return (sx, sy, fmt, mips) where each mip = dict(sx, sy, size, inline_pos or bulk_off, hdr_pos)."""
    i = uexp.find(b'PF_')
    n = struct.unpack_from('<i', uexp, i - 4)[0]
    fmt = uexp[i:i + n - 1].decode()
    sx, sy = struct.unpack_from('<ii', uexp, i - 16)
    p = i + n
    first, nmips = struct.unpack_from('<ii', uexp, p); p += 8
    mips = []
    for _ in range(nmips):
        cooked, flags, cnt, size, off = struct.unpack_from('<IIiiq', uexp, p)
        hdr = p; p += 24
        m = dict(flags=flags, size=size, off=off, hdr=hdr)
        if flags & 0x100:  # separate .ubulk
            m['where'] = 'ubulk'
        else:
            m['where'] = 'inline'; m['pos'] = p; p += size
        m['sx'], m['sy'] = struct.unpack_from('<ii', uexp, p); p += 8
        mips.append(m)
    return sx, sy, fmt, mips
