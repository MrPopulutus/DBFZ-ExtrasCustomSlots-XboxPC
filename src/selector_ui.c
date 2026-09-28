// Raises the selection help bar and loads missing extra-character portraits.
// StaticFindObject only sees loaded textures; on a miss, use the game loader
// before repeating the lookup. Addresses target the verified Store executable.
#include <windows.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

// Read by the caves in selector_ui.S.
const uint8_t *ui_announce;           // announcement singleton: +0 shown state, +0x24 ASCII key
const float ui_original_base = 764.0f;
float ui_top_shift = 620.0f;          // 1280x720 units; overridable with selector-ui.ini
void *ui_resume_guide, *ui_resume_announce;
extern void ui_guide_cave(void), ui_announce_cave(void), ui_test_return(void);
extern float ui_test_guide(float), ui_test_announce(float);
static FILE *log_file;
static int initialized;

#define ANNOUNCE_RVA 0x46fa450u
static const struct Site { uint32_t rva, resume; int size; uint8_t expected[9]; } sites[] = {
    {0x5c98ce, 0x5c98d6, 8, {0xf3,0x0f,0x58,0x35,0x82,0x04,0xb1,0x02}},      // addss xmm6,[764.0]
    {0x5ca236, 0x5ca23f, 9, {0xf3,0x44,0x0f,0x58,0x05,0x19,0xfb,0xb0,0x02}}, // addss xmm8,[764.0]
    {0x453a7c, 0, 5, {0xe8,0xaf,0x3e,0x83,0x00}},                             // call StaticFindObject (1P/2P set)
    {0x453cec, 0, 5, {0xe8,0x3f,0x3c,0x83,0x00}},                             // call StaticFindObject (other)
};
#define NSITES 4
#define NBAR 2

struct GameFString { const wchar_t *data; uint64_t flags; int32_t num, max; };
typedef void *(*find_fn)(void *cls, void *outer, const wchar_t *name, uint8_t exact);
typedef void *(*load_fn)(const struct GameFString *path);
static uint8_t *game_base;
static int portrait_logs;
static void logf_(const char *fmt, ...);

// Portrait paths of the roster extras (ue4ss\Mods\DBFZSlotsStore\chara_mods.txt).
#define MAX_PORTRAITS 16
static wchar_t portrait_paths[MAX_PORTRAITS][96];
static int portrait_count, preloads;
// Counts the select screen's portrait lookups. The icon module polls it (selector_ui_select_seen)
// to know the select screen is up, instead of listening to every new object in the game.
static volatile long select_hits, select_reported;

static void load_path(const wchar_t *path) {
    size_t n = wcslen(path);
    struct GameFString fs = {path, 0, (int32_t)n + 1, (int32_t)n + 1};
    ((load_fn)(game_base + 0x4a69d0))(&fs);
}

static void *portrait_find(void *cls, void *outer, const wchar_t *name, uint8_t exact) {
    find_fn find = (find_fn)(game_base + 0xc87930);
    int portrait = name && wcsstr(name, L"/CS_CharacterImage_") != NULL;
    if (portrait) select_hits++;
    // Loading one texture from the pak on each first hover causes a visible hitch. When the
    // first extra is not in memory (selector just opened, or GC freed them), load all at once.
    if (portrait && portrait_count && !find(cls, outer, portrait_paths[0], exact)) {
        int ok = 0;
        for (int i = 0; i < portrait_count; i++) {
            if (!find(cls, outer, portrait_paths[i], exact)) load_path(portrait_paths[i]);
            ok += find(cls, outer, portrait_paths[i], exact) != NULL;
        }
        if (preloads++ < 40) logf_("preloaded extra portraits: %d/%d in memory\n", ok, portrait_count);
    }
    void *r = find(cls, outer, name, exact);
    if (!r && portrait) {
        load_path(name);
        r = find(cls, outer, name, exact);
        if (portrait_logs++ < 60) logf_("portrait %ls: loaded -> %p\n", name, r);
    }
    return r;
}

static void read_roster(const wchar_t *file) {
    FILE *f = _wfopen(file, L"rb");
    if (!f) return;
    char code[16];
    while (portrait_count < MAX_PORTRAITS && fscanf(f, "%15s", code) == 1) {
        if (strlen(code) != 3) continue;
        _snwprintf(portrait_paths[portrait_count], 96, L"/Game/UI/CharaSelect_S3/tex/CS_CharacterImage_%hs.CS_CharacterImage_%hs", code, code);
        portrait_count++;
    }
    fclose(f);
}

static void logf_(const char *fmt, ...) {
    if (!log_file) return;
    va_list ap; va_start(ap, fmt); vfprintf(log_file, fmt, ap); va_end(ap); fflush(log_file);
}

__declspec(dllexport) int selector_ui_install_at(void *base) {
    if (initialized) return initialized;
    uint8_t *b = base;
    for (int i = 0; i < NSITES; i++) {
        if (memcmp(b + sites[i].rva, sites[i].expected, sites[i].size)) {
            logf_("unexpected bytes at +%x; no UI patches applied\n", sites[i].rva);
            return -1;
        }
    }
    // The addss operand must still be the 764.0 constant the caves reproduce.
    for (int i = 0; i < NBAR; i++) {
        int32_t disp; memcpy(&disp, b + sites[i].rva + sites[i].size - 4, 4);
        float v; memcpy(&v, b + sites[i].rva + sites[i].size + disp, 4);
        if (v != ui_original_base) { logf_("constant at +%x is %f, not 764; no UI patches applied\n", sites[i].rva, v); return -1; }
    }
    // Executable jump stubs within rel32 range after the image.
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(b + ((IMAGE_DOS_HEADER *)b)->e_lfanew);
    uintptr_t start = ((uintptr_t)b + nt->OptionalHeader.SizeOfImage + 0x10000) & ~(uintptr_t)0xffff;
    uint8_t *stubs = NULL;
    for (uintptr_t a = start; a < (uintptr_t)b + 0x70000000u; a += 0x10000) {
        stubs = VirtualAlloc((void *)a, 0x10000, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
        if (stubs) break;
    }
    if (!stubs) return -2;
    void *targets[NSITES] = {ui_guide_cave, ui_announce_cave, portrait_find, portrait_find};
    for (int i = 0; i < NSITES; i++) {
        uint8_t *p = stubs + i * 16;           // jmp qword [rip+0]; dq target
        p[0] = 0xff; p[1] = 0x25; memset(p + 2, 0, 4); memcpy(p + 6, &targets[i], 8);
    }
    DWORD unused;
    if (!VirtualProtect(stubs, 0x10000, PAGE_EXECUTE_READ, &unused)) { VirtualFree(stubs, 0, MEM_RELEASE); return -3; }
    FlushInstructionCache(GetCurrentProcess(), stubs, 16 * NSITES);
    DWORD old[NSITES]; int writable = 0;
    for (; writable < NSITES; writable++)
        if (!VirtualProtect(b + sites[writable].rva, sites[writable].size, PAGE_EXECUTE_READWRITE, &old[writable])) break;
    if (writable != NSITES) {
        for (int i = 0; i < writable; i++) VirtualProtect(b + sites[i].rva, sites[i].size, old[i], &unused);
        VirtualFree(stubs, 0, MEM_RELEASE); return -4;
    }
    ui_announce = b + ANNOUNCE_RVA; game_base = b;
    ui_resume_guide = b + sites[0].resume; ui_resume_announce = b + sites[1].resume;
    for (int i = 0; i < NSITES; i++) {
        uint8_t patch[9]; memset(patch, 0x90, sizeof patch); patch[0] = i < NBAR ? 0xe9 : 0xe8;
        int32_t d = (int32_t)((stubs + i * 16) - (b + sites[i].rva + 5)); memcpy(patch + 1, &d, 4);
        memcpy(b + sites[i].rva, patch, sites[i].size);
        FlushInstructionCache(GetCurrentProcess(), b + sites[i].rva, sites[i].size);
    }
    // Restore protections in reverse order: portrait sites share a page, so
    // later calls saved the temporary RWX protection rather than the original.
    for (int i = NSITES - 1; i >= 0; i--) VirtualProtect(b + sites[i].rva, sites[i].size, old[i], &unused);
    initialized = 1;
    logf_("UI installed: selector help bar raised %.0f of 720 units\n", ui_top_shift);
    return 1;
}

__declspec(dllexport) void selector_ui_set_shift(float shift) {
    if (shift < 0.0f) shift = 0.0f;
    if (shift > 700.0f) shift = 700.0f;
    ui_top_shift = shift;
}

__declspec(dllexport) int luaopen_selector_ui(void *L) {
    (void)L;
    if (initialized) return 0;
    HMODULE self;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN,
                            (LPCWSTR)(void *)luaopen_selector_ui, &self)) return 0;
    wchar_t path[MAX_PATH]; GetModuleFileNameW(NULL, path, MAX_PATH);
    wchar_t *slash = wcsrchr(path, L'\\'); if (!slash) return 0;
    wcscpy(slash, L"\\ue4ss\\selector-ui.log"); log_file = _wfopen(path, L"w");
    // selector-ui.ini next to this DLL: [bar] shift=<units>
    wchar_t ini[MAX_PATH]; GetModuleFileNameW(self, ini, MAX_PATH);
    slash = wcsrchr(ini, L'\\');
    if (slash) {
        wcscpy(slash, L"\\selector-ui.ini");
        selector_ui_set_shift((float)GetPrivateProfileIntW(L"bar", L"shift", (int)ui_top_shift, ini));
    }
    wcscpy(wcsrchr(path, L'\\'), L"\\Mods\\DBFZSlotsStore\\chara_mods.txt");
    read_roster(path);
    logf_("roster portraits: %d\n", portrait_count);
    int r = selector_ui_install_at(GetModuleHandleW(NULL));
    logf_("install result %d\n", r);
    return 0;
}

// Offline harness: runs the exact cave arithmetic against a fake announcement object.
// Keeps the extras' portraits loaded for the whole session, so entering character select does
// not load 14 textures at once. Called from Lua a few seconds after start (game thread).
// GUObjectArray (RVA 0x4274390, UE 4.17 FFixedUObjectArray): Objects at +0x10, NumElements at
// +0x1C; FUObjectItem = {UObject*, int32 Flags, int32 ClusterRootIndex, int32 SerialNumber}.
// Setting EInternalObjectFlags::RootSet (1<<30) is what UObject::AddToRoot does.
#define GUOBJECTARRAY_RVA 0x4274390u
#define ROOTSET_FLAG (1 << 30)
struct UObjectItem { void *object; volatile LONG flags; int32_t cluster, serial; };
typedef void *(*static_class_fn)(void);
static int preload_done;

static int add_to_root(void *obj) {
    uint8_t *arr = game_base + GUOBJECTARRAY_RVA;
    struct UObjectItem *items = *(struct UObjectItem **)(arr + 0x10);
    int32_t max = *(int32_t *)(arr + 0x18), num = *(int32_t *)(arr + 0x1c);
    int32_t idx = *(int32_t *)((uint8_t *)obj + 0x0c);
    if (!items || num <= 0 || num > max || idx < 0 || idx >= num) return 0;
    if (items[idx].object != obj) return 0;   // layout guess wrong: do nothing
    InterlockedOr(&items[idx].flags, ROOTSET_FLAG);
    return 1;
}

__declspec(dllexport) int selector_ui_preload(void *L) {
    (void)L;
    if (!initialized || preload_done || !portrait_count) return 0;
    find_fn find = (find_fn)(game_base + 0xc87930);
    void *cls = ((static_class_fn)(game_base + 0x267a880))();   // the class the portrait setters pass
    int found = 0, rooted = 0;
    for (int i = 0; i < portrait_count; i++) {
        void *obj = find(cls, (void *)-1, portrait_paths[i], 0);
        if (!obj) { load_path(portrait_paths[i]); obj = find(cls, (void *)-1, portrait_paths[i], 0); }
        if (!obj) continue;
        found++; rooted += add_to_root(obj);
    }
    if (found) preload_done = 1;
    logf_("startup preload: %d/%d portraits loaded, %d kept in memory\n", found, portrait_count, rooted);
    return 0;
}

// Lua: selector_ui_select_seen(true) returns true once after new select-screen activity, nil
// otherwise. No Lua API is linked, so it returns its own argument (1 result) or nothing (0).
__declspec(dllexport) int selector_ui_select_seen(void *L) {
    (void)L;
    long hits = select_hits;
    if (hits == select_reported) return 0;
    select_reported = hits;
    return 1;
}

__declspec(dllexport) int selector_ui_test_roster(const wchar_t *file, wchar_t *last, int cap) {
    portrait_count = 0; read_roster(file);
    if (portrait_count && last) { wcsncpy(last, portrait_paths[portrait_count - 1], cap - 1); last[cap - 1] = 0; }
    return portrait_count;
}
__declspec(dllexport) float selector_ui_test(const uint8_t *announce, float input, int guide) {
    if (initialized) return -99999.0f;
    ui_announce = announce; ui_resume_guide = ui_test_return; ui_resume_announce = ui_test_return;
    return guide ? ui_test_guide(input) : ui_test_announce(input);
}
BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r) { (void)h; (void)reason; (void)r; return TRUE; }
