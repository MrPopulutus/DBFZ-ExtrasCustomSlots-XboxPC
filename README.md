# DBFZ Custom Slots for Microsoft Store / Xbox PC

Modified by MrPopulutus.

Adds a fourth row with up to 15 extra character slots to the tested Microsoft Store build of DRAGON BALL FighterZ. The current conversion recipes cover 14 characters; character downloads are supplied separately by the user.

Inspired by [WistfulHopes’ Custom Character Slots](https://gamebanana.com/mods/596230) for Steam. This project targets Microsoft Store / Xbox PC, which that release did not support. The current installer does not require installing the Steam slot mod. See [credits](CREDITOS.md) and [provenance notes](PROVENANCE.md).

The code, tools and documentation were developed with Claude and ChatGPT/Codex under MrPopulutus’ direction. AI assistance is disclosed here and in the credits.

## Build the DLLs

On Windows, install Zig or make its `zig` executable available on PATH, then run `build.cmd`. The fallback is `python -m ziglang` if that package is installed. Outputs are `out/dbfzslots.dll`, `out/selector-ui.dll` and `tests/selector_ui_test.exe`.

The source repository does not contain the portable runtime, UE4SS binaries, game-derived cursor mask or character downloads. It is not the one-click installer. The conversion and installation scripts expect the complete package layout, including `Game/` and its signature template. Copying this repository alone will not supply those inputs.

Target executable SHA-256: `6752c39a27ccfe1bbfc4a66c9da9dcdd3f80db0b25b15ebc3923f54c95ee1b3d`. Runtime target: UE4SS v3.0.1. Native hooks check expected bytes before applying patches. The target executable is not included.

## Find the code

| Path | Purpose |
|---|---|
| `src/` | Character IDs, validity checks, battle setup, selection bar and portrait loading. |
| `lua/` | Loads the native modules and adds fourth-row icons. |
| `config/` | Roster, icon paths and settings for the tested game build. |
| `tools/` | Local character conversion, asset checks and installer scripts. |
| `tests/` | Checks using an executable mapped without launching the game. Some diagnostic helpers require local fixtures. |

Read [CODE-WALKTHROUGH.md](CODE-WALKTHROUGH.md) for the implementation, [HOW-IT-WORKS.md](HOW-IT-WORKS.md) for addresses and [MOD-DNA.md](MOD-DNA.md) for the complete installer’s operation. Español: [RECORRIDO-DEL-CODIGO.md](RECORRIDO-DEL-CODIGO.md) y [ADN-DEL-MOD.md](ADN-DEL-MOD.md).

## Scope and licensing

Experimental, tested offline on one PC. Only the main character grid is extended. Open the game from Windows Start; close it before changing installed files. Offline checks do not establish gameplay compatibility for every character, colour or move.

[LICENSE.txt](LICENSE.txt) applies to contributions the contributor is entitled to license. Game assets, character mods and dependencies retain their own rights and licenses. Character packages and generated conversions are not included in this source repository.

## Español

Código y herramientas para Microsoft Store / Xbox PC. La inspiración fue el mod de espacios de WistfulHopes para Steam; el instalador actual no requiere instalarlo. Este repositorio contiene el código, no el instalador completo. Para compilar las DLL usa `build.cmd`; para montar personajes, las herramientas necesitan la estructura del paquete completo y tus descargas originales. Consulta los créditos y las notas de procedencia antes de redistribuir material de terceros.
