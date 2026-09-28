"""Pack newmask/ (current Store layout + 4th row ids 45..58) as DBFZSlotsMask.pak."""
import pathlib, struct, zlib, hashlib
from inspect_pak import read_pak
root = pathlib.Path(__file__).resolve().parent
out = root / 'store-port/paks/DBFZSlotsMask.pak'
files = [('RED/Content/UI/CharaSelect_S3/tex/CharaPositionMask.uasset', root/'newmask/CharaPositionMask.uasset'),
         ('RED/Content/UI/CharaSelect_S3/tex/CharaPositionMask.uexp', root/'newmask/CharaPositionMask.uexp')]
def fstring(s):
    b = s.encode('ascii') + b'\0'; return struct.pack('<i', len(b)) + b
def entry(offset, packed, raw, sha, block):
    return struct.pack('<QQQI', offset, packed, raw, 1) + sha + struct.pack('<I', 1) + struct.pack('<QQ', *block) + struct.pack('<BI', 0, raw)
out.parent.mkdir(parents=True, exist_ok=True)
index = bytearray(fstring('../../../') + struct.pack('<i', len(files)))
with open(out, 'wb') as f:
    for name, src in files:
        data = src.read_bytes(); comp = zlib.compress(data, 9); sha = hashlib.sha1(data).digest()
        off = f.tell(); hl = len(entry(0, 0, 0, sha, (0, 0)))
        blk = (off + hl, off + hl + len(comp))
        f.write(entry(0, len(comp), len(data), sha, blk)); f.write(comp)
        index += fstring(name) + entry(off, len(comp), len(data), sha, blk)
    io = f.tell(); f.write(index)
    f.write(struct.pack('<BIIQQ', 0, 0x5A6F12E1, 4, io, len(index)) + hashlib.sha1(index).digest())
info = read_pak(out, str(root/'store-port/_verify'))
for (name, src) in files:
    assert (root/'store-port/_verify'/name).read_bytes() == src.read_bytes()
print('ok', out, out.stat().st_size, [e['name'] for e in info['entries']])
