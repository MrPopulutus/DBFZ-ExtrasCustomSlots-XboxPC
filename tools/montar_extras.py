"""Build the 14-character reference roster on your own PC, from the mods you download.

Nothing made from other people's mods is shipped with the port: this script takes the
original downloads (zip files or extracted folders) and produces, locally, the same
character paks, preload repair, Werezaru-on-EX-Goku overlay, text pak, portrait/icon
pak, chara_mods.txt and icons.txt as the tested setup.

  python montar_extras.py --descargas "C:\\DBFZ descargas" --juego "D:\\Games\\Dragon Ball FighterZ"
  python montar_extras.py ... --instalar          (copies the result into the game, with a backup)
  python montar_extras.py ... --solo SBG,GRN      (only some characters; others are left out of the roster)

Requirements: use the complete installer package for its Game/ assets and SIG
template. The source-only repository does not include those files. Close the
game before using --instalar; without that flag, output stays outside the game.
"""
import sys as _sys, pathlib as _pl; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from idioma import t
import argparse, datetime, hashlib, json, os, pathlib, re, runpy, shutil, struct, subprocess, sys, tempfile, zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# Match sources by pak name and character folders. Prefer the tested SHA-256;
# ambiguous untested versions are skipped by elegir().
FUENTES = {
    # Replacement movesets (their own pages), each turned into its own character code here.
    # 'con': character folders the download must contain (several use the same file name).
    'piccolo':  dict(pak='OrangePiccolo.pak', chara='PCN', con=['PCN'], web='https://gamebanana.com/mods/472631'),
    'godgoku':  dict(pak='GodGoku.pak', chara='GKS', con=['GKS'], web='https://gamebanana.com/mods/395251'),
    'vegeta4':  dict(pak='SS4VegetaMoveset.pak', chara='VGS', con=['VGS'], web='https://gamebanana.com/mods/525644'),
    'dio':      dict(pak='DIOCharacterMoveset.pak', chara='CEN', con=['CEN'], web='https://gamebanana.com/mods/564409'),
    'raditz':   dict(pak='RaditzMoveset.pak', chara='MGS', con=['MGS'], web='https://gamebanana.com/mods/440356'),
    'gohan':    dict(pak='BeastGohanMoveset.pak', chara='GHU', con=['GHU'], web='https://gamebanana.com/mods/594699'),
    'yugi':     dict(pak='YugiMutoCharacterMoveset.pak', chara='AVP', web='https://gamebanana.com/mods/641650'),
    'sol':      dict(pak='SolBadguy.pak', chara='YMN', web='https://gamebanana.com/mods/655977'),
    'sukuna':   dict(pak='mod.pak', chara='BSN', web='https://gamebanana.com/mods/581695'),
    'omega':    dict(pak='mod.pak', chara='BRS', web='https://gamebanana.com/mods/451264'),
    'vegito':   dict(pak='UDBFZ_SuperVegito.pak', chara='VTB', web='https://gamebanana.com/mods/431940'),
    'granolah': dict(pak='mod.pak', chara='TRS', web='https://gamebanana.com/mods/461713'),
    'ssj3':     dict(pak='mod.pak', chara='GKS', web='https://gamebanana.com/mods/444309'),
    'exgoku':   dict(pak='EXDaimaGoku.pak', chara='DGF', web='https://gamebanana.com/mods/679368'),
    'werezaru': dict(pak='WerezaruGoku.pak', chara='DGF', web='https://gamebanana.com/mods/695077', opcional=True),
}
PROBADO = {'piccolo': 'ca839d64a8f1ebf2dce668153a42c6c3b3f1065f97d1df8df5fab2c4078d4e45', 'godgoku': '9054b422390322633db504c9cc43bab721fe9bcf3d4bb6c1d8bc69a0522f32d1', 'vegeta4': '880aa3a7f921327a9abc465e0e73f228471bc56bab49e5d3efa4e6304eb94a92', 'raditz': 'f9f25faa58bda7240f64e1d57bc08b96665cd649d3909ca65e0b29c7e96d8c03', 'dio': 'ec688ed70415bff13e6cac550d7315ff1ad8a7ece9874fd30daeef8b7aab6029', 'gohan': '43b5c5c3676cc159c13685671e6908e23800bd11c57e01956bfcc187d1fa723f', 'yugi': 'c122de86dc6402d3efa9dcce9d9fd3b8afc25d5157ed57b122484eb63c4fb1a9', 'sol': '607ec2779525e90c74b5f26b6f605b032c165a46eef60d4c60e9d53591e1c3b6', 'sukuna': '6f8a93f56e0d0cae9488d9239e2b765e9dc4445a74d24d964214be60aa4bbcdc', 'omega': '40664aebcf8dbb6744a6f3b9fc4dd999437c4c0cced721d24981146b0987af42', 'vegito': '765588b5b3d24612bdecd6eadf6c41c763ac41c9534efdcf7aaddbb1df2ccbb4', 'granolah': '8116d3b451d513185e294a0eeba356578f2b5d2262f4607a4e5cc5668a943440', 'ssj3': '173b25f76bdb6b53afd243685c1c04a36de9ff16ab19b73e0052f1c695817330', 'exgoku': '6ff234f1d2b145b13ef3f5ed58eeaa92e807b5babd0f2758990c0584824d9f69', 'werezaru': '588814bcb85364b134d56e9bb3909e6c73b4718c1d717ce8df1af5affa1df6e4'}
# code: how it is built. names = (long ES, short ES, long EN, short EN); texto = base code for texts.
ROSTER = [
    ('PCO', dict(tipo='convertir', fuente='piccolo', base='PCN', args=[], ui=('piccolo', 'PCN'), texto='PCN',
                 names=('Piccolo (Naranja)', 'Piccolo Naranja', 'Orange Piccolo', 'Orange Piccolo'))),
    ('GHB', dict(tipo='convertir', fuente='gohan', base='GHU', args=[], ui=('gohan', 'GHU'), texto='GHU',
                 names=('Gohan (Bestia)', 'Gohan Bestia', 'Gohan (Beast)', 'Beast Gohan'))),
    ('GKG', dict(tipo='convertir', fuente='godgoku', base='GKS', args=['--keep', 'GOD', '--sub', 'SRG:SRX'], ui=('godgoku', 'GKS'), texto='GKS',
                 names=('Goku (Super Saiyajin Dios)', 'Goku Dios', 'Goku (Super Saiyan God)', 'God Goku'))),
    ('VGF', dict(tipo='convertir', fuente='vegeta4', base='VGF', args=[], ui=('vegeta4', 'VGS'), texto='VGS',
                 names=('Vegeta (Super Saiyajin 4)', 'Vegeta SSJ4', 'Vegeta (Super Saiyan 4)', 'SSJ4 Vegeta'))),
    ('RDN', dict(tipo='convertir', fuente='raditz', base='MGS', args=[], ui=(None, 'BDN'), texto='BDN',
                 names=('Raditz', 'Raditz', 'Raditz', 'Raditz'))),
    ('DIO', dict(tipo='convertir', fuente='dio', base='CEN', args=['--keep', 'DIO,WLD'], ui=('dio', 'CEN'), texto='BDN',
                 names=('DIO', 'DIO', 'DIO', 'DIO'))),
    ('YUG', dict(tipo='convertir', fuente='yugi', base='AVP', args=['--keep', 'YGI', '--keep-refs'], texto='AVP',
                 names=('Yugi Muto', 'Yugi', 'Yugi Muto', 'Yugi'))),
    ('SBG', dict(tipo='convertir', fuente='sol', base='YMN', args=['--keep', 'SOL'], texto='YMN', textos='json', precarga=True,
                 names=('Sol Badguy', 'Sol Badguy', 'Sol Badguy', 'Sol Badguy'))),
    ('SKN', dict(tipo='convertir', fuente='sukuna', base='BSN', args=['--sub', 'WTN:URA'], texto='BSN', textos='json',
                 names=('Sukuna', 'Sukuna', 'Sukuna', 'Sukuna'))),
    ('OMG', dict(tipo='convertir', fuente='omega', base='BRS', args=[], texto='BRS', textos='pak',
                 names=('Omega Shenron', 'Omega Shenron', 'Omega Shenron', 'Omega Shenron'))),
    ('SVG', dict(tipo='convertir', fuente='vegito', base='VTB', args=['--sub', 'VGS:VGX'], texto='VTB', textos='json',
                 names=('Vegito (Super Saiyajin)', 'Super Vegito', 'Vegito (Super Saiyan)', 'Super Vegito'))),
    ('GRN', dict(tipo='convertir', fuente='granolah', base='TRS', args=[], texto='TRS', textos='pak', precarga=True,
                 names=('Granolah', 'Granolah', 'Granolah', 'Granolah'))),
    ('GK3', dict(tipo='convertir', fuente='ssj3', base='GKS', args=[], texto='GKS', textos='pak',
                 names=('Goku (Super Saiyajin 3)', 'Goku SSJ3', 'Goku (Super Saiyan 3)', 'SSJ3 Goku'))),
    ('EXG', dict(tipo='convertir', fuente='exgoku', base='DGF', args=[], texto='DGF', aspecto='werezaru',
                 names=('EX Goku (SS4, DAIMA)', 'EX Goku', 'EX Goku (SS4, DAIMA)', 'EX Goku'))),
]
ICONO_JUEGO = {'BDN': 25, 'DGF': 45}   # base-game select icon number, when the mod has no icon
KINDS = [('Chara_Image/Face_A/', 'cp_chara_'), ('Chara_Image/Face_A/', 'cp_chara_sparking_'), ('Chara_Image/Face_B/', 'vs_chara_'),
         ('Chara_Image/Face_C/', 'arcade_chara_'), ('Chara_Image/Face_D/', 'faceD_'), ('Chara_Image/Story_Stand/', 'StoryStand_'),
         ('CharaSelect_S3/tex/', 'CS_CharacterImage_')]
def log(*a): print(*a, flush=True)

# Finding the downloads
def pak_charas(path):
    from inspect_pak import read_pak
    import collections
    d = read_pak(path); found = collections.Counter()
    for e in d['entries']:
        m = re.search(r'(?:^|/)Chara/(\w{3})/', d['mount'] + e['name'])
        if m: found[m.group(1).upper()] += 1
    return found

def sha(path, n=None):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()[:n] if n else h.hexdigest()

def buscar(descargas, tmp):
    """Every .pak in the downloads (also inside .zip files), with its text.json and .sig if present."""
    paks = []
    for p in sorted(q for d in descargas for q in pathlib.Path(d).rglob('*')):
        if p.suffix.lower() == '.pak':
            paks.append(dict(pak=p, text=p.with_name('text.json') if p.with_name('text.json').exists() else None,
                             sig=p.with_suffix('.sig') if p.with_suffix('.sig').exists() else None, origen=str(p)))
        elif p.suffix.lower() == '.zip':
            with zipfile.ZipFile(p) as z:
                members = z.namelist()
                for m in members:
                    if not m.lower().endswith('.pak'): continue
                    folder = m.rsplit('/', 1)[0] + '/' if '/' in m else ''
                    dest = pathlib.Path(tempfile.mkdtemp(dir=tmp))
                    def take(name, dest=dest):
                        out = dest / pathlib.PurePosixPath(name).name
                        with z.open(name) as src, open(out, 'wb') as dst: shutil.copyfileobj(src, dst)
                        return out
                    tj = next((x for x in members if x.lower() == (folder + 'text.json').lower()), None)
                    sg = next((x for x in members if x.lower() == (m[:-4] + '.sig').lower()), None)
                    paks.append(dict(pak=take(m), text=take(tj) if tj else None, sig=take(sg) if sg else None,
                                     origen='%s -> %s' % (p, m)))
        elif p.suffix.lower() in ('.7z', '.rar'):
            tar = pathlib.Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32/tar.exe'
            if not tar.is_file():
                raise RuntimeError(t('No está disponible tar de Windows para abrir ', 'Windows tar is not available to open ') + p.name + t('. Usa una carpeta ya extraída.', '. Use an extracted folder instead.'))
            dest = pathlib.Path(tempfile.mkdtemp(dir=tmp))
            log(t('  Extrayendo', '  Extracting'), p.name, t('con el lector de archivos de Windows...', 'with the Windows archive reader...'))
            subprocess.run([str(tar), '-xf', str(p.resolve()), '-C', str(dest)], check=True)
            for q in dest.rglob('*.pak'):
                if not q.resolve().is_relative_to(dest.resolve()): raise RuntimeError(t('Ruta de archivo no válida en ', 'Invalid file path in ') + p.name)
                paks.append(dict(pak=q, text=q.with_name('text.json') if q.with_name('text.json').exists() else None,
                                 sig=q.with_suffix('.sig') if q.with_suffix('.sig').exists() else None,
                                 origen='%s -> %s' % (p, q.relative_to(dest))))
    for d in paks: d['charas'] = pak_charas(d['pak']); d['sha'] = sha(d['pak'])
    return paks

def elegir(paks, necesarias):
    elegidas, faltan = {}, []
    for key in necesarias:
        f = FUENTES[key]
        # same file name, and the expected character folders ('con') or main folder of the pak
        def fits(d):
            if d['sha'].startswith(PROBADO.get(key, '-')): return True
            c = d['charas']
            if f.get('con'): return all(x in c for x in f['con'])
            return c.most_common(1)[0][0] == f['chara']
        cands = [d for d in paks if d['pak'].name.lower() == f['pak'].lower() and d['charas'] and fits(d)]
        if not cands:
            faltan.append(key); continue
        best = next((d for d in cands if d['sha'].startswith(PROBADO.get(key, '-'))), None)
        if not best:
            if len({d['sha'] for d in cands}) > 1:
                log(t('  Omitido %s: hay varias versiones desconocidas y ninguna es la probada.', '  Skipped %s: several unknown versions and none is the tested one.') % key)
                for d in cands: log('    %s  SHA-256 %s' % (d['origen'], d['sha']))
                log(t('  Deja solo la versión que quieras usar o descarga la versión de referencia.', '  Keep only the version you want, or download the reference version.'))
                faltan.append(key)
                continue
            best = cands[-1]
            log(t('  aviso: %s es una versión distinta de la probada (%s)', '  warning: %s is a different version from the tested one (%s)') % (key, best['origen']))
        elif len(cands) > 1:
            log(t('  %s: hay %d versiones, uso la probada', '  %s: %d versions found, using the tested one') % (key, len(cands)))
        elegidas[key] = best
    return elegidas, faltan

# Building
def raditz_desde_juego(files, game):
    """Raditz has no portraits of his own (his download ships none), so he uses the game's
    Bardock (BDN) portraits and select icon, renamed to RDN. Only game content is reused."""
    from build_ui2 import rename_uasset
    for folder, prefix in KINDS:
        stem = 'RED/Content/UI/' + folder + prefix + 'BDN'
        for ext in ('.uasset', '.uexp', '.ubulk'):
            k = (stem + ext).lower()
            if k not in game: continue
            data = game[k][1]()
            if ext == '.uasset':
                rx = re.compile(re.escape(prefix) + 'BDN$', re.I)
                data = rename_uasset(data, lambda s, rx=rx, prefix=prefix: rx.sub(prefix + 'RDN', s))
            files['RED/Content/UI/' + folder + prefix + 'RDN' + ext] = data
    stem = 'RED/Content/UI/CharaSelect_S3/tex/CS_CIcon25'   # Bardock's select icon
    for ext in ('.uasset', '.uexp', '.ubulk'):
        k = (stem + ext).lower()
        if k not in game: continue
        data = game[k][1]()
        if ext == '.uasset':
            data = rename_uasset(data, lambda s: s.replace('/CharaSelect_S3/tex/CS_CIcon25', '/CharaSelect_S3/ext/CS_CIcon99').replace('CS_CIcon25', 'CS_CIcon99'))
        files['RED/Content/UI/CharaSelect_S3/ext/CS_CIcon99' + ext] = data

def construir_ui(roster, elegidas, game_pak, out):
    """Portraits (7 kinds) and select icon for each code, from the mod when it has them (named for
    the base character) or from the game. Icons go to /Game/UI/CharaSelect_S3/<CODE>/."""
    from build_char import entries_data, names, write_pak
    from build_ui2 import rename_uasset
    game = {n.lower(): (n, g) for n, g in entries_data(game_pak) if n.startswith('RED/Content/UI/')}
    files, icons = {}, []
    old_icons = dict(PCO=19, GHB=3, GKG=5, VGF=13, RDN=99, DIO=15)
    # Codes with a numbered select icon: every UI file of their download, including locked icons.
    for code, r in roster:
        if code not in old_icons or code == 'RDN': continue
        key, base = r['ui']
        for n, get in entries_data(elegidas[key]['pak']):
            if '/UI/' not in n: continue
            data = get()
            if re.search(r'/CS_CIcon\d\d(_Lock)?\.', n):
                conv = lambda x: x.replace('/CharaSelect_S3/tex/', '/CharaSelect_S3/ext/')
                newpath = conv(n)
            else:
                rx = re.compile(base, re.I)
                conv = lambda x, rx=rx, base=base, code=code: rx.sub(code, x) if re.search(r'(?i)(chara_|faceD_|StoryStand_|CharacterImage_)' + base, x) else x
                newpath = rx.sub(code, n)
            files[newpath] = rename_uasset(data, conv) if n.endswith('.uasset') else data
    if any(c == 'RDN' for c, _ in roster):
        raditz_desde_juego(files, game)
    for code, r in roster:
        if code in old_icons:
            leaf = 'CS_CIcon%02d' % old_icons[code]
            icons.append((code, '/Game/UI/CharaSelect_S3/ext/%s.%s' % (leaf, leaf)))
    ui_roster = list(roster)
    if 'werezaru' in elegidas:
        ui_roster.append(('WRZ', dict(tipo='convertir', fuente='werezaru', base='DGF')))
    for code, r in ui_roster:
        if code in old_icons: continue
        src_key, base = r.get('ui', (None, r.get('base')))
        mod = {}
        if src_key and src_key in elegidas:
            mod = {n.lower(): (n, g) for n, g in entries_data(elegidas[src_key]['pak']) if '/UI/' in n}
        elif r['tipo'] == 'convertir':
            mod = {n.lower(): (n, g) for n, g in entries_data(elegidas[r['fuente']]['pak']) if '/UI/' in n}
            base = r['base']
        for folder, prefix in KINDS:
            stem = 'RED/Content/UI/' + folder + prefix + base
            src = mod if (stem + '.uasset').lower() in mod else game
            if (stem + '.uasset').lower() not in src: continue
            for ext in ('.uasset', '.uexp', '.ubulk'):
                k = (stem + ext).lower()
                if k not in src: continue
                data = src[k][1]()
                if ext == '.uasset':
                    rx = re.compile(re.escape(prefix) + base + '$', re.I)
                    data = rename_uasset(data, lambda s, rx=rx, prefix=prefix: rx.sub(prefix + code, s))
                files['RED/Content/UI/' + folder + prefix + code + ext] = data
        iconsrc = sorted(n for n in mod if re.search(r'/charaselect_s3/tex/cs_cicon\d\d\.uasset$', n))
        if iconsrc: src, stem = mod, iconsrc[0][:-len('.uasset')]
        else: src, stem = game, ('RED/Content/UI/CharaSelect_S3/tex/CS_CIcon%02d' % ICONO_JUEGO[base]).lower()
        leaf = src[stem + '.uasset'][0][:-len('.uasset')].split('/')[-1]
        for ext in ('.uasset', '.uexp', '.ubulk'):
            if stem + ext not in src: continue
            data = src[stem + ext][1]()
            if ext == '.uasset':
                data = rename_uasset(data, lambda s: s.replace('/CharaSelect_S3/tex/', '/CharaSelect_S3/%s/' % code))
            files['RED/Content/UI/CharaSelect_S3/%s/%s%s' % (code, leaf, ext)] = data
        if code != 'WRZ': icons.append((code, '/Game/UI/CharaSelect_S3/%s/%s.%s' % (code, leaf, leaf)))
    # export name must equal the file name (/Game/.../X.X); fix same-length code swaps
    for n in list(files):
        if not n.endswith('.uasset'): continue
        leaf = n.rsplit('/', 1)[1][:-len('.uasset')]
        ns = [s for s, *_ in names(files[n])]
        if leaf in ns: continue
        cand = [s for s in ns if not s.startswith('/') and len(s) == len(leaf) and s[:-3].lower() == leaf[:-3].lower()]
        if cand: files[n] = rename_uasset(files[n], lambda s, old=cand[0], leaf=leaf: leaf if s == old else (s[:-len(old)] + leaf if s.startswith('/') and s.endswith('/' + old) else s))
        else: log(t('  aviso UI: %s no tiene un objeto con su nombre', '  UI warning: %s has no object with its name') % n)
    write_pak(out, sorted(files.items()))
    return icons

# Base-game characters an output pak may touch. VGF is an unused leftover folder of the game (49
# files, no playable character) that the SSJ4 Vegeta download already builds on. Anything else
# means a wrong download was picked and would change an original character, so nothing is installed.
PERMITIDO_ORIGINALES = {'DBFZX_VGF.pak': {'VGF'}}

def proteger_originales(game_pak, paks_out):
    from inspect_pak import read_pak
    d = read_pak(game_pak); base = set()
    for e in d['entries']:
        m = re.search(r'(?:^|/)Chara/(\w{3})/', d['mount'] + e['name'])
        if m: base.add(m.group(1).upper())
    malos = []
    for pak in sorted(paks_out.glob('*.pak')):
        tocados = (set(pak_charas(pak)) & base) - PERMITIDO_ORIGINALES.get(pak.name, set())
        if tocados: malos.append(t('%s cambiaría a %s', '%s would change %s') % (pak.name, ', '.join(sorted(tocados))))
    if malos:
        raise RuntimeError(t('Seguridad: el resultado modificaría personajes originales del juego (', 'Safety: the result would change original game characters (') + '; '.join(malos) +
                           t('). Revisa que cada descarga sea la de la lista. No se ha instalado nada.',
                             '). Check that each download is the one on the list. Nothing was installed.'))
    log(t('Comprobado: ningún pak cambia a los personajes originales del juego.', 'Checked: no pak changes the original game characters.'))

def main():
    ap = argparse.ArgumentParser(description='Monta los extras desde tus descargas.')
    ap.add_argument('--descargas', required=True, nargs='+', help='carpeta(s) con los mods descargados (zip o descomprimidos)')
    ap.add_argument('--juego', default='D:/Games/Dragon Ball FighterZ')
    ap.add_argument('--salida', default=str(HERE / 'salida'))
    ap.add_argument('--solo', default='', help='códigos separados por comas (por defecto, los 14)')
    ap.add_argument('--sin-werezaru', action='store_true', help='EX Goku con su aspecto normal')
    ap.add_argument('--instalar', action='store_true', help='copiar el resultado al juego (con copia de seguridad)')
    ap.add_argument('--incluir-port', action='store_true', help='añadir UE4SS y el port incluidos al montaje para un juego sin mods')
    a = ap.parse_args()
    from comprobar_runtime import comprobar
    comprobar()
    juego = pathlib.Path(a.juego); os.environ['DBFZ_GAME'] = str(juego)
    game_pak = juego / 'RED/Content/Paks/pakchunk0-WinAnvil.pak'
    mods_dir = juego / 'RED/Content/Paks/~mods'
    assert game_pak.exists(), 'No encuentro el juego en %s (usa --juego)' % juego
    plantilla_sig = HERE.parent / 'Game/RED/Content/Paks/~mods/DBFZSlotsMask.sig'
    if not plantilla_sig.exists(): plantilla_sig = mods_dir / 'DBFZSlotsMask.sig'
    assert plantilla_sig.exists(), 'Falta la plantilla SIG: extrae el paquete completo, no solo tools.'
    solo = {c.strip().upper() for c in a.solo.split(',') if c.strip()}
    if solo - {c for c, _ in ROSTER}: ap.error('Códigos desconocidos: ' + ', '.join(sorted(solo - {c for c, _ in ROSTER})))
    roster = [(c, r) for c, r in ROSTER if not solo or c in solo]
    necesarias = set()
    for c, r in roster:
        necesarias.add(r['fuente'])
        if r.get('ui', (None,))[0]: necesarias.add(r['ui'][0])
        if r.get('aspecto') and not a.sin_werezaru: necesarias.add(r['aspecto'])

    salida = pathlib.Path(a.salida).resolve()
    if salida == juego.resolve() or juego.resolve() in salida.parents:
        ap.error('--salida debe estar fuera de la carpeta del juego; usa --instalar explícitamente para desplegar.')
    if salida.exists() and any(salida.iterdir()):
        ap.error('--salida debe ser una carpeta nueva o vacía para no mezclar montajes.')
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='dbfzx'))
    work = tmp / 'w'; (work / 'paks/chars').mkdir(parents=True)
    paks_out = salida / 'RED/Content/Paks/~mods'; paks_out.mkdir(parents=True, exist_ok=True)
    cfg_out = salida / 'RED/Binaries/Win64/ue4ss/Mods'
    try:
        if a.incluir_port:
            from instalar import preparar_port
            preparar_port(juego, salida)
        log(t('Buscando mods en', 'Looking for mods in'), ', '.join(a.descargas))
        elegidas, faltan = elegir(buscar(a.descargas, tmp), sorted(necesarias))
        if 'werezaru' in faltan:
            log(t('  Werezaru no está: EX Goku se queda con su aspecto normal.', '  Werezaru not found: EX Goku keeps its normal look.')); faltan.remove('werezaru')
        if faltan:
            log(t('\nDescargas ausentes (se omitirán los personajes que las necesitan):', '\nMissing downloads (the characters that need them will be skipped):'))
            for k in faltan:
                log(t('  - %s  (%s, archivo %s)', '  - %s  (%s, file %s)') % (k, FUENTES[k]['web'], FUENTES[k]['pak']))
        disponibles = []
        for code, r in roster:
            required = {r['fuente']}
            if r.get('ui', (None,))[0]: required.add(r['ui'][0])
            missing = required - elegidas.keys()
            if missing: log(t('  Omitido %s: falta %s', '  Skipped %s: missing %s') % (code, ', '.join(sorted(missing))))
            else: disponibles.append((code, r))
        roster = disponibles
        if not roster:
            raise RuntimeError(t('No hay ningún personaje completo para montar. Consulta las descargas indicadas arriba.', 'No complete character to build. Check the downloads listed above.'))
        for k, d in sorted(elegidas.items()): log('  %-11s %s' % (k, d['origen']))
        hecho = []

        import build_char as bc
        bc.root = work; bc.GAME_PAK = game_pak
        for code, r in roster:
            dest = paks_out / ('DBFZX_%s.pak' % code)
            log(t('Convirtiendo', 'Converting'), code, '...')
            sys.argv = ['build_char.py', code, r['base'], str(elegidas[r['fuente']]['pak'])] + r['args']
            bc.main()
            shutil.copy2(work / 'paks/chars' / ('DBFZX_%s.pak' % code), dest)
            shutil.copy2(plantilla_sig, dest.with_suffix('.sig')); hecho.append(dest)

        if {'SBG', 'GRN', 'GKG'} & {c for c, _ in roster}:
            import fix_preload_dependencies as fp
            fp.root = work; os.environ['DBFZ_SIG'] = str(plantilla_sig)
            fp.main(codes=tuple(c for c in ('SBG', 'GRN', 'GKG') if any(k == c for k, _ in roster)))
            for ext in ('.pak', '.sig'):
                shutil.copy2(work / 'paks/fixes' / ('zzDBFZSlotsPreloadFix' + ext), paks_out / ('zzDBFZSlotsPreloadFix' + ext))
            hecho.append(paks_out / 'zzDBFZSlotsPreloadFix.pak')

        if 'werezaru' in elegidas and any(c == 'EXG' for c, _ in roster):
            os.environ.update(DBFZ_WEREZARU=str(elegidas['werezaru']['pak']), DBFZ_EXG_DIR=str(paks_out), DBFZ_WORK=str(work))
            os.environ['DBFZ_SIG'] = str(plantilla_sig)
            runpy.run_path(str(HERE / 'build_werezaru_exg.py'), run_name='__main__')
            for ext in ('.pak', '.sig'):
                shutil.copy2(work / 'paks/werezaru-exg' / ('zzWerezaruEXG_P' + ext), paks_out / ('zzWerezaruEXG_P' + ext))
            hecho.append(paks_out / 'zzWerezaruEXG_P.pak')

        log(t('Textos (13 idiomas) ...', 'Texts (13 languages) ...'))
        import build_texts as bt
        bt.root = work
        bt.EXTRAS = {c: (r['texto'],) + r['names'] for c, r in roster}
        bt.MOD_TEXT = {}
        for c, r in roster:
            if r.get('textos') == 'json' and elegidas[r['fuente']]['text']: bt.MOD_TEXT[c] = ('json', elegidas[r['fuente']]['text'])
            elif r.get('textos') == 'pak': bt.MOD_TEXT[c] = ('pak', elegidas[r['fuente']]['pak'])
        bt.main()
        shutil.copy2(work / 'paks/DBFZSlotsText.pak', paks_out / 'DBFZSlotsText.pak')
        shutil.copy2(plantilla_sig, paks_out / 'DBFZSlotsText.sig'); hecho.append(paks_out / 'DBFZSlotsText.pak')

        log(t('Retratos e iconos ...', 'Portraits and icons ...'))
        icons = construir_ui(roster, elegidas, game_pak, paks_out / 'DBFZSlotsUI.pak')
        shutil.copy2(plantilla_sig, paks_out / 'DBFZSlotsUI.sig'); hecho.append(paks_out / 'DBFZSlotsUI.pak')

        (cfg_out / 'DBFZSlotsStore').mkdir(parents=True, exist_ok=True); (cfg_out / 'DBFZSlotsIcons').mkdir(parents=True, exist_ok=True)
        (cfg_out / 'DBFZSlotsStore/chara_mods.txt').write_bytes(''.join(c + '\r\n' for c, _ in roster).encode('ascii'))
        (cfg_out / 'DBFZSlotsIcons/icons.txt').write_bytes(''.join('%s %s\n' % i for i in icons).encode('ascii'))
        proteger_originales(game_pak, paks_out)
        reference = json.loads((HERE / 'reference-sha256.json').read_text(encoding='utf-8'))
        complete = len(roster) == len(ROSTER) and not a.sin_werezaru and 'werezaru' in elegidas
        partial_preload = not {'SBG', 'GRN', 'GKG'} <= {c for c, _ in roster}
        checks = {n: sha(salida / n) == h for n, h in reference.items()
                  if (salida / n).is_file() and not (partial_preload and pathlib.Path(n).name == 'zzDBFZSlotsPreloadFix.pak') and (complete or pathlib.Path(n).name not in
                  ('DBFZSlotsUI.pak', 'DBFZSlotsText.pak', 'chara_mods.txt', 'icons.txt'))}
        exact_sources = all(d['sha'] == PROBADO.get(k) for k, d in elegidas.items())
        informe = dict(fecha=datetime.datetime.now().isoformat(timespec='seconds'), roster=[c for c, _ in roster], descargas_ausentes=faltan,
                       fuentes={k: dict(origen=d['origen'], sha256=d['sha'], probada=d['sha'].startswith(PROBADO.get(k, '-')))
                                for k, d in elegidas.items()},
                       referencia=checks, fuentes_exactas=exact_sources,
                       salida={p.relative_to(salida).as_posix(): sha(p) for p in sorted((salida / 'RED').rglob('*')) if p.is_file()})
        (salida / 'informe-montaje.json').write_text(json.dumps(informe, indent=1), encoding='utf-8')
        if exact_sources and not all(checks.values()):
            raise RuntimeError(t('El resultado difiere de la referencia; no se instalará. Revisa informe-montaje.json y las versiones de Python/dependencias: ', 'The result differs from the reference; it will not be installed. Check informe-montaje.json and the Python/library versions: ') + ', '.join(n for n, ok in checks.items() if not ok))
        log(t('Comprobación SHA-256:', 'SHA-256 check:'), sum(checks.values()), '/', len(checks), t('archivos idénticos a la referencia pública.', 'files identical to the public reference.'))
        log(t('\nListo: %d paks en %s', '\nDone: %d paks in %s') % (len(hecho), paks_out))
        log('Roster:', ' '.join(c for c, _ in roster))

        if a.instalar:
            from instalar import instalar_salida
            instalar_salida(juego, salida)
            log(t('Abre el juego desde Inicio de Windows.', 'Start the game from the Windows Start menu.'))
        else:
            log(t('Para instalarlo, copia el contenido de la carpeta de salida sobre la del juego, o repite con --instalar.', 'To install it, copy the output folder over the game folder, or run again with --instalar.'))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == '__main__':
    main()
