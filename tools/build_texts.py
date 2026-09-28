"""Add text entries (names, assists, command list) for the extra characters to every
REDGame text table and pack them as DBFZSlotsText.pak.

Each extra copies the entries of a similar base character (code replaced), then its
display names are overridden. REDGame.uexp holds a UTF-16 "KEY\\r\\nVALUE\\r\\n" file.
"""
import os
import pathlib, struct, re, zlib, hashlib, sys
root = pathlib.Path(__file__).resolve().parent
work = root.parent
sys.path.insert(0, str(work))
from inspect_pak import read_pak

# extra code -> (base code to copy from, long name ES, short name ES, long name EN, short name EN)
EXTRAS = {
    'PCO': ('PCN', 'Piccolo (Naranja)', 'Piccolo Naranja', 'Orange Piccolo', 'Orange Piccolo'),
    'GHB': ('GHU', 'Gohan (Bestia)', 'Gohan Bestia', 'Gohan (Beast)', 'Beast Gohan'),
    'GKG': ('GKS', 'Goku (Super Saiyajin Dios)', 'Goku Dios', 'Goku (Super Saiyan God)', 'God Goku'),
    'VGF': ('VGS', 'Vegeta (Super Saiyajin 4)', 'Vegeta SSJ4', 'Vegeta (Super Saiyan 4)', 'SSJ4 Vegeta'),
    'RDN': ('BDN', 'Raditz', 'Raditz', 'Raditz', 'Raditz'),
    'DIO': ('BDN', 'DIO', 'DIO', 'DIO', 'DIO'),
    'YUG': ('AVP', 'Yugi Muto', 'Yugi', 'Yugi Muto', 'Yugi'),
    'SBG': ('YMN', 'Sol Badguy', 'Sol Badguy', 'Sol Badguy', 'Sol Badguy'),
    'SKN': ('BSN', 'Sukuna', 'Sukuna', 'Sukuna', 'Sukuna'),
    'OMG': ('BRS', 'Omega Shenron', 'Omega Shenron', 'Omega Shenron', 'Omega Shenron'),
    'SVG': ('VTB', 'Vegito (Super Saiyajin)', 'Super Vegito', 'Vegito (Super Saiyan)', 'Super Vegito'),
    'GRN': ('TRS', 'Granolah', 'Granolah', 'Granolah', 'Granolah'),
    'GK3': ('GKS', 'Goku (Super Saiyajin 3)', 'Goku SSJ3', 'Goku (Super Saiyan 3)', 'SSJ3 Goku'),
    'EXG': ('DGF', 'EX Goku (SS4, DAIMA)', 'EX Goku', 'EX Goku (SS4, DAIMA)', 'EX Goku'),
}

# Real texts shipped with the mods (English), keyed by the BASE code; applied to every language.
UNV = work.parent / 'Unverum/Mods/Dragon Ball FighterZ'
ANA = work / 'analisis-movesets'
MOD_TEXT = {
    'SBG': ('json', ANA / 'Soldguy moveset__solbadguy_de618/SolBadguy/text.json'),
    'SKN': ('json', ANA / 'Sukuna moveset__sukuna_moveset11_eng_jap_1722b/text.json'),
    'SVG': ('json', ANA / 'Supervegito moveset__udbfzsupervegito_v104/UDBFZSuperVegito v1.04/text.json'),
    'OMG': ('pak', ANA / 'Omega shenron__mod2/mod.pak'),
    'GRN': ('pak', UNV / 'Granolah Modded Moveset/mod.pak'),
    'GK3': ('pak', UNV / 'Goku (SSJ3) Moveset/mod.pak'),
}

def parse_table(uexp):
    n = struct.unpack_from('<I', uexp, 0x24)[0]
    s = uexp[0x30:0x30 + n].decode('utf-16-le').rstrip('\r\n')
    lines = s.split('\r\n')
    return {lines[i].lstrip('\x00\ufeff'): lines[i + 1] for i in range(0, len(lines) - 1, 2)}

def mod_overrides(base_int):
    """extra code -> {new key: text} from the mods' own texts."""
    out = {}
    for extra, (kind, path) in MOD_TEXT.items():
        base = EXTRAS[extra][0]; o = {}
        if not path.exists(): print('missing text source', path); continue
        if kind == 'json':
            import json
            for e in json.load(open(path, encoding='utf-8-sig'))['Entries']:
                nk = key_for(base, extra, e['header'])
                if nk: o[nk] = e['text']
        else:
            d = read_pak(path); f = open(path, 'rb')
            for e in d['entries']:
                if e['name'].endswith('Localization/INT/REDGame.uexp'):
                    ue = b''.join(zlib.decompress((f.seek(a), f.read(b - a))[1]) for a, b in e['blocks']) if e['method'] else (f.seek(e['offset'] + e['header']), f.read(e['raw']))[1]
                    for k, v in parse_table(ue).items():
                        nk = key_for(base, extra, k)
                        if nk and base_int.get(k) != v: o[nk] = v
        out[extra] = o
        print(extra, 'mod texts:', len(o))
    return out

SPANISH = {'SPA', 'ESN'}

def key_for(base, extra, key):
    """If `key` belongs to character `base`, return the same key for `extra`."""
    pats = [(rf'^CMD{base}(\d\d\w*)$', rf'CMD{extra}\1'), (rf'^STGCMD{base}(\d\d)$', rf'STGCMD{extra}\1'),
            (rf'^{base}_ASSIST_(\d\d)$', rf'{extra}_ASSIST_\1'), (rf'^CHARA_NAME_(L|S|DEMO)_{base}$', rf'CHARA_NAME_\1_{extra}'),
            (rf'^AVATAR_NAME_{base}$', rf'AVATAR_NAME_{extra}'), (rf'^ComboChallengeName{base}(\d\d)$', rf'ComboChallengeName{extra}\1')]
    for p, r in pats:
        if re.match(p, key):
            return re.sub(p, r, key)
    return None

def patch(lang, uasset, uexp, overrides):
    n = struct.unpack_from('<I', uexp, 0x24)[0]
    assert struct.unpack_from('<I', uexp, 0x28)[0] == n
    text = uexp[0x30:0x30 + n]
    tail = uexp[0x30 + n:]
    assert tail[-4:] == bytes.fromhex('c1832a9e')
    s = text.decode('utf-16-le')
    body = s.rstrip('\r\n')
    lines = body.split('\r\n')
    keys = [lines[i].lstrip('\x00\ufeff') for i in range(0, len(lines) - 1, 2)]
    vals = [lines[i + 1] for i in range(0, len(lines) - 1, 2)]
    existing = set(keys)
    add = []
    for extra, (base, les, ses, len_, sen) in EXTRAS.items():
        names = (les, ses) if lang in SPANISH else (len_, sen)
        for k, v in zip(keys, vals):
            nk = key_for(base, extra, k)
            if nk and nk not in existing:
                if nk.startswith(('CHARA_NAME_L_', 'AVATAR_NAME_')): v = names[0]
                elif nk.startswith(('CHARA_NAME_S_', 'CHARA_NAME_DEMO_')): v = names[1]
                elif nk in overrides.get(extra, {}): v = overrides[extra][nk]
                add.append((nk, v)); existing.add(nk)
        for nk, v in overrides.get(extra, {}).items():   # mod keys the base character does not have
            if nk not in existing and not nk.startswith(('CHARA_NAME_', 'AVATAR_NAME_')):
                add.append((nk, v)); existing.add(nk)
    new = body + ''.join('\r\n%s\r\n%s' % kv for kv in add) + s[len(body):]
    newtext = new.encode('utf-16-le')
    m = len(newtext)
    out = bytearray(uexp[:0x30]) + newtext + tail
    struct.pack_into('<I', out, 0x24, m); struct.pack_into('<I', out, 0x28, m)
    old_serial = len(uexp) - 4
    ua = bytearray(uasset)
    hits = [i for i in range(len(ua) - 3) if struct.unpack_from('<I', ua, i)[0] == old_serial]
    assert len(hits) == 1, hits
    struct.pack_into('<I', ua, hits[0], len(out) - 4)
    return bytes(ua), bytes(out), len(add)

def main():
    pak = os.environ.get('DBFZ_GAME', 'D:/Games/Dragon Ball FighterZ') + '/RED/Content/Paks/pakchunk0-WinAnvil.pak'
    d = read_pak(pak)
    ents = {e['name']: e for e in d['entries'] if re.match(r'RED/Content/Localization/\w+/REDGame\.u(asset|exp)$', e['name'])}
    f = open(pak, 'rb')
    def data(e):
        return b''.join(zlib.decompress((f.seek(a), f.read(b - a))[1]) for a, b in e['blocks'])
    files = []
    base_int = parse_table(data(ents['RED/Content/Localization/INT/REDGame.uexp']))
    overrides = mod_overrides(base_int)
    for name in sorted(ents):
        if not name.endswith('.uasset'): continue
        lang = name.split('/')[3]
        ua, ue = data(ents[name]), data(ents[name[:-6] + 'uexp'])
        ua2, ue2, nadd = patch(lang, ua, ue, overrides)
        print(lang, 'added', nadd)
        files += [(name, ua2), (name[:-6] + 'uexp', ue2)]
    write_pak(root / 'paks/DBFZSlotsText.pak', files)

def fstring(s):
    b = s.encode('ascii') + b'\0'; return struct.pack('<i', len(b)) + b
def entry(off, packed, raw, sha, blk):
    return struct.pack('<QQQI', off, packed, raw, 1) + sha + struct.pack('<I', 1) + struct.pack('<QQ', *blk) + struct.pack('<BI', 0, raw)
def write_pak(out, files):
    index = bytearray(fstring('../../../') + struct.pack('<i', len(files)))
    with open(out, 'wb') as f:
        for name, dat in files:
            comp = zlib.compress(dat, 9); sha = hashlib.sha1(dat).digest(); off = f.tell()
            hl = len(entry(0, 0, 0, sha, (0, 0))); blk = (off + hl, off + hl + len(comp))
            f.write(entry(0, len(comp), len(dat), sha, blk)); f.write(comp)
            index += fstring(name) + entry(off, len(comp), len(dat), sha, blk)
        io = f.tell(); f.write(index)
        f.write(struct.pack('<BIIQQ', 0, 0x5A6F12E1, 4, io, len(index)) + hashlib.sha1(index).digest())
    d = read_pak(out); g = open(out, 'rb')
    for (name, dat), e in zip(files, d['entries']):
        assert e['name'] == name
        got = b''.join(zlib.decompress((g.seek(a), g.read(b - a))[1]) for a, b in e['blocks'])
        assert got == dat
    print('ok', out, out.stat().st_size)

if __name__ == '__main__':
    main()
