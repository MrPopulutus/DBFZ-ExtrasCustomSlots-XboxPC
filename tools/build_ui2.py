"""Add portraits/icons for the converted characters to paks/DBFZSlotsUI.pak and write the
icon list used by DBFZSlotsIcons (mod/DBFZSlotsIcons/icons.txt).

For each new code, UI textures come from the mod when it ships them (named for the base
character) and otherwise from the base game's own texture for that base character.
Icons go to /Game/UI/CharaSelect_S3/<CODE>/ so numbers from different mods never clash.
"""
import os
import pathlib, sys, re, zlib, glob
root = pathlib.Path(__file__).resolve().parent
work = root.parent
sys.path.insert(0, str(work)); sys.path.insert(0, str(root))
from inspect_pak import read_pak
from build_char import entries_data, names, namehash, write_pak
import struct

UNV = work.parent / 'Unverum/Mods/Dragon Ball FighterZ'
ANA = work / 'analisis-movesets'
GAME = pathlib.Path(os.environ.get('DBFZ_GAME', 'D:/Games/Dragon Ball FighterZ')) / 'RED/Content/Paks/pakchunk0-WinAnvil.pak'
NEW = {  # code: (base, mod pak or None, base game icon number)
    'YUG': ('AVP', UNV / 'Yami Yugi - Character Moveset Mod/Yugi Muto - Character Moveset Mod/Yugi Muto Character Moveset Mod/YugiMutoCharacterMoveset.pak'),
    'SBG': ('YMN', ANA / 'Soldguy moveset__solbadguy_de618/SolBadguy/SolBadguy.pak'),
    'SKN': ('BSN', ANA / 'Sukuna moveset__sukuna_moveset11_eng_jap_1722b/mod.pak'),
    'OMG': ('BRS', ANA / 'Omega shenron__mod2/mod.pak'),
    'SVG': ('VTB', ANA / 'Supervegito moveset__udbfzsupervegito_v104/UDBFZSuperVegito v1.04/UDBFZ_SuperVegito.pak'),
    'GRN': ('TRS', UNV / 'Granolah Modded Moveset/mod.pak'),
    'GK3': ('GKS', UNV / 'Goku (SSJ3) Moveset/mod.pak'),
    'WRZ': ('DGF', UNV / 'Sonic x Dragon Ball FighterZ Vol.3 - Werezaru Goku/WerezaruGoku/WerezaruGoku.pak'),
    'EXG': ('DGF', UNV / 'EX Goku(SS4, DAIMA) Moveset/EXDaimaGoku/EXDaimaGoku.pak'),
}
OLD_ICONS = [('PCO', 'ext/CS_CIcon19'), ('GHB', 'ext/CS_CIcon03'), ('GKG', 'ext/CS_CIcon05'),
             ('VGF', 'ext/CS_CIcon13'), ('RDN', 'ext/CS_CIcon99'), ('DIO', 'ext/CS_CIcon15')]
KINDS = [('Chara_Image/Face_A/', 'cp_chara_'), ('Chara_Image/Face_A/', 'cp_chara_sparking_'), ('Chara_Image/Face_B/', 'vs_chara_'),
         ('Chara_Image/Face_C/', 'arcade_chara_'), ('Chara_Image/Face_D/', 'faceD_'), ('Chara_Image/Story_Stand/', 'StoryStand_'),
         ('CharaSelect_S3/tex/', 'CS_CharacterImage_')]

def rename_uasset(b, conv):
    new = bytearray(b)
    for s, start, size, hpos, enc in names(b):
        t = conv(s)
        if t == s: continue
        data = (t + '\0').encode(enc); assert len(data) == size, (s, t)
        new[start:start + size] = data
        stored = struct.unpack_from('<I', b, hpos)[0]; comp = namehash(s, enc); nh = namehash(t, enc)
        if stored == 0: nh = 0
        elif stored == comp & 65535: nh &= 65535
        elif stored != comp: nh = stored
        struct.pack_into('<I', new, hpos, nh)
    return bytes(new)

def main():
    game = {n.lower(): (n, get) for n, get in entries_data(GAME) if n.startswith('RED/Content/UI/')}
    pak = root / 'paks/DBFZSlotsUI.pak'
    files = dict((n, get()) for n, get in entries_data(pak))
    icons = [(c, '/Game/UI/CharaSelect_S3/%s.%s' % (p, p.split('/')[-1])) for c, p in OLD_ICONS]
    for code, (base, modpak) in NEW.items():
        mod = {n.lower(): (n, get) for n, get in entries_data(modpak) if '/UI/' in n}
        for folder, prefix in KINDS:
            stem = 'RED/Content/UI/' + folder + prefix + base
            src = mod if (stem + '.uasset').lower() in mod else game
            if (stem + '.uasset').lower() not in src:
                print(code, 'no', prefix, 'anywhere'); continue
            for ext in ('.uasset', '.uexp', '.ubulk'):
                k = (stem + ext).lower()
                if k not in src: continue
                n, get = src[k]; data = get()
                newname = 'RED/Content/UI/' + folder + prefix + code + ext
                if ext == '.uasset':
                    rx = re.compile(re.escape(prefix) + base + '$', re.I)
                    conv = lambda s, rx=rx: rx.sub(prefix + code, s) if not s.startswith('/') else re.sub(re.escape(prefix) + base + '$', prefix + code, s, flags=re.I)
                    data = rename_uasset(data, conv)
                files[newname] = data
            print(code, prefix, 'from', 'mod' if src is mod else 'game')
        iconsrc = [n for n in mod if re.search(r'/charaselect_s3/tex/cs_cicon\d\d\.uasset$', n)]
        if iconsrc:
            src, stem = mod, iconsrc[0][:-len('.uasset')]
        else:  # base game icon of the base character (DGF = 45)
            num = {'DGF': '45'}[base]; src = game; stem = ('RED/Content/UI/CharaSelect_S3/tex/CS_CIcon' + num).lower()
        realstem = src[stem + '.uasset'][0][:-len('.uasset')]
        leaf = realstem.split('/')[-1]
        for ext in ('.uasset', '.uexp', '.ubulk'):
            if stem + ext not in src: continue
            data = src[stem + ext][1]()
            if ext == '.uasset':
                data = rename_uasset(data, lambda s: s.replace('/CharaSelect_S3/tex/', '/CharaSelect_S3/%s/' % code))
            files['RED/Content/UI/CharaSelect_S3/%s/%s%s' % (code, leaf, ext)] = data
        icons.append((code, '/Game/UI/CharaSelect_S3/%s/%s.%s' % (code, leaf, leaf)))
        print(code, 'icon', leaf, 'from', 'mod' if src is mod else 'game')
    write_pak(pak, sorted(files.items()))
    (root / 'mod/DBFZSlotsIcons').mkdir(parents=True, exist_ok=True)
    (root / 'mod/DBFZSlotsIcons/icons.txt').write_text(''.join('%s %s\n' % i for i in icons))
    print('pak files', len(files)); print(open(root / 'mod/DBFZSlotsIcons/icons.txt').read())

if __name__ == "__main__":
    main()
