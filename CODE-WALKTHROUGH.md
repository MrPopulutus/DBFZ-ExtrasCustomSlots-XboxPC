# Code walkthrough

The core DLL extends character IDs in the Microsoft Store executable. Lua modules draw the extra icons, and Python tools convert character downloads locally. For inspiration and contributor credits, see [CREDITOS.md](CREDITOS.md).

Addresses are RVAs in the tested Microsoft Store executable. Code excerpts are shortened for explanation and may omit checks or use placeholders; consult the source files before changing or compiling anything.

Contents:

1. [Start-up chain](#1-start-up-chain)
2. [`lua/DBFZSlotsStore/main.lua`: loading the core DLL](#2-luadbfzslotsstoremainlua-loading-the-core-dll)
3. [`src/dbfzslots.c`: the core patch](#3-srcdbfzslotsc-the-core-patch)
4. [`src/caves.S`: the assembly caves](#4-srccavess-the-assembly-caves)
5. [`lua/DBFZSlotsIcons/main.lua`: 4th-row icons](#5-luadbfzslotsiconsmainlua-4th-row-icons)
6. [`lua/DBFZSlotsUIFix/main.lua` + `src/selector_ui.c` + `src/selector_ui.S`: help bar and portraits](#6-the-ui-fix-help-bar-and-big-portraits)
7. [`config/`: the data files](#7-config-the-data-files)
8. [`tools/inspect_pak.py` and the pak format](#8-toolsinspect_pakpy-and-the-pak-format)
9. [`tools/build_char.py`: giving a character its own code](#9-toolsbuild_charpy-giving-a-character-its-own-code)
10. [`tools/fix_preload_dependencies.py`: the Sol / Granolah repair](#10-toolsfix_preload_dependenciespy-the-sol--granolah-repair)
11. [`tools/build_texts.py`: names and command lists](#11-toolsbuild_textspy-names-and-command-lists)
12. [`tools/montar_extras.py`: the one-command build](#12-toolsmontar_extraspy-the-one-command-build)
13. [`tools/instalar.py`: the installer](#13-toolsinstalarpy-the-installer)
14. [`tests/`: offline tests](#14-tests-offline-tests)
15. [Where to change what](#15-where-to-change-what)

## 1. Start-up chain

```
Windows starts DRAGON_BALL_FighterZ.exe
  └─ loads dwmapi.dll from the game folder (UE4SS loader)
       └─ UE4SS.dll reads ue4ss/Mods/mods.txt and runs each enabled Lua module
            ├─ DBFZSlotsStore/Scripts/main.lua  → package.loadlib(dbfzslots.dll)  → patches IDs, grid, validity, battle
            ├─ DBFZSlotsIcons/Scripts/main.lua  → draws the 4th-row icons when the select screen appears
            └─ DBFZSlotsUIFix/Scripts/main.lua  → package.loadlib(selector-ui.dll) → help bar + portraits
```

The two DLLs are plain Windows DLLs with a `luaopen_*` export. Lua's `package.loadlib` loads them and calls that export once. They never use the Lua state; they patch the running game and pin themselves in memory.

## 2. `lua/DBFZSlotsStore/main.lua`: loading the core DLL

```lua
local src = debug.getinfo(1, "S").source                       -- "@D:\...\DBFZSlotsStore\Scripts\main.lua"
local p = src:sub(2):gsub(string.char(92), "/")
local dir = p:match("^(.*)/[Ss]cripts/main%.lua$")             -- the module folder
table.insert(candidates, dir .. "/dbfzslots.dll")
...
local init, e = package.loadlib(path, "luaopen_dbfzslots")
if init then init() ... return end
```

It works out its own folder from the script path (so it does not depend on the current directory), tries a few candidate paths, loads the DLL and calls `luaopen_dbfzslots`. Everything is wrapped in `pcall` so an error is logged in `UE4SS.log` instead of stopping UE4SS.

## 3. `src/dbfzslots.c`: the core patch

### 3.1 Constants and globals

```c
#define FIRST_EXTRA 0x31
#define MAX_EXTRAS 15  // IDs 0x31..0x3f; mask ids 45..59 (4th row)

uint32_t g_extra_end = FIRST_EXTRA;           // first ID past the last extra (read by caves.S)
__declspec(dllexport) uint64_t g_t[64];       // absolute jump targets back into the game
static wchar_t g_codes[MAX_EXTRAS][8];        // "PCO", "GHB", ... from chara_mods.txt
```

The game uses `0x00`–`0x2E` for real characters, `0x2F` for DMY (dummy) and `0x30` for MAX/none. Extras start at `0x31`, so the game's own markers keep their meaning. `g_extra_end` is what every cave compares against.

### 3.2 Entry points

```c
__declspec(dllexport) int luaopen_dbfzslots(void *L) { (void)L; dbfzslots_init(); return 0; }

__declspec(dllexport) int dbfzslots_init(void) {
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN, ...);  // never unload
    GetModuleFileNameW(NULL, dir, MAX_PATH);  ...                                                    // game's Win64 folder
    return dbfzslots_install_at(GetModuleHandleW(NULL), dir);
}
```

`GET_MODULE_HANDLE_EX_FLAG_PIN` matters: once the game jumps into this DLL, unloading it (for example on a UE4SS hot reload) would crash the game. `GetModuleHandleW(NULL)` is the base address of the game executable. `dbfzslots_install_at` opens `ue4ss\dbfzslots.log` and calls `install()`. The test harness calls `dbfzslots_install_at` directly with a mapped copy of the executable.

### 3.3 Safety first: `expect()` on every site

```c
static int expect(uint32_t rva, const char *hex) {       // compare game bytes with the expected hex string
    for (...) if (R(rva)[i] != (uint8_t)v) { logf_("MISMATCH at +0x%x ..."); return 0; }
    return 1;
}
...
static const struct { uint32_t rva; const char *hex; } sites[] = {
    {0x57ee26, "488d35c30db302"}, {0x57ee3a, "83f930"}, ...  // 34 sites
};
for (...) if (!expect(sites[i].rva, sites[i].hex)) { logf_("unexpected game build, nothing patched"); return 0; }
```

Before writing a single byte, all 34 sites are compared with the bytes of the tested executable. One difference and nothing is patched. This is what makes the DLL safe on another game version: it simply does nothing.

### 3.4 Reading the roster

```c
static void load_codes(void) {
    ... L"\\ue4ss\\Mods\\DBFZSlotsStore\\chara_mods.txt"
    while (g_nextras < MAX_EXTRAS && fgets(line, sizeof line, f)) {
        ... // trim, skip empty lines, keep up to 7 chars
        logf_("extra 0x%x = %.*s", FIRST_EXTRA + g_nextras, (int)n, p);
        g_nextras++;
    }
}
```

Line N becomes ID `0x30 + N`. `g_extra_end = FIRST_EXTRA + g_nextras`.

### 3.5 Tools used by every patch

```c
static uint8_t *near_alloc_init(void)    // VirtualAlloc a 64 KB block within +-2 GB of the exe
static void *near_take(size_t n)         // take n bytes from that block (16-byte aligned)
static void retarget_rip(uint32_t rva, int doff, int len, void *abs)   // rewrite a rip-relative displacement
static void hook(uint32_t rva, int n, void *cave)                      // jmp rel32 -> 14-byte stub -> cave
```

- A `jmp rel32` can only reach ±2 GB, and the DLL may be loaded further away. So `hook()` writes a 5-byte `jmp` at the game site to a **stub** in the near block, and the stub does `jmp qword ptr [rip+0]` with the cave's full 64-bit address. The rest of the overwritten instruction bytes become `nop`.
- `retarget_rip()` changes where an instruction like `lea rsi, [rip+table]` points: it computes the new 32-bit displacement to our copy of the table and writes it.
- `write_bytes()` does `VirtualProtect` → `memcpy` → restore protection → `FlushInstructionCache`.

### 3.6 Patch 1: ID ↔ code table

```c
struct CodeEntry { int32_t id; int32_t pad; const wchar_t *code; };
struct CodeEntry *tab = near_take(sizeof(struct CodeEntry) * (48 + MAX_EXTRAS));
memcpy(tab, R(0x30afbf0), 48 * sizeof(struct CodeEntry));           // the game's 48 entries
for (i...) { tab[48 + i].id = FIRST_EXTRA + i; tab[48 + i].code = g_codes[i]; }
retarget_rip(0x57ee26, 3, 7, tab);            // IdToCode:  lea rsi, table
put8(0x57ee3a + 2, count);                    //            cmp ecx, count
retarget_rip(0x57ef31, 3, 7, (uint8_t *)tab + 8); // CodeToId: lea r15, table+8
put8(0x57effd + 3, count);                    //            cmp r14d, count
retarget_rip(0x57f019, 3, 7, tab);            //            lea rcx, table
```

The game converts IDs to codes (`0x00` → `L"GKS"`) with a 48-entry table at `0x30AFBF0`, read by `IdToCode` (`0x57EE00`) and `CodeToId` (`0x57EF00`). We copy it, append the extras and point the three `lea` instructions and the two loop limits at the bigger copy. From here on, the game knows that `0x31` is `L"PCO"`, and it builds every asset path (`/Game/Chara/PCO/...`) from that.

### 3.7 Patch 2: cursor mask → character

```c
uint8_t *m45 = near_take(64), *m38 = near_take(64);
memset(m45, 0x30, 64); memset(m38, 0x30, 64);           // 0x30 = none
memcpy(m45, R(0x41e7510), 0x2d); memcpy(m38, R(0x41e75b8), 0x26);
for (i...) { m45[0x2d + i] = FIRST_EXTRA + i; m38[0x2d + i] = FIRST_EXTRA + i; }
put8(0x455cae + 2, 0x2d + MAX_EXTRAS); retarget_rip(0x455cbc, 3, 7, m45);
...
```

The select screen reads a byte from the cursor mask texture (`DBFZSlotsMask.pak`) under the cursor, then uses these tables to turn it into a character ID. Two tables exist (45 and 38 entries) for two layouts. Mask values 45–59 (the 4th row drawn in our mask) now map to `0x31`–`0x3F`, and the bound checks (`cmp dl, 0x2D`) are raised so those values are accepted.

### 3.8 Patches 3–5: "is this a real character?"

```c
g_t[0] = (uint64_t)R(0x58783d); g_t[1] = (uint64_t)R(0x587845);
hook(0x587830, 13, cave_isvalid);                                   // IsCharaValid
g_t[2] = (uint64_t)R(0x453f48);  g_t[3] = (uint64_t)R(0x454032); hook(0x453f3f, 9, cave_453f3f);
... // 12 more sites
```

All over the game there are checks like `cmp edi, 0x2F / jge bad` ("an ID of 0x2F or more is not a character"). Each one gets a cave that says "≤ 0x2E **or** an extra". For each site, `g_t[ok]` and `g_t[bad]` hold the two addresses the original code would have jumped to. The table of sites is in section 3.2 of `HOW-IT-WORKS.md`.

The last comment explains what is **not** patched: the list-based selectors (`0x74DDE0`, `0x72E2F0`) have 48 entries, so extras only appear in the main grid.

## 4. `src/caves.S`: the assembly caves

GNU assembler, Intel syntax. Every cave ends in `jmp qword ptr [rip + g_t + 8*i]`, which jumps back into the game through the table filled in section 3.8.

### IsCharaValid

```asm
cave_isvalid:
    cmp ecx, 0x31
    jb 1f                                   ; below the extras -> original code
    cmp ecx, dword ptr [rip + g_extra_end]
    jae 1f                                  ; above the last extra -> original code
    mov al, 1                               ; extra: valid
    ret
1:  push rdi                                ; the 13 original bytes we overwrote
    sub rsp, 0x20
    mov edi, ecx
    cmp ecx, 0x2f
    jne 2f
    jmp qword ptr [rip + g_t + 8*0]
2:  jmp qword ptr [rip + g_t + 8*1]
```

### The generic check

```asm
.macro REAL_S reg, ok, bad
    cmp \reg, 0x2e
    jle 8f                                  ; a real game character
    cmp \reg, 0x31
    jl 9f                                   ; DMY / none
    cmp \reg, dword ptr [rip + g_extra_end]
    jge 9f                                  ; past the last extra
8:  jmp qword ptr [rip + g_t + 8*\ok]
9:  jmp qword ptr [rip + g_t + 8*\bad]
.endm
cave_453f3f: REAL_S edi, 2, 3
```

`REAL_U` is the same with unsigned jumps. `COUNT_SITE` does it for the battle-setup loop that counts team members (`cmp dword [rdx+disp], 0x2E`), saving `rax` because it needs a register.

### Diagnostics

`cave_4a69d0` guards the game's `LoadObject(FString)`: an empty path makes the engine abort, so the cave logs who asked and returns null instead. `cave_58e830`/`cave_58e850` log every "set character for side/member" call; `cave_5d4804` logs the six team IDs at battle setup. They save and restore every volatile register and the flags (`SAVE_VOLATILE`/`RESTORE_VOLATILE`) and align the stack to 16 bytes before calling C.

## 5. `lua/DBFZSlotsIcons/main.lua`: 4th-row icons

```lua
local CENTERS = { {117,629}, {195,631}, ... }            -- 15 slot centres in mask pixels (1280x720)
for _, r in ipairs(readLines(MODS .. "/DBFZSlotsStore/chara_mods.txt", "^%s*(%w%w%w)%s*$")) do codes[#codes + 1] = r[1] end
for _, r in ipairs(readLines(MODS .. "/DBFZSlotsIcons/icons.txt", "^%s*(%w%w%w)%s+(%S+)")) do icons[r[1]] = r[2] end
```

```lua
local function addIcons(host)
    local canvas = host.Icon01.Slot.Parent                  -- the canvas that holds the game's icons
    local imageClass = StaticFindObject("/Script/UMG.Image")
    local loadIcons = package.loadlib(MODS .. "/DBFZSlotsStore/dbfzslots.dll", "dbfz_load_icons")
    if loadIcons then loadIcons() end                       -- load icons.txt textures with the game's loader
    for i, code in ipairs(codes) do
        local tex = StaticFindObject(icons[code])
        local img = StaticConstructObject(imageClass, host.WidgetTree, FName("DBFZExtraIcon_" .. code))
        img:SetBrushFromTexture(tex, false)
        img:SetVisibility(4)                                -- HitTestInvisible: never steals the cursor
        canvas:AddChildToCanvas(img)
        img.Slot:SetAlignment({X = 0.5, Y = 0.5}); img.Slot:SetSize({X = 256, Y = 256})
        img.Slot:SetPosition({X = c[1] * 3, Y = c[2] * 3 + 256})   -- mask pixels -> canvas units
        img.Slot:SetZOrder(3)
    end
end
```

```lua
local selectSeen = package.loadlib(MODS .. "/DBFZSlotsUIFix/selector-ui.dll", "selector_ui_select_seen")
LoopAsync(500, function()                                   -- twice a second, a plain number read
    if not searching and selectSeen(true) then              -- true once after new select-screen activity
        searching = true
        search(0)                                           -- FindAllOf, then add the icons
    end
    return false
end)
```

`selector-ui.dll` counts the select screen's portrait lookups; `selector_ui_select_seen` returns its argument once after that count changes (it has no Lua API, so it returns 1 result, its own argument, or 0 results). When that happens, `search()` looks the icon lists up with `FindObjects` (skipping objects being destroyed) every 250 ms (up to 30 times) and adds one `Image` per extra, in the game thread (`ExecuteInGameThread`), to each one whose `Icon01` slot exists. It never listens to new objects and never keeps a widget across a delay: an earlier version did, and the game crashed at the end of Versus matches and when a rematch went back to character select (fixed in 0.3.2 and 0.3.3; since 0.3.3 `dbfz_load_icons` also keeps the icon textures loaded for the whole session). If `selector-ui.dll` is missing it falls back to `pollEverySecond()`.

## 6. The UI fix: help bar and big portraits

### 6.1 `lua/DBFZSlotsUIFix/main.lua`

```lua
local init = package.loadlib(dir .. "/selector-ui.dll", "luaopen_selector_ui")
init()
local preload = package.loadlib(dir .. "/selector-ui.dll", "selector_ui_preload")
LoopAsync(8000, function()                                  -- every 8 s, 6 times
    runs = runs + 1
    ExecuteInGameThread(function() pcall(preload) end)
    return runs >= 6
end)
```

### 6.2 `src/selector_ui.c`: install

```c
static const struct Site { uint32_t rva, resume; int size; uint8_t expected[9]; } sites[] = {
    {0x5c98ce, 0x5c98d6, 8, {0xf3,0x0f,0x58,0x35,0x82,0x04,0xb1,0x02}},      // addss xmm6,[764.0]
    {0x5ca236, 0x5ca23f, 9, {0xf3,0x44,0x0f,0x58,0x05,0x19,0xfb,0xb0,0x02}}, // addss xmm8,[764.0]
    {0x453a7c, 0, 5, {0xe8,0xaf,0x3e,0x83,0x00}},                             // call StaticFindObject
    {0x453cec, 0, 5, {0xe8,0x3f,0x3c,0x83,0x00}},                             // call StaticFindObject
};
```

`selector_ui_install_at()`:

1. `memcmp` of all four sites with `expected`; any difference → log and return `-1`.
2. For the two bar sites, it also reads the `addss` operand and checks the constant is still `764.0`.
3. Allocates a near stub block and writes one `jmp qword ptr [rip+0]` stub per site.
4. Makes all four sites writable, writes `jmp rel32` (bar sites) or `call rel32` (portrait sites) plus `nop` padding, and **only then** restores the protections, in reverse order. Both portrait sites share one memory page, so restoring after the first write would leave the second on a read-only page.

`luaopen_selector_ui()` pins the DLL, opens `ue4ss\selector-ui.log`, reads `[bar] shift` from `selector-ui.ini` (clamped 0–700), reads `chara_mods.txt` into `portrait_paths[]` and calls the install.

### 6.3 `src/selector_ui.S`: the help bar cave

```asm
.macro UI_ADJUST reg, destination
    addss \reg, dword ptr [rip + ui_original_base]  ; the instruction we replaced: y += 764
    pushfq
    push rax
    mov rax, qword ptr [rip + ui_announce]          ; announcement object (RVA 0x46FA450)
    test rax, rax
    jz 9f
    cmp dword ptr [rax], 1                          ; shown right now?
    jne 9f
    cmp dword ptr [rax + 0x24], 0x52414843          ; key starts "CHAR" ...
    ...                                             ; "CHARASELECT_" or "COLORSELECT_"
    subss \reg, dword ptr [rip + ui_top_shift]      ; y -= shift (620 by default)
9:  pop rax
    popfq
    jmp qword ptr [rip + \destination]              ; back to the game, after the replaced bytes
.endm
ui_guide_cave:    UI_ADJUST xmm6, ui_resume_guide
ui_announce_cave: UI_ADJUST xmm8, ui_resume_announce
```

The game draws the announcement and button guide at `y = 764 − animation × 140` in 1280×720 units. The cave keeps that and subtracts `shift` only while the announcement with a select-screen key is visible, so other menus are untouched. It preserves `rax` and the flags because the game's next instructions expect them unchanged.

### 6.4 Portraits: `portrait_find()` and `selector_ui_preload()`

```c
static void *portrait_find(void *cls, void *outer, const wchar_t *name, uint8_t exact) {
    find_fn find = (find_fn)(game_base + 0xc87930);             // StaticFindObject
    int portrait = name && wcsstr(name, L"/CS_CharacterImage_") != NULL;
    if (portrait && portrait_count && !find(cls, outer, portrait_paths[0], exact)) {
        for (i...) { if (!find(...portrait_paths[i]...)) load_path(portrait_paths[i]); ... }   // load all 14
    }
    void *r = find(cls, outer, name, exact);
    if (!r && portrait) { load_path(name); r = find(cls, outer, name, exact); }
    return r;
}
```

The game's portrait setters call `StaticFindObject`, which only returns objects already in memory. The original characters' portraits are always loaded; the extras' never were, so every extra showed Super Saiyan Goku. `portrait_find` replaces those two calls: on a miss it loads the textures with the game's own loader (`0x4A69D0`, `load_path()`) and searches again.

```c
static int add_to_root(void *obj) {
    uint8_t *arr = game_base + GUOBJECTARRAY_RVA;                       // 0x4274390
    struct UObjectItem *items = *(struct UObjectItem **)(arr + 0x10);
    int32_t num = *(int32_t *)(arr + 0x1c), idx = *(int32_t *)((uint8_t *)obj + 0x0c);
    if (... idx < 0 || idx >= num || items[idx].object != obj) return 0;   // layout check
    InterlockedOr(&items[idx].flags, ROOTSET_FLAG);                     // 1 << 30, like AddToRoot
    return 1;
}
```

`selector_ui_preload()` (called from Lua 8 s after start) loads the 14 portraits once and marks each one `RootSet` in the engine's object array, exactly what the game's own inline `AddToRoot` does at `0x2459B5`. They then stay in memory for the session, so entering the select screen does not stop to load them. If the layout check fails, it just skips the flag.

## 7. `config/`: the data files

| File | Format |
|---|---|
| `chara_mods.txt` | One code per line, ASCII, no BOM. Line N = ID `0x30+N` = 4th-row slot N. Installed in `ue4ss/Mods/DBFZSlotsStore/`. |
| `icons.txt` | `CODE /Game/Path/Texture.Texture` per line. |
| `selector-ui.ini` | `[bar]` `shift=620` (0 = original position). |
| `MemberVariableLayout.ini` | UE4SS: the Store build has 24-byte `TArray`/`FString`, so `UStruct`, `UFunction` and `UEnum` fields sit 16 bytes later than UE4SS assumes. Measured values. |
| `mods.txt` | UE4SS module list: `DBFZSlotsStore`, `DBFZSlotsIcons`, `DBFZSlotsUIFix` at `1`, in that order. |

## 8. `tools/inspect_pak.py` and the pak format

```python
def read_pak(path, output=None):
    f.seek(-44, 2)
    magic, ver, offset, size, digest = struct.unpack('<IIQQ20s', f.read(44))   # footer
    assert magic == 0x5a6f12e1 and ver in (3, 4)
    f.seek(offset); index = f.read(size)                                        # index
    mount = string(); count = ...
    for _ in range(count):
        name = string()
        pos, packed, raw, method = struct.unpack('<QQQI', r.read(28)); sha = r.read(20)
        if method: blocks = [struct.unpack('<QQ', r.read(16)) for _ in range(nb)]
        encrypted, blocksize = struct.unpack('<BI', r.read(5))
```

A UE4 pak (version 3/4, used by DBFZ) is: file data, then an index (mount point + one entry per file: offset, sizes, compression, SHA-1, compressed blocks), then a 44-byte footer with the magic `0x5A6F12E1`, the index offset and its SHA-1. `write_pak()` in `build_char.py` writes the same format: zlib, one block per file, mount `../../../`.

## 9. `tools/build_char.py`: giving a character its own code

`python build_char.py NEW BASE mod.pak [--keep A,B] [--sub OLD:NEW] [--keep-refs]`

### Asset names and their hash

```python
def names(b):                                   # the name map of a .uasset
    folderlen = struct.unpack_from('<i', b, 28)[0]
    p = 32 + folderlen + 4
    count, offset = struct.unpack_from('<ii', b, p)
    for _ in range(count):
        n = ...; size = abs(n) * (2 if n < 0 else 1); enc = 'utf-16-le' if n < 0 else 'utf8'
        yield text, offset, size, hpos, enc      # position of the text and of its hash

def namehash(s, enc):                            # UE4 FName hash: CRC of the upper-case text + CRC32
    up = ''.join(chr(ord(c) - 32) if 'a' <= c <= 'z' else c for c in s)
    for b in up.encode(enc): h = (h >> 8) ^ table[(h ^ b) & 255]
    return (h & 65535) | ((zlib.crc32(s.encode('utf-32-le')) & 65535) << 16)
```

### Renaming

```python
def make_conv(base, new):
    rx_path = re.compile(r'(/chara/)' + base + '(/|$)', re.I)       # /Game/Chara/YMN/... -> /Game/Chara/SBG/...
    rx_data = re.compile(r'^(BBS_|COL_)' + base + '(EF)?$', re.I)    # BBS_YMN -> BBS_SBG (script / colour data)

def convert_uasset(b, conv, report, path):
    for s, start, size, hpos, enc in names(b):
        t = conv(s)
        data = (t + '\0').encode(enc); assert len(data) == size   # same length: codes are 3 letters
        new[start:start + size] = data
        ... # keep the hash style the file used: 0, 16-bit, or full 32-bit
        struct.pack_into('<I', new, hpos, nh)

def convert_uexp(b, base, new):                  # plain byte replace of /Chara/BASE/ in ASCII and UTF-16
```

Because the old and new codes have the same length, every string keeps its size, so offsets inside the file never change. Only the text and its hash are rewritten.

### `main()` step by step

1. Reads every file of `Chara/<BASE>/` **from the game** (`pakchunk0-WinAnvil.pak`).
2. Overlays the mod's files: those under `Chara/<BASE>/` replace the game's; those under `--sub` characters get their own copy; `--keep` folders are copied; new `Shared/` files are kept; overrides of existing shared files and files of other characters are skipped and listed in `report['skipped']`.
3. Renames paths (`rename_path`) and contents (`convert_uasset`, `convert_uexp`, plus the `--sub` byte replacements).
4. Checks that every `/Game/Chara/NEW/...` import exists in the result (`missing_refs`).
5. Writes `paks/chars/DBFZX_<NEW>.pak` and a JSON report.

## 10. `tools/fix_preload_dependencies.py`: the Sol / Granolah repair

```python
CLASSES = {'REDPawnMaterials', 'REDMeshMaterialSet', 'REDAnimSet'}
def repair(b, x):
    ... # single-export assets of those classes only
    # the export's CreateBeforeSerializationDependencies list is missing some imports it uses:
    # add them, then fix the counts, the total header size, SerialOffset and BulkDataStartOffset
```

Unreal loads an asset's dependencies from a preload list in its header. Sol's colour material lists and Granolah's animation set used objects that were not in that list, so they were not loaded in time: Sol crashed on `MI_BaseWep`, Granolah froze in Rolling Kick. The script adds the missing entries to the header and leaves the `.uexp` payload byte-for-byte unchanged. It is idempotent: running it twice changes nothing.

## 11. `tools/build_texts.py`: names and command lists

```python
def key_for(base, extra, key):
    pats = [(rf'^CMD{base}(\d\d\w*)$', rf'CMD{extra}\1'), (rf'^{base}_ASSIST_(\d\d)$', rf'{extra}_ASSIST_\1'),
            (rf'^CHARA_NAME_(L|S|DEMO)_{base}$', rf'CHARA_NAME_\1_{extra}'), ...]
```

`Localization/<LANG>/REDGame.uexp` is a UTF-16 text of `KEY\r\nVALUE\r\n` pairs. For each of the 13 languages, `patch()` copies every key of the base character to the extra's code, puts the display names (Spanish tables get the Spanish names), applies the mod's own texts (`text.json` or its `REDGame`), then fixes the two length fields and the serial size in the `.uasset`.

## 12. `tools/montar_extras.py`: the one-command build

The data at the top drives everything:

```python
FUENTES = {  # how to recognise each download
    'dio':    dict(pak='DIOCharacterMoveset.pak', chara='CEN', con=['CEN'], web=...),   # DIO over Cell: must contain CEN
    'raditz': dict(pak='RaditzMoveset.pak', chara='MGS', con=['MGS'], web=...),
    ...
}
PROBADO = {'dio': 'ec688ed7...', ...}      # SHA-256 of each tested download
ROSTER = [('PCO', dict(tipo='convertir', fuente='piccolo', base='PCN', args=[], ...)),
          ('DIO', dict(tipo='convertir', fuente='dio', base='CEN', args=['--keep', 'DIO,WLD'], ...)),
          ('YUG', dict(tipo='convertir', fuente='yugi', base='AVP', args=['--keep', 'YGI', '--keep-refs'], ...)), ...]
```

`main()`:

1. `comprobar()` tests Pillow/NumPy/etcpak with a 4×4 image.
2. With `--incluir-port`, `preparar_port()` (from `instalar.py`) checks the game exe hash and the package hashes and copies `Game/`.
3. `buscar()` walks the download folders, reads `.zip` with `zipfile` and `.rar/.7z` with Windows `tar.exe` into a temp folder, and records every pak with its character folders (`pak_charas`) and SHA-256.
4. `elegir()` picks one pak per source: tested SHA first; otherwise name + main character folder + `con`/`sin` rules; several unknown versions → skip.
5. Characters missing a source are dropped from `roster`; the rest are built: `build_char.main()` for all 14 conversions, `fix_preload_dependencies.main()`, `build_werezaru_exg.py`, `build_texts.main()`, `construir_ui()`.
6. Writes `chara_mods.txt` and `icons.txt` for the built roster.
7. `proteger_originales()` refuses any output pak that touches one of the game's 85 character folders (except `VGF` in `DBFZX_VGF.pak`: an unused leftover folder of the game that the SSJ4 Vegeta download already builds on).
8. Compares with `reference-sha256.json` and writes `informe-montaje.json`.

## 13. `tools/instalar.py`: the installer

- `pedir_juego()`: asks until the folder contains the game exe.
- `preparar_port()`: exe SHA-256 must match; every file in `Game/` must match `technical-sha256.json`; copies `Game/` to the output and merges `mods.txt`.
- `main()`: runs `montar_extras.py` as a subprocess, streams its output to the screen and the `.log`, then asks to install.
- `instalar_salida()`: checks the game process is not running (PowerShell `Get-Process`), backs up every file it will overwrite (verified by hash, listed in `manifest.json`), copies and verifies each file, and on any error restores what it had written. It refuses any destination outside the game folder. Files left by 0.2.x under older names (`RETIRADOS`, `RENOMBRADOS`) go into the same backup.
- `idioma.py`: `t(es, en)` picks Spanish or English from the Windows UI language (`GetUserDefaultUILanguage`); `DBFZ_LANG` forces one.

## 14. `tests/`: offline tests

- `selector_ui_test.c`: `LoadLibraryExW(exe, DONT_RESOLVE_DLL_REFERENCES)` maps the game without running it. It runs the bar caves with fake announcement objects (right key/state, wrong key, hidden, empty), checks the ini clamp and the roster reader, installs on the mapped exe, checks every site became `jmp`/`call` to a stub that jumps into the DLL, and checks that a changed byte makes it refuse without writing.
- `harness.c` (+ `cavetest.c`, `callsite.S`, `emptytest.c`, `settest.c`): the same for `dbfzslots.dll`. It applies the patches to the mapped exe and runs the patched mask lookup and `IsCharaValid`.
- `check_lua.py`: Lua 5.4 syntax check of the modules.

## 15. Where to change what

| I want to… | Change |
|---|---|
| Add or reorder characters | `config/chara_mods.txt` + `icons.txt`, and give each code its paks (`build_char.py`) |
| Move the help bar | `config/selector-ui.ini` → `shift` |
| Move the 4th-row icons | `CENTERS` in `lua/DBFZSlotsIcons/main.lua`, and the mask regions in `DBFZSlotsMask.pak` to match |
| More than 15 extras | `MAX_EXTRAS`, table sizes and every site in section 3 of `HOW-IT-WORKS.md`, plus new mask regions |
| Support another exe (a patch, another edition) | Find each site again and update the `sites[]` tables and every RVA (`HOW-IT-WORKS.md` §9); never remove the byte checks |
| Add a character to the one-command build | `FUENTES`, `PROBADO`, `ROSTER` in `tools/montar_extras.py`, then update `reference-sha256.json` |
