# How it works: Custom Character Slots for the Microsoft Store build

**AI disclosure: this mod's code, tools and documentation were written with AI assistance (Claude by Anthropic and ChatGPT/Codex by OpenAI) under MrPopulutus' direction. It contains no AI-generated art, audio or voices.**

Microsoft Store / Xbox PC implementation with native patches, Lua modules and a local character converter. See CREDITOS.md for inspiration and contributions.

This document is for modders who want to change the mod, port it to another build (a future patch, another edition) or reuse parts of it. It explains every moving part, where it lives in the game and in this package, and how to find each part again in a different executable. A longer Spanish guide with the same material and more history is in `GUIA-COMPLETA.md`.

All addresses below are **RVAs** (offsets from the image base) in the tested Microsoft Store executable:

- `DRAGON_BALL_FighterZ.exe`, 73 082 880 bytes, SHA-256 `6752c39a27ccfe1bbfc4a66c9da9dcdd3f80db0b25b15ebc3923f54c95ee1b3d`.
- UE4SS v3.0.1 Beta #0 (Git 7bb156c, `LessEqual421__Shipping__Win64`), loaded through `dwmapi.dll`.

**They are only valid for that exact file.** Both DLLs compare the original bytes of every site before writing anything, and apply nothing if one differs. Never disable those checks to "make it work" on another build; find the sites again (section 9).

---

## 1. The big picture

DBFZ has a fixed roster. Every character has:

- a **character ID** (`ECharaID`, one byte): `0x00`–`0x2E` are real characters, `0x2F` is `DMY` (dummy) and `0x30` is `MAX`/none;
- a **three-letter code** (`GKS`, `VGS`, `BDN`…) that names its folder `/Game/Chara/<CODE>/`, its UI textures and its text keys.

A "replacement" mod overwrites a base character's files (for example Sol Badguy replaces Yamcha, `YMN`). This mod instead gives each extra character **a new ID (`0x31`–`0x3F`) and its own code**, so it sits in a new slot and the base character stays untouched.

Four things have to change for that to work:

| Layer | What changes | Where |
|---|---|---|
| Native code | ID↔code tables, selector grid lookups, "is this a real character" checks, battle setup | `dbfzslots.dll` (`DBFZSlotsStore`) |
| Selector UI | 4th-row icons, help bar position, big portraits | Lua `DBFZSlotsIcons`, `selector-ui.dll` (`DBFZSlotsUIFix`) |
| Cursor mask | Which pixel of the select screen maps to which slot | `DBFZSlotsMask.pak` |
| Character assets | The character's files copied and renamed to the new code | `DBFZX_<CODE>.pak` and friends, built locally by `tools/montar_extras.py` |

Runtime order at game start: UE4SS loads the Lua mods listed in `ue4ss/Mods/mods.txt`. `DBFZSlotsStore/Scripts/main.lua` loads `dbfzslots.dll` with `package.loadlib` and calls `luaopen_dbfzslots`, which patches the running executable in memory. `DBFZSlotsIcons` then waits for the selector widget and adds the icons. `DBFZSlotsUIFix` loads `selector-ui.dll`. Nothing is written to the executable on disk.

---

## 2. The roster file

`ue4ss/Mods/DBFZSlotsStore/chara_mods.txt`: one code per line, ASCII, no BOM. Line 1 becomes ID `0x31`, line 2 `0x32`, and so on, up to 15 lines. The order is also the order of the 4th row. Both DLLs and the icon module read this same file.

`ue4ss/Mods/DBFZSlotsIcons/icons.txt`: `CODE /Game/.../Texture.Texture` per line, the select icon for each code.

---

## 3. `dbfzslots.dll`: the native patches

Source: `source/src/dbfzslots.c` (patch logic) and `source/src/caves.S` (assembly caves). Log: `ue4ss/dbfzslots.log` (`installed: N extras (0x31..0x3N)`).

### 3.1 Technique

- **Near memory.** The DLL reserves a 64 KB block within ±2 GB of the executable (`near_alloc_init`), so a 5-byte `jmp rel32` from game code can reach it.
- **Hooks.** `hook(rva, n, cave)` writes `jmp rel32` to a 14-byte stub in near memory (`jmp qword ptr [rip+0]` + absolute address), which jumps to the cave in the DLL. The overwritten bytes are padded with `nop`.
- **Caves** reproduce the overwritten instructions and end in `jmp qword ptr [g_t + 8*i]`, where `g_t[]` holds the absolute game addresses to return to (the "OK" and "BAD" branches of the original compare).
- **RIP retargeting.** For tables, the DLL copies the game's table into near memory, extends it, and rewrites the 32-bit displacement of the `lea reg, [rip+table]` that reads it (`retarget_rip`).

### 3.2 Patch list

| # | RVA | Original | Change |
|---|---|---|---|
| 1 | `0x57EE00` IdToCode, `0x57EF00` CodeToId | table of 48 `{int32 id, int32 pad, wchar_t* code}` at `0x30AFBF0`; `lea rsi,[table]` at `0x57EE26`, `cmp ecx,0x30` at `0x57EE3A`; `lea r15,[table+8]` at `0x57EF31`, `cmp r14d,0x30` at `0x57EFFD`, `lea rcx,[table]` at `0x57F019` | Table copied, extras appended, the three `lea` retargeted, both counts set to `48 + N`. |
| 2 | Mask ID → character ID | two byte tables at `0x41E7510` (0x2D entries) and `0x41E75B8` (0x26 entries), bound-checked with `cmp dl,0x2D/0x26` | Tables copied into 64-byte buffers; mask IDs 45–59 map to `0x31…`; bounds raised to `0x2D + 15`. Sites: `0x455CAE/0x455CBC`, `0x455C1E/0x455C2C`, `0x454B97/0x454BA6`, `0x454857/0x454866`. |
| 3 | `0x587830` IsCharaValid(`ecx`) | prologue | Cave returns true for `0x31 ≤ id < 0x31+N`, else runs the original. |
| 4 | "real character" checks | `cmp reg,0x2F / jge bad`, `cmp reg,0x2E / jg skip`, `cmp al,0x30 / jb ok` … | Caves accept "id ≤ 0x2E **or** extra". Hover/confirm: `0x453F3F`, `0x453F80`, `0x4541DF`, `0x454220`. Stored ID sanity: `0x74F5A0`, `0x74C4A3`. Team member count at battle setup: `0x5D4810`, `0x5D4818`, `0x5D481F`. Battle setup: `0x5D5436`, `0x5D5605`, `0x5CFF1B`. |
| 5 | `0x5A9783`, `0x5A97AE` battle setup fill | `cmp eax,0x30` turned IDs ≥ `0x30` into `DMY` | Extras accepted. |
| 6 | Diagnostics | `0x5D4804` (log team IDs), `0x4A69D0` LoadObject (log and survive an empty path instead of aborting), `0x58E830/0x58E850` setup setters (log side/member/ID) | Logging only. |

Not patched on purpose: the list-based selectors at `0x74DDE0` / `0x72E2F0` (not the main grid) hold 48 entries, so extras only appear in the main character grid.

`MAX_EXTRAS` is 15 because IDs must stay a byte below the next sentinel range used by the game and the mask IDs 45–59 are what the 4th row provides. Raising it needs new mask regions, bigger tables and a check of every site above.

### 3.3 UE4SS structure offsets

The Store build has 24-byte `TArray`/`FString`, so several engine structs are 16 bytes bigger than UE4SS assumes. `ue4ss/MemberVariableLayout.ini` gives the measured offsets (`UStruct`, `UFunction`, `UEnum`). Without it, Lua calls into UMG (used by the icon module) crash or misbehave.

---

## 4. The 4th-row icons (`DBFZSlotsIcons`)

`Scripts/main.lua` polls `selector_ui_select_seen` in `selector-ui.dll` twice a second; it reports new portrait lookups by the select screen. Then the module finds the live `BP_CharaSelect_IconList_C` in the transient package with `FindObjects` (banned flags skip objects being destroyed), retrying every 250 ms until its `Icon01` slot exists. `dbfz_load_icons` keeps the icon textures in memory for the whole session (RootSet), so a later select screen never gets one being destroyed. (Up to 0.3.1 it listened to every new `UserWidget` with `NotifyOnNewObject`; that crashed the game when screens were torn down after a match. Version 0.2 polled with `FindAllOf` every second, which scanned every object even during matches; that is kept only as a fallback if `selector-ui.dll` is missing.) For each roster code it:

1. calls `dbfz_load_icons` in `dbfzslots.dll`, which loads every texture in `icons.txt` with the game's own loader (`0x4A69D0`; UE4SS `LoadAsset` does not work on this build);
2. finds the texture with `StaticFindObject`, creates a UMG `Image`, `SetBrushFromTexture`, `HitTestInvisible`, and adds it to the same canvas as the game's icons;
3. places it with `CENTERS` (mask-space centres of the 15 slots) converted to canvas units: `X*3`, `Y*3+256`, size 256×256, alignment 0.5, ZOrder 3.

The icons are only a picture. Selection comes from the cursor mask (section 6).

---

## 5. `selector-ui.dll` (`DBFZSlotsUIFix`)

Source: `source/src/selector_ui.c` and `.S`. Log: `ue4ss/selector-ui.log`. Settings: `selector-ui.ini`.

### 5.1 Help bar at the top

The two lines at the bottom of character and colour select are drawn natively, in 1280×720 units:

| Line | Function | Site | Original bytes |
|---|---|---|---|
| Button guide | `0x5C9660` | `0x5C98CE` | `f3 0f 58 35 82 04 b1 02` = `addss xmm6, [764.0]` |
| Announcement + its background | `0x5C9EF0` | `0x5CA236` | `f3 44 0f 58 05 19 fb b0 02` = `addss xmm8, [764.0]` |

Y = 764 − animation × 140 (+29 for the guide; the background is drawn at Y+9, 64 high). The patch jumps to a cave that does the original `addss` and then subtracts `shift` **only when** the announcement singleton (RVA `0x46FA450`, returned by `0x5BB870`) is shown (`+0x00 == 1`) and its ASCII key at `+0x24` starts with `CHARASELECT_` or `COLORSELECT_`. That keeps other menus untouched even if the key stays behind. RAX and flags are preserved. `shift` defaults to 620 (as high as it fits); `[bar] shift=` in the ini changes it.

### 5.2 Big portraits of the extras

`0x4538E0` and `0x453B50` set the big select portraits. They read the ID at `selector + side*0x6C + member*0x14 + 0xBED`, convert it with IdToCode, build `/Game/UI/CharaSelect_S3/tex/CS_CharacterImage_%s.CS_CharacterImage_%s` (`0x4A21D0`) and pass it to `0xC87930`.

`0xC87930` is **`StaticFindObject(class, ANY_PACKAGE, name, exact)`**: its assert strings are "Illegal call to StaticFindObject() while serializing object data!" and "…while collecting garbage!". It only finds objects already in memory. The original characters' portraits always are; the extras' never were, so the widget got null and kept Super Saiyan Goku.

The fix replaces the two calls (`0x453A7C` and `0x453CEC`, both `e8 → 0xC87930`) with `portrait_find`: if the first extra from `chara_mods.txt` is not in memory, it loads all of them with `0x4A69D0` and searches again; if one still misses, it loads that one. Since 0.2.2, `selector_ui_preload` (called from the module's Lua 8 s after start, on the game thread) loads the 14 portraits once and marks them `RootSet` in `GUObjectArray` (RVA `0x4274390`; `Objects` at +0x10, `NumElements` at +0x1C, 24-byte items with flags at +8), exactly what the game's own inline `AddToRoot` does at `0x2459B5`. They then stay in memory, so entering the select screen loads nothing. Every code therefore needs a texture named exactly `CS_CharacterImage_<CODE>` (object name = file name) in `/Game/UI/CharaSelect_S3/tex/`.

Known gap: the portrait offset tables (`widget+0x394/+0x514` and `+0x49C/+0x61C`, indexed `id*8`) have 48 entries, so extras read the neighbouring entry. No visible shift has been reported, but a new code could land slightly off.

Lesson from this patch: both portrait sites are on the same memory page. Restoring the page protection right after writing the first site leaves the second write on a read-only page and crashes the game. Write everything, then restore protections in reverse order (`selector_ui_install_at`).

---

## 6. The cursor mask (`DBFZSlotsMask.pak`)

`/Game/UI/CharaSelect_S3/tex/CharaPositionMask` is a 1280×720 texture with one index byte per pixel: `255` = nothing, other values = mask IDs. Mask IDs go through the tables of patch 2 to character IDs. This pak is the game's own Store mask with regions 45–59 added for the 4th row. `tools/build_mask_pak.py` packs an edited mask; it does not draw one.

---

## 7. Turning a replacement mod into its own slot

`tools/build_char.py NEW BASE mod.pak [--keep FOLDERS] [--sub OLD:NEW] [--keep-refs]`

1. Takes the base game's `Chara/<BASE>/` files, then overlays the mod's files for that folder.
2. Renames every path `/Game/Chara/<BASE>/` → `/Game/Chara/<NEW>/` and the data names `BBS_<BASE>`, `COL_<BASE>` (same length, so name maps keep their layout; FName hashes are recomputed with the game's CRC).
3. Skips mod files that belong to other base characters (so, for example, Beerus and Whis stay normal). `--sub WTN:URA` gives such a character its own copy instead (Sukuna's Uraume uses Whis's files; Super Vegito uses `--sub VGS:VGX`).
4. Keeps new `Shared/` files; skips overrides of existing shared files (those would change every character). `--keep YGI,SOL` copies extra folders the mod adds. `--keep-refs` leaves references inside kept folders as they were (needed to reproduce the tested Yugi).
5. Writes `DBFZX_<NEW>.pak` and a JSON report with missing references.

Cooked assets sometimes import objects without listing them as preload dependencies; the engine then touches an unloaded object (Sol's `MI_BaseWep` crash, Granolah's frozen Rolling Kick). `tools/fix_preload_dependencies.py` adds the missing `CreateBeforeSerializationDependencies` and fixes the header counts and offsets without touching the `.uexp` payloads. It only supports the single-export structure it was checked on.

UI and text for each code:

- `build_ui2.py` / `montar_extras.py`: seven portrait kinds (`cp_chara_`, `cp_chara_sparking_`, `vs_chara_`, `arcade_chara_`, `faceD_`, `StoryStand_`, `CS_CharacterImage_`) and the select icon, taken from the mod (named for the base) or from the game, renamed to the code.
- `build_texts.py`: copies the base character's text keys (`CMD<BASE>…`, `<BASE>_ASSIST_…`, `CHARA_NAME_*`, `AVATAR_NAME_…`, `ComboChallengeName…`) to the new code in all 13 language tables (`Localization/*/REDGame`), sets the display names and applies the mod's own texts (`text.json` or its `REDGame`).

`tools/montar_extras.py` runs all of this for the 14-character reference roster from the original downloads and checks the result against `tools/reference-sha256.json` (the tested install, byte for byte). The versions it expects are listed in `docs/VERSIONES-PROBADAS.md`.

---

## 8. Adding your own character

1. Pick an unused three-letter code (letters and digits, not a game code).
2. `build_char.py CODE BASE yourmod.pak` (add `--keep`/`--sub` if the mod ships extra folders or touches other characters) and read the report's `missing_refs`.
3. Add UI (portraits + icon) and texts for the code, or extend `ROSTER` in `montar_extras.py`.
4. Append the code to `chara_mods.txt` and its icon to `icons.txt`. The Nth line takes the Nth 4th-row slot.
5. Put the paks (each with a `.sig`) in `RED/Content/Paks/~mods/`, restart the game from the Start menu, and read `dbfzslots.log`, `selector-ui.log` and `UE4SS.log`.

---

## 9. Porting to another build

The tools and the asset side (sections 6–8) are build-independent as long as the game's asset versions match. The native addresses are not.

For every site, find the same instruction in the other executable, check its behaviour, and put the new RVA and bytes in the site tables (`sites[]` in both `.c` files). Ways to find them:

| Site | How to find it |
|---|---|
| IdToCode / CodeToId and the code table | Search the wide strings `L"GKS"`, `L"VGS"`… The table of `{id, pad, wchar_t*}` points at them; its two readers are IdToCode/CodeToId. |
| StaticFindObject | UTF-16 strings "Illegal call to StaticFindObject() while serializing object data!"; the function that references them. |
| Portrait setters | Wide string `/Game/UI/CharaSelect_S3/tex/CS_CharacterImage_%s.CS_CharacterImage_%s`; its path builder is called from the two setters, each followed by the find call. |
| LoadObject used for icons | Called with an FString path; referenced by many UI loads. It is the function the empty-path diagnostic hooks. |
| Help bar | Floats `764.0` and `140.0` in the two draw functions; the announcement singleton is the object whose `+0x24` receives `CHARASELECT_Announce` / `COLORSELECT_Announce` from the setter that references those key strings. |
| "Real character" checks | Compares against `0x2E`, `0x2F` or `0x30` on a character ID in selector, validation and battle-setup code; follow the IdToCode callers and the team setup. |
| Mask tables | Byte tables of 0x2D and 0x26 entries indexed by the mask value, bound-checked with `cmp dl,0x2D` / `0x26`. |

`tools/selector_native_refs.py <rva> [end]` disassembles around an address and `--strings text…` finds references to a string (set `DBFZ_GAME` to your game folder). Also re-measure the UE4SS offsets for `MemberVariableLayout.ini` on that build.

Test offline first: `source/test/selector_ui_test.c` and `source/test/harness.c` map the executable without running it, apply the patches and check each jump and that nothing is written when bytes differ.

---

## 10. Building and testing

```powershell
zig cc -target x86_64-windows-gnu -shared -O2 -o dbfzslots.dll source/src/dbfzslots.c source/src/caves.S
zig cc -target x86_64-windows-gnu -shared -O2 -o selector-ui.dll source/src/selector_ui.c source/src/selector_ui.S
zig cc -target x86_64-windows-gnu -O1 -municode -o selector_ui_test.exe source/test/selector_ui_test.c
.\selector_ui_test.exe "<game>\RED\Binaries\Win64\DRAGON_BALL_FighterZ.exe" selector-ui.dll
```

`selector-ui.dll` in this package was built with Zig 0.16.0. `dbfzslots.dll` is the exact binary tested in game; rebuilding it gives different bytes, so test a rebuild before using it. Restart the game after replacing a DLL: both pin themselves in memory and UE4SS hot reload (Ctrl+R) can close the game.

---

## 11. Files and logs at a glance

| Path (under `RED/Binaries/Win64/`) | Role |
|---|---|
| `dwmapi.dll`, `ue4ss/` | UE4SS loader and runtime |
| `ue4ss/Mods/mods.txt` | `DBFZSlotsStore : 1`, `DBFZSlotsIcons : 1`, `DBFZSlotsUIFix : 1` (in that order) |
| `ue4ss/Mods/DBFZSlotsStore/` | `dbfzslots.dll` + loader Lua |
| `ue4ss/Mods/DBFZSlotsIcons/` | icon Lua + `icons.txt` |
| `ue4ss/Mods/DBFZSlotsUIFix/` | `selector-ui.dll`, `selector-ui.ini`, loader Lua |
| `ue4ss/Mods/DBFZSlotsStore/chara_mods.txt` | roster |
| `ue4ss/MemberVariableLayout.ini` | UE4SS offsets for this build |
| `ue4ss/dbfzslots.log`, `ue4ss/selector-ui.log`, `ue4ss/UE4SS.log` | logs |
| `RED/Content/Paks/~mods/` | `DBFZSlotsMask.pak`, character paks, `DBFZSlotsText.pak`, `DBFZSlotsUI.pak`, patches (each with `.sig`) |

## 12. License and credits

MrPopulutus' own code, tools and docs are MIT (`LICENSE.txt`): change, reuse and redistribute them freely, keeping the credit. The game and every character mod keep their owners and licenses (most characters are CC BY-NC-ND 4.0: ask their authors before sharing adapted versions). Credits and links: `CREDITOS.md`. Built with help from Claude (Anthropic) and ChatGPT/Codex (OpenAI).
