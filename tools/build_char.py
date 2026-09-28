"""Turn a replacement moveset (which overrides a base character) into its own character code.

  base game files of Chara/<BASE>  +  the mod's files for Chara/<BASE>  ->  Chara/<NEW>
  (+ extra folders the mod adds, e.g. Chara/YGI, copied as they are)

Asset paths /Game/Chara/<BASE>/ and the BBS_/COL_ data names are renamed to <NEW>
(same length, so name maps keep their layout; name hashes are recomputed).
Mod files for other base characters (e.g. Whis, Vegeta) are skipped so base
characters stay unchanged. New files under Shared/ are kept; overrides of
existing Shared files are skipped.

usage: build_char.py NEW BASE mod.pak [mod2.pak ...] [--keep YGI,SOL]
output: paks/chars/DBFZX_<NEW>.pak and a report paks/chars/DBFZX_<NEW>.json
"""
import os
import pathlib, sys, re, zlib, struct, hashlib, json, argparse
root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(root.parent))
from inspect_pak import read_pak

GAME_PAK = pathlib.Path(os.environ.get('DBFZ_GAME', 'D:/Games/Dragon Ball FighterZ')) / 'RED/Content/Paks/pakchunk0-WinAnvil.pak'  # set DBFZ_GAME to your game folder

table = []
for i in range(256):
    c = i << 24
    for _ in range(8): c = ((c << 1) ^ (0x04c11db7 if c & 0x80000000 else 0)) & 0xffffffff
    table.append(c)
def namehash(s, enc):
    h = 0
    up = ''.join(chr(ord(c) - 32) if 'a' <= c <= 'z' else c for c in s)
    for b in up.encode(enc): h = (h >> 8) ^ table[(h ^ b) & 255]
    return (h & 65535) | ((zlib.crc32(s.encode('utf-32-le')) & 65535) << 16)
def names(b):
    assert struct.unpack_from('<i', b, 4)[0] == -7
    folderlen = struct.unpack_from('<i', b, 28)[0]
    p = 32 + folderlen + 4
    count, offset = struct.unpack_from('<ii', b, p)
    for _ in range(count):
        n = struct.unpack_from('<i', b, offset)[0]; offset += 4
        size = abs(n) * (2 if n < 0 else 1); enc = 'utf-16-le' if n < 0 else 'utf8'
        text = b[offset:offset + size].decode(enc).rstrip('\0'); hpos = offset + size
        yield text, offset, size, hpos, enc
        offset = hpos + 4

def entries_data(pak):
    d = read_pak(pak); f = open(pak, 'rb')
    for e in d['entries']:
        n = (d['mount'] + e['name']).lstrip('./')
        if not n.startswith('RED/'):
            n = 'RED/Content/' + n if not n.startswith('Content/') else 'RED/' + n
        def get(e=e):
            if e['method']:
                return b''.join(zlib.decompress((f.seek(a), f.read(b - a))[1]) for a, b in e['blocks'])
            f.seek(e['offset'] + e['header']); return f.read(e['raw'])
        yield n, get

def make_conv(base, new):
    rx_path = re.compile(r'(/chara/)' + base + '(/|$)', re.I)
    rx_data = re.compile(r'^(BBS_|COL_)' + base + '(EF)?$', re.I)
    def keep_case(m_text, repl):
        return repl.lower() if m_text.islower() else repl
    def conv(s):
        t = rx_path.sub(lambda m: m.group(1) + keep_case(s[m.start() + len(m.group(1)):m.start() + len(m.group(1)) + 3], new) + m.group(2), s)
        t = rx_data.sub(lambda m: m.group(1) + keep_case(s[len(m.group(1)):len(m.group(1)) + 3], new) + (m.group(2) or ''), t)
        # package paths ending in the data asset name: .../Common/Data/BBS_BASE(EF) or COL_BASE
        t = re.sub(r'(/)(BBS_|COL_)' + base + r'(EF)?$', lambda m: m.group(1) + m.group(2) + new + (m.group(3) or ''), t, flags=re.I)
        return t
    return conv

def convert_uasset(b, conv, report, path):
    new = bytearray(b)
    for s, start, size, hpos, enc in names(b):
        t = conv(s)
        if t == s: continue
        data = (t + '\0').encode(enc); assert len(data) == size, (s, t)
        new[start:start + size] = data
        stored = struct.unpack_from('<I', b, hpos)[0]; comp = namehash(s, enc)
        nh = namehash(t, enc)
        if stored == 0: nh = 0
        elif stored == comp & 65535: nh &= 65535
        elif stored != comp:
            report['hash_mismatch'].append([path, s]); nh = stored
        struct.pack_into('<I', new, hpos, nh)
    return bytes(new)

def convert_uexp(b, base, new):
    out = b
    for a, c in ((('/Chara/%s/' % base), ('/Chara/%s/' % new)), (('/chara/%s/' % base.lower()), ('/chara/%s/' % new.lower()))):
        for enc in ('ascii', 'utf-16-le'):
            out = out.replace(a.encode(enc), c.encode(enc))
    return out

def rename_path(path, base, new):
    p = re.sub(r'(RED/Content/Chara/)' + base + '/', r'\g<1>' + new + '/', path, flags=re.I)
    p = re.sub(r'/(BBS_|COL_)' + base + r'(EF)?\.', lambda m: '/' + m.group(1) + new + (m.group(2) or '') + '.', p, flags=re.I)
    return p

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('new'); ap.add_argument('base'); ap.add_argument('paks', nargs='+')
    ap.add_argument('--keep', default='')
    ap.add_argument('--keep-refs', action='store_true', help='Preserve references in the character folders selected by --keep')
    ap.add_argument('--sub', default='', help='OLD:NEW,... other characters the mod changes; they get their own copy')
    ap.add_argument('--shared-map', default='', help='SEG:NEWSEG, keep overridden Shared/SEG files as Shared/NEWSEG copies')
    a = ap.parse_args()
    subs = dict(x.upper().split(':') for x in a.sub.split(',') if x)
    smap = dict(x.split(':') for x in a.shared_map.split(',') if x)
    for o, n_ in list(subs.items()) + list(smap.items()): assert len(o) == len(n_), (o, n_)
    new, base = a.new.upper(), a.base.upper()
    keep = [k.upper() for k in a.keep.split(',') if k]
    assert len(new) == len(base) == 3
    report = dict(new=new, base=base, mods=a.paks, keep=keep, from_game=0, from_mod=0, skipped=[], shared_new=0,
                  shared_override_skipped=0, hash_mismatch=[], missing_refs=[])

    # 1. base character from the game
    files = {}
    base_prefix = 'RED/Content/Chara/%s/' % base
    game_names = set()
    for n, get in entries_data(GAME_PAK):
        game_names.add(n.lower())
        if n.upper().startswith(base_prefix.upper()):
            files[n] = get(); report['from_game'] += 1
    # 1b. other characters the mod changes: full copies from the game
    for n, get in entries_data(GAME_PAK):
        parts = n.split('/')
        if len(parts) > 3 and parts[2] == 'Chara' and parts[3].upper() in subs:
            files[n] = get(); report.setdefault('from_game_sub', 0); report['from_game_sub'] += 1
    shared_paths = {}   # '/game/shared/seg/...'(lower) -> new package path
    # 2. mod files on top
    for pak in a.paks:
        for n, get in entries_data(pak):
            parts = n.split('/')
            if len(parts) > 3 and parts[2] == 'Chara' and parts[3].upper() in subs:
                key = next((k for k in files if k.lower() == n.lower()), n)
                files[key] = get(); report['from_mod'] += 1
            elif len(parts) > 3 and parts[2] == 'Shared' and n.lower() in game_names and parts[3] in smap:
                newn = '/'.join(parts[:3] + [smap[parts[3]]] + parts[4:])
                files[newn] = get(); report['shared_new'] += 1
                old_pkg = '/Game/' + n[len('RED/Content/'):].rsplit('.', 1)[0]
                shared_paths[old_pkg.lower()] = '/Game/' + newn[len('RED/Content/'):].rsplit('.', 1)[0]
            elif n.upper().startswith(base_prefix.upper()):
                # match the game's spelling of the same file if there is one
                key = next((k for k in files if k.lower() == n.lower()), n)
                files[key] = get(); report['from_mod'] += 1
            elif len(parts) > 3 and parts[2] == 'Chara' and parts[3].upper() in keep:
                files[n] = get(); report['from_mod'] += 1
            elif len(parts) > 2 and parts[2] == 'Shared':
                if n.lower() in game_names: report['shared_override_skipped'] += 1
                else: files[n] = get(); report['shared_new'] += 1
            else:
                report['skipped'].append(n)
    # 3. rename BASE -> NEW (and the copies of other characters / shared files)
    conv0 = make_conv(base, new)
    sub_rx = [(re.compile(r'(/chara/)' + o + '(/|$)', re.I), nn) for o, nn in subs.items()]
    def conv(s_):
        t = conv0(s_)
        for rx, nn in sub_rx:
            t = rx.sub(lambda m: m.group(1) + (nn.lower() if m.group(0)[len(m.group(1)):len(m.group(1)) + 3].islower() else nn) + m.group(2), t)
        k = t.lower()
        if k in shared_paths: t = shared_paths[k]
        return t
    sub_bytes = []
    for o, nn in subs.items():
        for a1, b1 in (('/Chara/%s/' % o, '/Chara/%s/' % nn), ('/chara/%s/' % o.lower(), '/chara/%s/' % nn.lower())):
            for enc in ('ascii', 'utf-16-le'): sub_bytes.append((a1.encode(enc), b1.encode(enc)))
    shared_bytes = []
    for old_l, newp in shared_paths.items():
        oldp = newp  # same length; rebuild the original spelling from the new one
        seg_new = newp.split('/')[3]; seg_old = [k for k, v in smap.items() if v == seg_new][0]
        oldp = newp.replace('/Shared/%s/' % seg_new, '/Shared/%s/' % seg_old, 1)
        for enc in ('ascii', 'utf-16-le'): shared_bytes.append((oldp.encode(enc), newp.encode(enc)))
    out = {}
    for n, data in files.items():
        parts = n.split('/')
        if a.keep_refs and len(parts) > 3 and parts[2] == 'Chara' and parts[3].upper() in keep:
            out[n] = data
            continue
        np_ = rename_path(n, base, new) if n.upper().startswith(base_prefix.upper()) else n
        for o, nn in subs.items():
            np_ = re.sub(r'(RED/Content/Chara/)' + o + '/', r'\g<1>' + nn + '/', np_, flags=re.I)
        if n.endswith('.uasset'):
            data = convert_uasset(data, conv, report, n)
        elif n.endswith('.uexp'):
            data = convert_uexp(data, base, new)
            for a1, b1 in sub_bytes: data = data.replace(a1, b1)
            if shared_bytes and b'Shared' in data or (shared_bytes and 'Shared'.encode('utf-16-le') in data):
                for a1, b1 in shared_bytes: data = data.replace(a1, b1)
        out[np_] = data
    # 4. references check: /Game/Chara/NEW/... imports must exist
    have = {k[len('RED/Content/'):].rsplit('.', 1)[0].lower() for k in out if k.endswith('.uasset')}
    for n, data in out.items():
        if not n.endswith('.uasset'): continue
        for s, *_ in names(data):
            if s.lower().startswith('/game/chara/%s/' % new.lower()):
                k = s[len('/Game/'):].lower()
                if k not in have and not any(h.startswith(k + '_') for h in have): report['missing_refs'].append([n, s])
    report['missing_refs'] = report['missing_refs'][:200]
    report['skipped'] = sorted(set(report['skipped']))
    dst = root / 'paks/chars'; dst.mkdir(parents=True, exist_ok=True)
    write_pak(dst / ('DBFZX_%s.pak' % new), sorted(out.items()))
    (dst / ('DBFZX_%s.json' % new)).write_text(json.dumps(report, indent=1))
    print(new, 'files', len(out), 'game', report['from_game'], 'mod', report['from_mod'], 'shared new', report['shared_new'],
          'shared overrides skipped', report['shared_override_skipped'], 'skipped', len(report['skipped']),
          'hash mismatches', len(report['hash_mismatch']), 'missing refs', len(report['missing_refs']))

def fstring(s):
    b = s.encode('ascii') + b'\0'; return struct.pack('<i', len(b)) + b
def entry(off, packed, raw, sha, blk):
    return struct.pack('<QQQI', off, packed, raw, 1) + sha + struct.pack('<I', 1) + struct.pack('<QQ', *blk) + struct.pack('<BI', 0, raw)
def write_pak(path, files, compression=6):
    index = bytearray(fstring('../../../') + struct.pack('<i', len(files)))
    with open(path, 'wb') as f:
        for name, dat in files:
            comp = zlib.compress(dat, compression); sha = hashlib.sha1(dat).digest(); off = f.tell()
            hl = len(entry(0, 0, 0, sha, (0, 0))); blk = (off + hl, off + hl + len(comp))
            f.write(entry(0, len(comp), len(dat), sha, blk)); f.write(comp)
            index += fstring(name) + entry(off, len(comp), len(dat), sha, blk)
        io = f.tell(); f.write(index)
        f.write(struct.pack('<BIIQQ', 0, 0x5A6F12E1, 4, io, len(index)) + hashlib.sha1(index).digest())
    d = read_pak(path)
    assert [e['name'] for e in d['entries']] == [n for n, _ in files]

if __name__ == '__main__':
    main()
