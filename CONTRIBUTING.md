# Contributing and modifying

Standalone mod by MrPopulutus: its own code, with no dependency on any other mod. You can change, fork and redistribute MrPopulutus' code and docs under the MIT license (`LICENSE.txt`). Keep the credit line.

## Start here

1. `docs/HOW-IT-WORKS.md`: the architecture. It covers every native patch with its address, the Lua modules, the cursor mask, how characters are converted, and how to port it to another build.
2. `source/README.md`: building both DLLs and running the offline tests.
3. `tools/README.md`: the build script (`montar_extras.py`) and every helper.
4. `docs/GUIA-COMPLETA.md`: the long guide in Spanish, with the full history and troubleshooting.

## Repository layout

| Path | Contents |
|---|---|
| `source/src/` | `dbfzslots.c` + `caves.S` (slots), `selector_ui.c` + `selector_ui.S` (help bar, portraits) |
| `source/test/` | Offline harnesses that map the game executable without running it |
| `tools/` | Python: pak reader/writer, character converter, text/UI builders, preload repair, the one-command builder and its reference hashes |
| `Game/` | What gets copied over the game: UE4SS modules, configuration, selector mask (`DBFZSlotsMask.pak`) |
| `runtime/` | Portable Python, libraries and UE4SS used by `INSTALAR.cmd` |
| `docs/` | Architecture, Spanish guide, tested versions, credits |

## Rules that keep it working

- **Never remove the byte checks.** Every patch compares the original bytes before writing. On another build, find the sites again (HOW-IT-WORKS §9) and update the tables.
- **Test offline before the game.** Build, run `selector_ui_test.exe` / `harness.exe` against the executable, then launch the game from the Windows Start menu and read `ue4ss/dbfzslots.log`, `ue4ss/selector-ui.log` and `UE4SS.log`.
- **Keep the reference reproducible.** If you change a tool, `montar_extras.py` must still match `tools/reference-sha256.json`. If you change the output on purpose, update the hashes and say why in `CHANGELOG.md`.
- **Do not redistribute other people's characters** unless their authors allow it. Most are CC BY-NC-ND 4.0. Ship scripts that build them from the original downloads instead.
- Log changes in `CHANGELOG.md` with a version number, and credit the original authors of anything you reuse.

## Reporting a bug

Include the game version (Store/Xbox or Steam), the roster (`chara_mods.txt`), the character, colour, mode and exact input, a screenshot or clip, and the relevant lines of the three logs. Remove personal information first.
