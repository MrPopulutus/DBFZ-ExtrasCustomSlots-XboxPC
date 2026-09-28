"""Offline installer. Made by MrPopulutus."""
import sys as _sys, pathlib as _pl; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from idioma import t
import datetime, hashlib, json, os, pathlib, shutil, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
EXE_SHA = "6752c39a27ccfe1bbfc4a66c9da9dcdd3f80db0b25b15ebc3923f54c95ee1b3d"
# Files left by versions up to 0.2.3 under other names; moved to the backup when their
# replacement is installed. old pak name -> code it held (now DBFZX_<code>.pak)
RETIRADOS = {'OrangePiccolo.pak': 'PCO', 'BeastGohanCustomSlot.pak': 'GHB', 'GodGoku.pak': 'GKG',
             'SS4VegetaMoveset.pak': 'VGF', 'RaditzMoveset.pak': 'RDN', 'DIOCharacterMoveset.pak': 'DIO'}
# old path -> new path that replaces it
RENOMBRADOS = {'RED/Content/Paks/~mods/DBFZCSelectStore.pak': 'RED/Content/Paks/~mods/DBFZSlotsMask.pak',
               'RED/Content/Paks/~mods/DBFZCSelectStore.sig': 'RED/Content/Paks/~mods/DBFZSlotsMask.sig',
               'RED/Binaries/Win64/ue4ss/Mods/DBFZCharaSelect/chara_mods.txt': 'RED/Binaries/Win64/ue4ss/Mods/DBFZSlotsStore/chara_mods.txt'}

def digest(path):
    with path.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def preparar_port(game, output):
    exe = game / 'RED/Binaries/Win64/DRAGON_BALL_FighterZ.exe'
    if not exe.exists() or digest(exe) != EXE_SHA:
        raise RuntimeError(t('Esta version del ejecutable no coincide con la version Xbox/Store comprobada. No se instala.', 'This game executable is not the tested Xbox/Store version. Nothing is installed.'))
    source = ROOT / 'Game'
    for name, expected in json.loads((ROOT / 'tools/technical-sha256.json').read_text()).items():
        p = ROOT / name
        if not p.is_file() or digest(p) != expected: raise RuntimeError(t('Archivo tecnico ausente o alterado: ', 'Package file missing or altered: ') + name)
    shutil.copytree(source, output, dirs_exist_ok=True)
    # Retain other enabled modules when updating an existing setup.
    current = game / 'RED/Binaries/Win64/ue4ss/Mods/mods.txt'
    target = output / 'RED/Binaries/Win64/ue4ss/Mods/mods.txt'
    if current.exists():
        import re
        text = current.read_text(encoding='utf-8-sig')
        # UE4SS's sample modules run Lua on every map change and are not needed by this mod.
        samples = ['CheatManagerEnablerMod','ConsoleCommandsMod','ConsoleEnablerMod','LineTraceMod','BPML_GenericFunctions','BPModLoaderMod']
        for mod, value in [('DBFZSlotsStore',1),('DBFZSlotsIcons',1),('DBFZSlotsUIFix',1)] + [(m, 0) for m in samples]:
            pattern = r'(?m)^' + mod + r'\s*:\s*\d+.*$'
            line = mod + ' : ' + str(value)
            text = re.sub(pattern, line, text) if re.search(pattern,text) else text.rstrip() + '\n' + line + '\n'
        text = re.sub(r'(?m)^DBFZCharaSelect\s*:\s*\d+.*\n?', '', text)   # line left by versions up to 0.2.3
        target.write_text(text,encoding='utf-8')

def instalar_salida(game, output):
    game, output = game.resolve(), output.resolve()
    if os.name == 'nt':
        powershell = pathlib.Path(os.environ.get('SystemRoot','C:/Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        result = subprocess.run([str(powershell), '-NoProfile', '-Command',
                                 "if (Get-Process -Name 'DRAGON_BALL_FighterZ' -ErrorAction SilentlyContinue) { exit 42 } else { exit 0 }"],
                                creationflags=0x08000000)
        if result.returncode == 42: raise RuntimeError(t('Cierra el juego antes de instalar.', 'Close the game before installing.'))
        if result.returncode: raise RuntimeError(t('No se pudo comprobar si el juego está cerrado; no se instala.', 'Could not check that the game is closed; nothing is installed.'))
    backup = output.parent / ('copia-antes-de-montar-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    changes = []
    for source in sorted((output / 'RED').rglob('*')):
        if not source.is_file(): continue
        relative = source.relative_to(output)
        destination = game / relative
        if not destination.resolve().is_relative_to(game): raise RuntimeError(t('Destino fuera del juego.', 'Destination outside the game folder.'))
        existed = destination.exists()
        if existed:
            saved = backup / relative
            saved.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(destination,saved)
            if digest(saved) != digest(destination): raise RuntimeError(t('No se pudo verificar la copia anterior.', 'Could not verify the backup copy.'))
        changes.append(dict(path=relative.as_posix(),existed=existed,sha256=digest(source)))
    # Paks left by versions up to 0.2.3 under other names, holding the same new codes the
    # DBFZX_ paks now build; with both in ~mods the game would load two copies of a character.
    retired = []
    mods = game / 'RED/Content/Paks/~mods'
    if (output / 'RED/Content/Paks/~mods').is_dir():
        from montar_extras import pak_charas
        for name, code in RETIRADOS.items():
            old = mods / name
            if not old.is_file() or not (output / 'RED/Content/Paks/~mods' / ('DBFZX_%s.pak' % code)).is_file(): continue
            if code not in pak_charas(old): continue
            for f in (old, old.with_suffix('.sig')):
                if not f.is_file(): continue
                relative = f.relative_to(game)
                saved = backup / relative
                saved.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(f,saved)
                if digest(saved) != digest(f): raise RuntimeError(t('No se pudo verificar la copia anterior.', 'Could not verify the backup copy.'))
                retired.append(dict(path=relative.as_posix(),removed=True))
    for old, new in RENOMBRADOS.items():
        if not (game / old).is_file() or not (output / new).is_file(): continue
        saved = backup / old
        saved.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(game / old,saved)
        if digest(saved) != digest(game / old): raise RuntimeError(t('No se pudo verificar la copia anterior.', 'Could not verify the backup copy.'))
        retired.append(dict(path=old,removed=True))
    backup.mkdir(parents=True,exist_ok=True)
    (backup/'manifest.json').write_text(json.dumps(changes + retired,indent=2),encoding='utf-8')
    for item in retired:
        (game / item['path']).unlink()
        print(t('Retirado (queda en la copia): ', 'Retired (kept in the backup): ') + item['path'])
    written = []
    try:
        for item in changes:
            relative = pathlib.Path(item['path']); destination = game / relative
            destination.parent.mkdir(parents=True,exist_ok=True)
            written.append(item)
            shutil.copy2(output/relative,destination)
            if digest(destination) != item['sha256']: raise RuntimeError(t('No coincide la copia: ', 'Copy does not match: ') + item['path'])
    except Exception:
        for item in reversed(written):
            destination = game / item['path']
            if item['existed']: shutil.copy2(backup/item['path'],destination)
            elif destination.exists(): destination.unlink()
        for item in retired: shutil.copy2(backup/item['path'], game/item['path'])
        raise
    print(t('Instalado. Copia anterior:', 'Installed. Previous files backed up in:'),backup)
    print(t('Abre el juego desde Inicio de Windows.', 'Start the game from the Windows Start menu.'))

GAME_EXE = 'RED/Binaries/Win64/DRAGON_BALL_FighterZ.exe'
def pedir_juego():
    # Asks until the folder holds the game. Enter only works when the usual folder really has it.
    usual = pathlib.Path('D:/Games/Dragon Ball FighterZ')
    print()
    print(t('Escribe la carpeta donde esta instalado el juego (la que contiene la carpeta RED).', 'Type the folder where the game is installed (the one that contains the RED folder).'))
    print(t('Ejemplo: ', 'Example: ') + r'D:\Games\Dragon Ball FighterZ')
    found = (usual / GAME_EXE).exists()
    if found: print(t('He encontrado el juego en %s: pulsa Enter para usar esa carpeta.', 'Game found in %s: press Enter to use that folder.') % usual)
    while True:
        text = input(t('Carpeta del juego: ', 'Game folder: ')).strip().strip('"')
        if not text and found: return usual
        folder = pathlib.Path(text)
        if text and (folder / GAME_EXE).exists(): return folder
        print(t('  No encuentro DRAGON_BALL_FighterZ.exe en esa carpeta. Revisa la ruta y prueba otra vez.', '  DRAGON_BALL_FighterZ.exe is not in that folder. Check the path and try again.'))

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Instalador completo de DBFZ Custom Slots')
    parser.add_argument('--juego')
    parser.add_argument('--descargas', nargs='+')
    args = parser.parse_args()
    print('DBFZ Custom Slots - Made by MrPopulutus')
    print(t('No necesitas instalar Python, UE4SS ni librerias. Solo tus descargas de personajes.', 'You do not need to install Python, UE4SS or libraries. Only your character downloads.'))
    game = pathlib.Path(args.juego) if args.juego else pedir_juego()
    print()
    print(t('Ahora la carpeta (o carpetas) donde tienes los mods de personajes descargados.', 'Now the folder (or folders) with your downloaded character mods.'))
    print(t('Pueden estar en cualquier sitio; si son varias, separalas con ;', 'They can be anywhere; separate several folders with ;'))
    print(t('Ejemplo: ', 'Example: ') + t(r'C:\Users\tu-usuario\Downloads\Mods DBFZ', r'C:\Users\your-name\Downloads\DBFZ mods') + r';E:\Unverum\Mods\Dragon Ball FighterZ')
    downloads = args.descargas or [p.strip().strip('"') for p in input(t('Carpeta(s) de descargas: ', 'Download folder(s): ')).split(';') if p.strip().strip('"')]
    if not downloads or any(not pathlib.Path(p).is_dir() for p in downloads): raise RuntimeError(t('Indica carpetas de descargas existentes.', 'Give download folders that exist.'))
    output = ROOT.parent / ('DBFZ-montaje-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    script = ROOT / 'tools/montar_extras.py'
    logfile = output.with_suffix('.log')
    print(t('Registro completo:', 'Full log:'), logfile, flush=True)
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1')
    with logfile.open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable,'-B','-u',str(script),'--descargas',*downloads,'--juego',str(game),'--salida',str(output),'--incluir-port'],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding='utf-8', errors='replace', env=env)
        for line in process.stdout:
            print(line, end='', flush=True)
            log.write(line)
            log.flush()
        code = process.wait()
    if code: raise RuntimeError(t('El montaje fallo. No se ha instalado nada. Registro: ', 'The build failed. Nothing was installed. Log: ') + str(logfile))
    print(t('Montaje preparado y comprobado en:', 'Build ready and checked in:'),output)
    if input(t('Instalar ahora? Escribe S o pulsa Enter para dejarlo preparado: ', 'Install now? Type Y, or press Enter to leave it prepared: ')).strip().lower() in ('s', 'si', 'y', 'yes'): instalar_salida(game,output)

if __name__ == '__main__':
    try: main()
    except (Exception,KeyboardInterrupt) as exc:
        print(t('No se completo:', 'Not completed:'),exc)
        sys.exit(1)
