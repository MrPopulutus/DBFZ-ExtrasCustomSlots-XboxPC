# The mod's DNA: what it is, what it does and how it works, step by step

**AI disclosure: this mod's code, tools and documentation were written with AI assistance (Claude by Anthropic and ChatGPT/Codex by OpenAI) under MrPopulutus' direction. It contains no AI-generated art, audio or voices.**

Microsoft Store / Xbox PC implementation with native patches, Lua modules and a local character converter. See CREDITOS.md for inspiration and contributions.

This document is for two kinds of people:

- **Those who won't run anything without knowing what it does.** Here is everything that happens on your PC, step by step: what is read, what is written, where and why. It also covers how to check it yourself and how to install by hand.
- **Those who want to understand it or build something bigger.** Here is the whole logic, where each piece comes from and where to change things. For the game's exact addresses and every patch, continue with `HOW-IT-WORKS.md`.

---

## 1. The idea in one paragraph

DBFZ has a fixed roster. Every character has a **number** (its ID, `0x00` to `0x2E`) and a **three-letter code** (`GKS` is Super Saiyan Goku, `VGS` Vegeta, `BDN` Bardock…). The code is the name of its folder in the game (`/Game/Chara/GKS/`), of its images and of its texts. Almost every character mod on GameBanana is a **replacement**: it overwrites an existing character's files (Sol Badguy, for example, replaces Yamcha). This mod does something else: **it gives each new character its own number (`0x31` to `0x3F`) and its own code**, and adds a **fourth row** to the select screen. You get up to **15 extra characters** without losing any original.

Four pieces make that work:

1. **An in-memory patch of the game** (`dbfzslots.dll`), so it accepts the new numbers.
2. **The select screen**: 4th-row icons, help bar and big portraits (modules `DBFZSlotsIcons` and `DBFZSlotsUIFix`).
3. **The cursor mask** (`DBFZSlotsMask.pak`), which says which character is under each point of the screen.
4. **The converted characters**: each mod's files copied and renamed to the new code. These are **not included**: the script builds them on your PC from each author's original download.

---

## 2. What is in the zip, file by file

| Folder or file | What it is | Made by |
|---|---|---|
| `INSTALAR.cmd` | Two lines: runs `tools\instalar.py` with the bundled Python and waits for a key at the end. Open it in Notepad to see. | This project |
| `LEEME-PRIMERO.txt` | Short instructions. | This project |
| `Game\` | What gets copied over the game folder. See the next table. | Mixed (see below) |
| `tools\` | Python scripts: installer, character build, converter, texts, portraits, preload repair, checks. All readable text. | This project |
| `tools\reference-sha256.json` | SHA-256 fingerprints of the tested result: the 18 paks and 2 configuration files you should get from the same downloads. | This project |
| `tools\technical-sha256.json` | Fingerprints of every file in `Game\`. The installer checks them before copying anything: if a file in the zip was changed, it stops. | This project |
| `source\` | C and assembly source of both DLLs, plus tests that run without the game. | This project |
| `runtime\python\` | Portable Python 3.12.14 for Windows (the official "embeddable" build) with Pillow, NumPy, etcpak, texture2ddecoder and archspec from PyPI. Only used to run the scripts; nothing is installed in Windows. | Python Software Foundation and each library's authors |
| `docs\` | This guide, the technical one (`HOW-IT-WORKS.md`), the long Spanish guide, tested versions and credits. | This project |
| `licenses\` | Licenses of third-party components. | — |

Inside `Game\RED\Binaries\Win64\`:

| File | What it does | Origin |
|---|---|---|
| `dwmapi.dll` | UE4SS loader. Windows loads it when the game starts because it sits in the game folder; it loads UE4SS. | Official UE4SS release (MIT) |
| `ue4ss\UE4SS.dll`, `UE4SS-settings.ini`, stock Lua modules | **UE4SS**, the open modding tool that runs code inside Unreal Engine games. | UE4SS team, unchanged (MIT) |
| `ue4ss\MemberVariableLayout.ini` | Engine structure sizes for this game build, which UE4SS needs. | This project |
| `ue4ss\Mods\mods.txt` | List of active modules. | This project |
| `ue4ss\Mods\DBFZSlotsStore\` | `dbfzslots.dll`, the slot patch, the Lua that loads it, and `chara_mods.txt`, the list of extra characters in order. | This project |
| `ue4ss\Mods\DBFZSlotsIcons\` | Lua that draws the 4th-row icons, plus `icons.txt`. | This project |
| `ue4ss\Mods\DBFZSlotsUIFix\` | `selector-ui.dll` (help bar at the top and big portraits), its `.ini` and Lua. | This project |

And in `Game\RED\Content\Paks\~mods\`: `DBFZSlotsMask.pak` (the cursor mask, an edited copy of a game file) and its `.sig`.

The installer includes an edited cursor-mask resource derived from the game. It does not include the game executable, the original game paks or character mod packages. Character assets are assembled from the user’s local downloads.

---

## 3. Exactly what happens when you open `INSTALAR.cmd`

Everything runs **offline**, **without administrator rights**, **without touching the Windows registry or installing services**. Until step 11, **your game is not modified**.

1. **The bundled Python starts** (`runtime\python\python.exe`), not your system's. It is configured (`python312._pth`) to use only its own folders.
2. **Language.** It reads the Windows display language: Spanish if Windows is in Spanish, English otherwise. You can force it with `DBFZ_LANG=es` or `DBFZ_LANG=en`.
3. **Game folder.** It asks for it and checks that `RED\Binaries\Win64\DRAGON_BALL_FighterZ.exe` is inside. If not, it asks again.
4. **Download folders.** It asks where your downloaded mods are (several allowed, separated by `;`) and checks they exist.
5. **Library check.** It creates a 4×4 image in memory, saves and reads it, and compresses it as a texture. If this fails, it stops before any heavy work.
6. **Game and package check.**
   - It fingerprints your `DRAGON_BALL_FighterZ.exe` (SHA-256) and compares it with the tested version. If it differs (another version, Steam…), **it stops**: the patches are only valid for that executable.
   - It fingerprints every file in `Game\` and compares it with `technical-sha256.json`. Missing or changed file → stop.
7. **Finding your downloads.**
   - It walks the folders you gave, subfolders included.
   - It opens `.zip` files with Python and `.rar`/`.7z` with the `tar.exe` that ships with Windows, extracting to a Windows temp folder (`%TEMP%\dbfzx…`), never inside your downloads.
   - For each `.pak` it checks **three things**: its name, which character folders it contains and its SHA-256. That is how it tells apart, for example, the right DIO download from another file with the same name.
   - Exact tested version found → it uses it. A single different version → used with a warning. Several different versions and none tested → that character is skipped with an explanation.
   - If something a character needs is missing, **that character is skipped** and you are told what to download and where. The others go ahead.
8. **It builds everything in a new folder** next to the extracted zip (`DBFZ-montaje-date`), **outside the game**:
   1. Copies `Game\` there. If you already had a `mods.txt`, it keeps your other lines and only sets the mod's four.
   2. **All 14 characters** are converted the same way: for each one it reads the base character's files **from your own game**, lays the mod's files over them and renames everything to the new code (section 5). The result is a new pak (`DBFZX_SBG.pak`, for example). Orange Piccolo, Beast Gohan, God Goku, SSJ4 Vegeta, Raditz, DIO, Yugi, Sol, Sukuna, Omega, Super Vegito, Granolah, SSJ3 Goku and EX Goku all go through this.
   3. **Preload repair** for Sol and Granolah (`zzDBFZSlotsPreloadFix.pak`): fixes an internal list that, in the original mods, left some materials and animations unloaded. Without it Sol crashed the game and Granolah froze in his Rolling Kick.
   4. **Werezaru** (optional): moves the Werezaru look onto EX Goku without changing his moves (`zzWerezaruEXG_P.pak`).
   5. **Texts:** reads the 13 language tables **from your game**, copies the base character's entries to the new code, sets the names and adds the mod's own texts (command list, assists). Result: `DBFZSlotsText.pak`.
   6. **Portraits and icons:** takes each mod's portraits (or the game's if the mod has none) and renames them to the new code. Raditz uses the game's own Bardock portraits and icon. Result: `DBFZSlotsUI.pak`.
   7. Writes `chara_mods.txt` and `icons.txt` with only the characters that were built, in order. Missing ones leave no gap.
9. **Safety brake.** It checks every resulting pak and makes sure **none changes any of the game's 85 original characters**. The one exception is `VGF`: an unused leftover folder in the game (no playable character) that the SSJ4 Vegeta download already builds on. If anything else would touch an original (for example, because the wrong mod was downloaded), **it stops and installs nothing**.
10. **Result check.** It compares the fingerprints with `reference-sha256.json`. With exactly the tested downloads, all 20 files must be byte-identical; if they are the tested downloads and something differs, it stops. It writes `informe-montaje.json` with everything: which download it used, their fingerprints and the result.
11. **It asks whether to install.** Enter → everything stays prepared in the build folder and **the game is not touched**. `Y` (or `S`) →
    - Checks the game is closed (a PowerShell command that only looks for the process).
    - **Backup:** saves every game file that will be overwritten to `copia-antes-de-montar-date`, verifying each copy by fingerprint, with a `manifest.json` list.
    - Files left by version 0.2.x under older names (old character paks, old mask, old roster file) are moved into that backup, so no character loads twice.
    - Copies the files into the game one by one and verifies each by fingerprint. If a copy fails, **it undoes everything it copied** and restores the previous files.
    - It never writes outside the game folder; this is checked file by file.
12. **Cleanup** of the Windows temp folder. Your downloads are not modified.

**Everything written to your PC:** the `DBFZ-montaje-date` folder and its `.log` (next to the extracted zip), a temp folder deleted at the end, and, only if you confirm, the mod's files in the game plus the backup folder.

---

## 4. What happens when you start the game

1. **Windows loads `dwmapi.dll`** from the game folder (it does that for any DLL with that name next to the executable). This loader starts **UE4SS**.
2. **UE4SS** reads `mods.txt` and runs the active modules in order. The ones that matter:
   - **`DBFZSlotsStore`**: its Lua loads `dbfzslots.dll`. The DLL checks the original bytes of **every** site it will change; if a single one differs it changes nothing and logs it. Otherwise it patches **in memory** (never the `.exe` on disk):
     - extends the number ↔ code table with the characters from `chara_mods.txt`;
     - extends the "screen point → character" table for the 4th row;
     - makes the game accept the new numbers as valid in selection, validation and battle setup.
   - **`DBFZSlotsIcons`**: when the select screen opens, draws one icon per extra character on top. It is only a picture; the mask decides what you select.
   - **`DBFZSlotsUIFix`**: loads `selector-ui.dll`, which:
     - moves the help bar to the top edge, only in character and colour select, so it does not cover the 4th row (height in `selector-ui.ini`);
     - loads the extras' big portraits a few seconds after start and keeps them in memory. The game only looked for portraits that were already loaded, which is why every extra used to show Super Saiyan Goku.
3. **The game** mounts every pak in `~mods` (characters, texts, portraits, mask) over its own, as with any mod.
4. **Logs** to see what happened: `ue4ss\dbfzslots.log`, `ue4ss\selector-ui.log`, `ue4ss\UE4SS.log`.

None of this connects to the internet. Everything was tested **offline**; online play has not been tested.

---

## 5. How a character gets its own slot

This is what `tools\build_char.py`, the heart of the build, does:

1. Takes **from the game** every file of the base character (`Chara/YMN/…` for Sol, who replaces Yamcha).
2. Lays the mod's files for that character over them.
3. **Renames** every path `/Game/Chara/YMN/` to `/Game/Chara/SBG/`, and the internal data names `BBS_YMN` and `COL_YMN` to `BBS_SBG` and `COL_SBG`. Codes are always 3 letters, so no name changes length and each file keeps its structure. It recomputes the name hashes the engine uses.
4. Mod files that belong **to other characters** are not copied, so those characters stay unchanged. If the mod needs them, they get their **own copy** under another code: Sukuna uses a copy of Whis (`WTN` → `URA`), Super Vegito one of Vegeta (`VGS` → `VGX`).
5. **New** shared files are kept; files that would overwrite the game's shared files are skipped, because they would change every character.
6. The mod's own extra folders (`SOL` for Sol, `YGI` for Yugi) are copied as they are.

Texts and portraits are built the same way: the base character's are copied under the new code and the mod's own are applied.

---

## 6. If you don't want to run anything

- **Read everything first:** `INSTALAR.cmd` and all of `tools\` are text. Open them in any editor. Search for `http`, `socket` or `urllib`: there is no network code.
- **Only what goes into the game:** you can copy the contents of `Game\` over the game folder by hand (first back up your `RED\Binaries\Win64\ue4ss` folder and your `~mods`). That gives you the slot system without running anything, but no characters: those are converted by the scripted build.
- **Check fingerprints:** in PowerShell, `Get-FileHash -Algorithm SHA256 <file>`. Compare with `tools\technical-sha256.json` (package files) and `docs\VERSIONES-PROBADAS.md` (tested downloads).
- **Build the DLLs yourself** from `source\` (`source\README.md`) and run the offline tests before using them.
- **Build without installing:** run `INSTALAR.cmd` and press Enter instead of `Y` at the end. Everything stays prepared in `DBFZ-montaje-date` for you to inspect and copy yourself.

---

## 7. Uninstalling

- **If you installed with the script:** with the game closed, copy the contents of `copia-antes-de-montar-date` over the game folder, then delete the files the mod added (all listed in its `manifest.json` with `existed: false`).
- **By hand:** with the game closed, delete `RED\Binaries\Win64\dwmapi.dll` and the `RED\Binaries\Win64\ue4ss` folder, and remove the mod's paks from `RED\Content\Paks\~mods` (`DBFZ*`, `zz*` and the character paks). The game is back to stock.
- Always start the game from the Start menu or the Xbox app; running the `.exe` directly gives a sign-in error.

---

## 8. Building something bigger

- **Full architecture, every patch with its address, porting to another build:** `HOW-IT-WORKS.md`.
- **Rules to change it without breaking it:** `../CONTRIBUTING.md`.
- **Add your own character:** convert its mod with `build_char.py CODE BASE mod.pak`, add its portraits and texts, and put its code in `chara_mods.txt` (15 max).
- **Current limits:** 15 slots, main select grid only; the extras' big portraits have no position data of their own in the game.
- **Ideas:** more slots (needs a bigger mask and tables and a review of every check), a roster picker, or the same technique on other Unreal Engine 4 games.

---

## 9. Glossary

- **Pak**: Unreal Engine container file with a game's or mod's assets. Paks in `~mods` load over the game's.
- **UE4SS**: open tool that runs Lua scripts and DLLs inside Unreal Engine games.
- **ID / code**: the number and three-letter name the game uses for each character.
- **Cursor mask**: invisible image where every point of the select screen holds a slot number.
- **Preload list**: internal list of what an asset needs loaded before it is used.
- **SHA-256 (fingerprint)**: number that identifies an exact file; change one byte and it changes.
- **RootSet**: engine flag that keeps an object from being unloaded from memory.

## 10. License and credits

This project's code, tools and docs are **MIT** (`LICENSE.txt`): use, change and share them, keeping the credit. The game and every character mod keep their authors and licenses; most are CC BY-NC-ND 4.0, so ask their authors before sharing adapted versions. Full credits with links: `CREDITOS.md`. Built with help from Claude (Anthropic) and ChatGPT/Codex (OpenAI).
