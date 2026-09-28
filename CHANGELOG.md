# Changelog

## 0.3.4 (2026-09-28)

- God Goku: the red dragon of his ultimate now shows correctly. The download recolours the game's Shenron; the installer now gives God Goku his own copy of Shenron (code SRX) with those colours, so the original Shenron is untouched.
- God Goku no longer crashes the game when picked quickly ("Missing Dependency ... MI_DecalBody"): his colour materials get the same preload-list repair as Sol (`fix_preload_dependencies.py`).

## 0.3.3 (2026-09-28)

- Fixed the crash when opening character select a second time (after a match, a rematch, or just leaving and coming back). The cause was the 4th-row icon images: the game unloaded them when leaving the select screen, and the next screen picked one up while it was being destroyed. `dbfzslots.dll` now keeps the icon images loaded for the whole session, as it already did for the big portraits.
- The icon module finds the select screen with `FindObjects`, which skips objects being destroyed, and adds the icons about 0.3 s after the screen opens.

## 0.3.2 (2026-09-28)

- Fixed the crash when a rematch goes back to character select (0.3.1 was not enough). The 4th-row icon module no longer listens to every new object in the game: `selector-ui.dll` now counts the select screen's portrait lookups (`selector_ui_select_seen`) and the module polls that number twice a second, then looks the icon lists up with `FindAllOf`.
- UE4SS's sample modules (CheatManagerEnabler, ConsoleCommands, ConsoleEnabler, LineTrace, BPML_GenericFunctions, BPModLoader) are now off: they ran Lua on every map change and the mod does not need them. The installer switches them off on updates too.

## 0.3.1 (2026-09-28)

- Fixed a crash at the end of Versus matches: the 4th-row icon module kept a reference to a select-screen widget for 250 ms, and the game can destroy that widget in that time. It now looks the widget up again each time instead of keeping it.

## 0.3.0 (2026-09-27)

- Standalone: the mod depends on no other mod. The six characters that used to be taken ready-made from another download (Orange Piccolo, God Goku, SSJ4 Vegeta, Raditz, DIO, Beast Gohan) are now built on your PC by this project's own converter, from their original authors' downloads, like the other eight. Raditz now uses the Raditz moveset download (RCBurrito).
- Own names for everything: the roster list moved to `ue4ss/Mods/DBFZSlotsStore/chara_mods.txt` (both DLLs rebuilt to read it there) and the cursor mask is now `DBFZSlotsMask.pak`.
- Updating from 0.2.x: the installer moves the old files (the six old character paks, the old mask and the old roster file) into its backup, so no character is loaded twice.
- Documentation and page texts rewritten to match.

## 0.2.3 (2026-09-27)

- Removed the AI-generated Raditz art: Raditz now uses the game's own Bardock portraits and icon. The package contains no AI-generated art, audio or voices.
- Presented as an independent mod inspired by Custom Character Slots (no code from it is included), with an AI-assistance disclosure for the code.

## 0.2.2 (2026-09-27)

- Installer messages in English or Spanish, following the Windows language (`DBFZ_LANG` forces one).
- Clearer game-folder prompt with an example; it asks again until the folder really holds the game.
- Safer detection of downloads: files with the same name are no longer mixed up, and a final check refuses to install anything that would change an original character.
- New `docs/MOD-DNA.md` / `docs/ADN-DEL-MOD.md`: everything the installer and the mod do, step by step.
- Less stutter: the 4th-row icon module waits for the select screen to be created instead of scanning every game object once a second (also during matches).
- The extras' big portraits are loaded once, a few seconds after the game starts, and kept in memory, so entering character select no longer stops to load them.

## 0.2.1 (2026-09-27)

- Developer documentation: `docs/HOW-IT-WORKS.md` (architecture, every patch and address, conversion pipeline, porting to Steam) and `CONTRIBUTING.md`. No code changes.

## 0.2 (2026-09-26)

- New `DBFZSlotsUIFix` module (`selector-ui.dll`):
  - The help bar (announcement and button guide) is drawn at the top of character and colour select, so it no longer covers the 4th row. Height is set in `selector-ui.ini`.
  - Extras now show their own big portrait instead of Super Saiyan Goku. The game only looked the texture up among loaded objects; the module loads the extras' portraits when the selector opens.
- Reference setup: Sol no longer closes the game and Granolah's Rolling Kick (214+B) animates, thanks to the preload-list repair (`tools/fix_preload_dependencies.py`). Sukuna's Black Flash is 623 + L/M/H.
- Werezaru is now an appearance of EX Goku (EXG), keeping EX Goku's moves; Daima Goku is back to normal.
- Checked compatible with Accurate Destructive Finish.
- Source, tests, tools, full guide, credits and MIT license for MrPopulutus' own work.

## 0.1

- First Store port: `dbfzslots.dll` (IDs `0x31`–`0x3F`, selector, validity, battle setup), 4th-row icons (`DBFZSlotsIcons`), Store selector mask and UE4SS structure offsets.

### Montaje local verificado

- Montaje desde ZIP y carpetas originales, con SHA-256 completo de las fuentes y referencia automática de 20 archivos.
- Yugi conserva las referencias YGI originales; Gohan usa la compresión histórica y coincide byte a byte.
- Rutas e iconos históricos reproducidos; Raditz usa los retratos de Bardock del juego.
- Personajes ausentes opcionales, Werezaru opcional y precargas independientes de Sol/Granolah.
- No se incluyen movesets. Modified by MrPopulutus.

### Instalación desde cero

- INSTALAR.cmd con Python portátil, librerías, UE4SS y cargador incluidos.
- Firma del port incluida: ya no exige una instalación previa.
- Montaje y comprobación fuera del juego; instalación solo tras confirmar, con respaldo y reversión ante fallo de copia.
- Lectura de RAR/7z mediante el componente integrado de Windows. Solo los personajes se buscan aparte.
