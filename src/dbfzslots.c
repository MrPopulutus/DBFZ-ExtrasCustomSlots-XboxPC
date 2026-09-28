// DBFZ extra character slots for the Microsoft Store build of DRAGON_BALL_FighterZ.exe.
// Modified by MrPopulutus. Inspiration and contributor credits: CREDITOS.md.
//
// Extra characters get IDs 0x31.. (after ECharaID MAX = 0x30), so the game's own
// sentinels (DMY 0x2f, MAX/none 0x30) keep their meaning.
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <wchar.h>

#define FIRST_EXTRA 0x31
#define MAX_EXTRAS 15  // IDs 0x31..0x3f; mask ids 45..59 (4th row)

static uint8_t *g_base;
static FILE *g_log;
static int g_done;

// Read by the asm caves (caves.S).
uint32_t g_extra_end = FIRST_EXTRA;  // first ID past the last extra
__declspec(dllexport) uint64_t g_t[64];                    // absolute jump targets, see caves.S for the index map

static wchar_t g_codes[MAX_EXTRAS][8];
static int g_nextras;

static void logf_(const char *fmt, ...) {
    if (!g_log) return;
    va_list ap; va_start(ap, fmt); vfprintf(g_log, fmt, ap); va_end(ap);
    fputc('\n', g_log); fflush(g_log);
}

static uint8_t *R(uint32_t rva) { return g_base + rva; }

static int expect(uint32_t rva, const char *hex) {
    size_t n = strlen(hex) / 2;
    for (size_t i = 0; i < n; i++) {
        unsigned v; sscanf(hex + 2 * i, "%2x", &v);
        if (R(rva)[i] != (uint8_t)v) { logf_("MISMATCH at +0x%x byte %u: have %02x want %02x", rva, (unsigned)i, R(rva)[i], v); return 0; }
    }
    return 1;
}

static void write_bytes(uint8_t *dst, const void *src, size_t n) {
    DWORD old; VirtualProtect(dst, n, PAGE_EXECUTE_READWRITE, &old);
    memcpy(dst, src, n);
    VirtualProtect(dst, n, old, &old);
    FlushInstructionCache(GetCurrentProcess(), dst, n);
}
static void put8(uint32_t rva, uint8_t v) { write_bytes(R(rva), &v, 1); }
static void put32(uint32_t rva, int32_t v) { write_bytes(R(rva), &v, 4); }

static uint8_t *g_near, *g_near_cur;
static uint8_t *near_alloc_init(void) {
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(g_base + ((IMAGE_DOS_HEADER *)g_base)->e_lfanew);
    uintptr_t start = ((uintptr_t)g_base + nt->OptionalHeader.SizeOfImage + 0x10000) & ~(uintptr_t)0xFFFF;
    for (uintptr_t a = start; a < (uintptr_t)g_base + 0x70000000u; a += 0x10000) {
        void *p = VirtualAlloc((void *)a, 0x10000, MEM_RESERVE | MEM_COMMIT, PAGE_EXECUTE_READWRITE);
        if (p) return (uint8_t *)p;
    }
    return NULL;
}
static void *near_take(size_t n) {
    uint8_t *p = g_near_cur; g_near_cur += (n + 15) & ~(size_t)15; return p;
}

// rip-relative operand at instruction `rva` (length len, disp at +doff) -> point at abs
static void retarget_rip(uint32_t rva, int doff, int len, void *abs) {
    int64_t d = (int64_t)((uint8_t *)abs - (R(rva) + len));
    put32(rva + doff, (int32_t)d);
}

// 5-byte jmp at rva (padding the rest of n bytes with nops) to cave via a near stub
static void hook(uint32_t rva, int n, void *cave) {
    uint8_t *stub = near_take(14);
    uint8_t s[14] = {0xFF, 0x25, 0, 0, 0, 0};
    uint64_t a = (uint64_t)cave; memcpy(s + 6, &a, 8);
    memcpy(stub, s, 14);
    uint8_t j[16]; memset(j, 0x90, sizeof j);
    j[0] = 0xE9; int32_t rel = (int32_t)(stub - (R(rva) + 5)); memcpy(j + 1, &rel, 4);
    write_bytes(R(rva), j, n);
}

extern void cave_isvalid(void);
extern void cave_453f3f(void), cave_453f80(void), cave_4541df(void), cave_454220(void);
extern void cave_74f5a0(void), cave_74c4a3(void);
extern void cave_5d4810(void), cave_5d4818(void), cave_5d481f(void);
extern void cave_5d5436(void), cave_5d5605(void), cave_5cff1b(void);
extern void cave_5d4804(void), cave_4a69d0(void), cave_58e830(void), cave_58e850(void), cave_5a9783(void), cave_5a97ae(void);
static int g_setter_logs;
void log_setter(int side, int member, int id, int kind, uint64_t ret) {
    if (g_setter_logs++ >= 200) return;
    logf_("setup %s side %d member %d id %d (0x%x) caller +0x%llx", kind ? "copy" : "set", side, member, id, id,
          (unsigned long long)(ret - (uint64_t)g_base));
}

// Diagnostics called from caves.S
void log_team_ids(const int32_t *p) {
    logf_("battle setup team ids: P1 %d %d %d | P2 %d %d %d", p[-1], p[0], p[1], p[2], p[3], p[4]);
}
static int g_empty_loads;
void log_empty_load(uint64_t ret, const uint64_t *stack) {
    if (g_empty_loads++ >= 20) return;
    char buf[512]; int n = snprintf(buf, sizeof buf, "empty LoadObject path, caller +0x%llx; stack:", (unsigned long long)(ret - (uint64_t)g_base));
    for (int i = 0; i < 64 && n < 480; i++) {
        uint64_t v = stack[i];
        if (v >= (uint64_t)g_base && v < (uint64_t)g_base + 0x3000000) n += snprintf(buf + n, sizeof buf - n, " +0x%llx", (unsigned long long)(v - (uint64_t)g_base));
    }
    logf_("%s", buf);
}

static wchar_t g_dir[MAX_PATH];  // folder that holds ue4ss\ (the game's Win64 folder)

static void load_codes(void) {
    wchar_t path[MAX_PATH]; wcscpy(path, g_dir);
    wcscat(path, L"\\ue4ss\\Mods\\DBFZSlotsStore\\chara_mods.txt");
    FILE *f = _wfopen(path, L"rb");
    if (!f) { logf_("no chara_mods.txt"); return; }
    char line[64];
    while (g_nextras < MAX_EXTRAS && fgets(line, sizeof line, f)) {
        char *p = line; while (*p == ' ' || *p == '\t') p++;
        size_t n = strcspn(p, "\r\n \t");
        if (n == 0 || n > 7) continue;
        for (size_t i = 0; i < n; i++) g_codes[g_nextras][i] = (wchar_t)p[i];
        g_codes[g_nextras][n] = 0;
        logf_("extra 0x%x = %.*s", FIRST_EXTRA + g_nextras, (int)n, p);
        g_nextras++;
    }
    fclose(f);
}

struct CodeEntry { int32_t id; int32_t pad; const wchar_t *code; };

static int install(uint8_t *base) {
    g_base = base;
    // Every site is checked before anything is written.
    static const struct { uint32_t rva; const char *hex; } sites[] = {
        {0x57ee26, "488d35c30db302"}, {0x57ee3a, "83f930"},
        {0x57ef31, "4c8d3dc00cb302"}, {0x57effd, "4183fe30"}, {0x57f019, "488d0dd00bb302"},
        {0x455cae, "80fa2d7206"}, {0x455cbc, "488d0d4d18d903"},
        {0x455c1e, "80fa267206"}, {0x455c2c, "488d0d8519d903"},
        {0x454b97, "80fa2d7207"}, {0x454ba6, "420fb6843010751e04"},
        {0x454857, "80fa267207"}, {0x454866, "420fb68430b8751e04"},
        {0x587830, "40574883ec208bf983f92f7508"},
        {0x453f3f, "83ff2f0f8dea000000"}, {0x453f80, "83ff2f7d12"},
        {0x4541df, "83ff2f0f8dea000000"}, {0x454220, "83ff2f7d12"},
        {0x74f5a0, "488bd93c307219"}, {0x74c4a3, "80bfa40200002f7219"},
        {0x5d4810, "837afc2e7f02"}, {0x5d4818, "833a2e7f02"}, {0x5d481f, "837a042e7f02"},
        {0x5d5436, "83fa2f0f8d6f010000"}, {0x5d5605, "83fa2e7f68"}, {0x5cff1b, "4183fd2f0f83d3030000"},
        {0x74e055, "83fb307cb6"}, {0x72e48b, "83fb307cb6"},
        {0x5d4804, "488b45d8488b542450"}, {0x58e830, "4963c04c63d2"}, {0x5a9783, "83f830721b"}, {0x5a97ae, "83f8307345"}, {0x58e850, "4c63d24963c0"}, {0x4a69d0, "488bc4554156415748"},
    };
    for (size_t i = 0; i < sizeof sites / sizeof *sites; i++)
        if (!expect(sites[i].rva, sites[i].hex)) { logf_("unexpected game build, nothing patched"); return 0; }

    load_codes();
    if (!g_nextras) return 0;
    g_extra_end = FIRST_EXTRA + g_nextras;

    g_near = g_near_cur = near_alloc_init();
    if (!g_near) { logf_("no near memory"); return 0; }
    logf_("near memory at +0x%llx", (unsigned long long)(g_near - g_base));

    // 1. ID <-> code table (48 entries {id, wchar*}) extended with the extras.
    struct CodeEntry *tab = near_take(sizeof(struct CodeEntry) * (48 + MAX_EXTRAS));
    memcpy(tab, R(0x30afbf0), 48 * sizeof(struct CodeEntry));
    for (int i = 0; i < g_nextras; i++) { tab[48 + i].id = FIRST_EXTRA + i; tab[48 + i].pad = 0; tab[48 + i].code = g_codes[i]; }
    uint8_t count = (uint8_t)(48 + g_nextras);
    retarget_rip(0x57ee26, 3, 7, tab);            // IdToCode: lea rsi, table
    put8(0x57ee3a + 2, count);                    //           cmp ecx, count
    retarget_rip(0x57ef31, 3, 7, (uint8_t *)tab + 8); // CodeToId: lea r15, table+8
    put8(0x57effd + 3, count);                    //           cmp r14d, count
    retarget_rip(0x57f019, 3, 7, tab);            //           lea rcx, table

    // 2. Mask ID -> character ID tables; fourth-row mask IDs are 45..59.
    uint8_t *m45 = near_take(64), *m38 = near_take(64);
    memset(m45, 0x30, 64); memset(m38, 0x30, 64);
    memcpy(m45, R(0x41e7510), 0x2d);
    memcpy(m38, R(0x41e75b8), 0x26);
    for (int i = 0; i < g_nextras; i++) { m45[0x2d + i] = (uint8_t)(FIRST_EXTRA + i); m38[0x2d + i] = (uint8_t)(FIRST_EXTRA + i); }
    put8(0x455cae + 2, 0x2d + MAX_EXTRAS); retarget_rip(0x455cbc, 3, 7, m45);
    put8(0x455c1e + 2, 0x2d + MAX_EXTRAS); retarget_rip(0x455c2c, 3, 7, m38);
    put8(0x454b97 + 2, 0x2d + MAX_EXTRAS); put32(0x454ba6 + 5, (int32_t)(m45 - g_base));
    put8(0x454857 + 2, 0x2d + MAX_EXTRAS); put32(0x454866 + 5, (int32_t)(m38 - g_base));

    // 3. IsCharaValid: extras are always valid.
    g_t[0] = (uint64_t)R(0x58783d); g_t[1] = (uint64_t)R(0x587845);
    hook(0x587830, 13, cave_isvalid);

    // 4. Checks that meant "is a real character" (id < DMY) now also accept extras.
    g_t[2] = (uint64_t)R(0x453f48);  g_t[3] = (uint64_t)R(0x454032); hook(0x453f3f, 9, cave_453f3f);
    g_t[4] = (uint64_t)R(0x453f85);  g_t[5] = (uint64_t)R(0x453f97); hook(0x453f80, 5, cave_453f80);
    g_t[6] = (uint64_t)R(0x4541e8);  g_t[7] = (uint64_t)R(0x4542d2); hook(0x4541df, 9, cave_4541df);
    g_t[8] = (uint64_t)R(0x454225);  g_t[9] = (uint64_t)R(0x454237); hook(0x454220, 5, cave_454220);
    g_t[10] = (uint64_t)R(0x74f5c0); g_t[11] = (uint64_t)R(0x74f5a7); hook(0x74f5a0, 7, cave_74f5a0);
    g_t[12] = (uint64_t)R(0x74c4c5); g_t[13] = (uint64_t)R(0x74c4ac); hook(0x74c4a3, 9, cave_74c4a3);
    g_t[14] = (uint64_t)R(0x5d4816); g_t[15] = (uint64_t)R(0x5d4818); hook(0x5d4810, 6, cave_5d4810);
    g_t[16] = (uint64_t)R(0x5d481d); g_t[17] = (uint64_t)R(0x5d481f); hook(0x5d4818, 5, cave_5d4818);
    g_t[18] = (uint64_t)R(0x5d4825); g_t[19] = (uint64_t)R(0x5d4827); hook(0x5d481f, 6, cave_5d481f);
    g_t[20] = (uint64_t)R(0x5d543f); g_t[21] = (uint64_t)R(0x5d55ae); hook(0x5d5436, 9, cave_5d5436);
    g_t[22] = (uint64_t)R(0x5d560a); g_t[23] = (uint64_t)R(0x5d5672); hook(0x5d5605, 5, cave_5d5605);
    g_t[24] = (uint64_t)R(0x5cff25); g_t[25] = (uint64_t)R(0x5d02f8); hook(0x5cff1b, 10, cave_5cff1b);

    // Diagnostics: log team IDs at battle setup; survive (and log) empty asset paths.
    g_t[26] = (uint64_t)R(0x5d480d); hook(0x5d4804, 9, cave_5d4804);
    g_t[27] = (uint64_t)R(0x4a69d8); hook(0x4a69d0, 8, cave_4a69d0);
    g_t[28] = (uint64_t)R(0x58e836); hook(0x58e830, 6, cave_58e830);
    g_t[29] = (uint64_t)R(0x58e856); hook(0x58e850, 6, cave_58e850);

    // Battle setup fill turned ids >= 0x30 into DMY.
    g_t[30] = (uint64_t)R(0x5a97a3); g_t[31] = (uint64_t)R(0x5a9788); hook(0x5a9783, 5, cave_5a9783);
    g_t[32] = (uint64_t)R(0x5a97b3); g_t[33] = (uint64_t)R(0x5a97f8); hook(0x5a97ae, 5, cave_5a97ae);

    // 5. The list-based selectors (0x74dde0 / 0x72e2f0, not the main grid) keep only the
    //    base roster: their lists hold 48 entries, so extras are not added there.

    logf_("installed: %d extras (0x%x..0x%x)", g_nextras, FIRST_EXTRA, g_extra_end - 1);
    return 1;
}

// base: the mapped DRAGON_BALL_FighterZ.exe; dir: the folder that holds ue4ss\.
__declspec(dllexport) int dbfzslots_install_at(void *base, const wchar_t *dir) {
    if (g_done) return g_done;
    wcscpy(g_dir, dir);
    wchar_t path[MAX_PATH]; wcscpy(path, dir); wcscat(path, L"\\ue4ss\\dbfzslots.log");
    g_log = _wfopen(path, L"w");
    g_done = install((uint8_t *)base) ? 1 : -1;
    return g_done;
}

__declspec(dllexport) int dbfzslots_init(void) {
    // The game jumps into this DLL once patched: never let a UE4SS hot reload
    // (which closes the Lua state and its loaded libraries) unload it.
    HMODULE self;
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN,
                       (LPCWSTR)(void *)dbfzslots_init, &self);
    wchar_t dir[MAX_PATH]; GetModuleFileNameW(NULL, dir, MAX_PATH);
    wchar_t *s = wcsrchr(dir, L'\\'); if (s) *s = 0;
    return dbfzslots_install_at(GetModuleHandleW(NULL), dir);
}

// Loads the select-screen icon textures of the extras with the game's own loader
// (UE4SS's LoadAsset does not work in this build). Called from Lua in the game thread.
struct GameFString { const wchar_t *data; uint64_t flags; int32_t num, max; };
typedef void *(*load_object_fn)(const struct GameFString *path);
// The icons are kept in memory for the whole session (RootSet, like UObject::AddToRoot), so a
// later select screen never gets a texture the garbage collector is destroying. Without it the
// game crashed when the icons were added to the second select screen of a session.
// GUObjectArray (RVA 0x4274390, UE 4.17): Objects at +0x10, Max at +0x18, Num at +0x1C;
// FUObjectItem = {UObject*, int32 Flags, int32 ClusterRootIndex, int32 SerialNumber}.
struct UObjectItem { void *object; volatile LONG flags; int32_t cluster, serial; };
typedef void *(*find_object_fn)(void *cls, void *outer, const wchar_t *name, uint8_t exact);
typedef void *(*static_class_fn)(void);
static int icon_root(void *obj) {
    uint8_t *arr = R(0x4274390);
    struct UObjectItem *items = *(struct UObjectItem **)(arr + 0x10);
    int32_t max = *(int32_t *)(arr + 0x18), num = *(int32_t *)(arr + 0x1c);
    int32_t idx = *(int32_t *)((uint8_t *)obj + 0x0c);
    if (!items || num <= 0 || num > max || idx < 0 || idx >= num) return 0;
    if (items[idx].object != obj) return 0;   // layout guess wrong: do nothing
    InterlockedOr(&items[idx].flags, 1 << 30);
    return 1;
}
// Icon list: ue4ss\Mods\DBFZSlotsIcons\icons.txt, one "CODE /Game/...path.Object" per line.
static int icon_logs;
__declspec(dllexport) int dbfz_load_icons(void *L) {
    (void)L;
    if (!g_base) return 0;
    wchar_t list[MAX_PATH]; wcscpy(list, g_dir); wcscat(list, L"\\ue4ss\\Mods\\DBFZSlotsIcons\\icons.txt");
    FILE *f = _wfopen(list, L"rb");
    if (!f) { logf_("load icons: no icons.txt"); return 0; }
    load_object_fn load = (load_object_fn)R(0x4a69d0);
    char code[16], apath[200];
    while (fscanf(f, "%15s %199s", code, apath) == 2) {
        wchar_t path[200];
        size_t n = strlen(apath);
        for (size_t i = 0; i <= n; i++) path[i] = (wchar_t)(unsigned char)apath[i];
        struct GameFString fs = {path, 0, (int32_t)n + 1, (int32_t)n + 1};
        void *obj = load(&fs);
        find_object_fn find = (find_object_fn)R(0xc87930);
        void *tex = find(((static_class_fn)R(0x267a880))(), (void *)-1, path, 0);
        int rooted = tex ? icon_root(tex) : 0;
        if (icon_logs++ < 60) logf_("load icon %s %s -> %p, found %p, kept %d", code, apath, obj, tex, rooted);
    }
    fclose(f);
    return 0;
}

// Diagnostics: dump 0xd0 bytes at each hex address listed in ue4ss\dbfz_dump_req.txt
// ("name address" per line) into dbfzslots.log. Called from Lua.
__declspec(dllexport) int dbfz_dump_file(void *L) {
    (void)L;
    wchar_t path[MAX_PATH]; wcscpy(path, g_dir); wcscat(path, L"\\ue4ss\\dbfz_dump_req.txt");
    FILE *f = _wfopen(path, L"rb");
    if (!f) { logf_("dump: no request file"); return 0; }
    char name[256]; unsigned long long a;
    while (fscanf(f, "%255s %llx", name, &a) == 2) {
        MEMORY_BASIC_INFORMATION mbi;
        if (!VirtualQuery((void *)a, &mbi, sizeof mbi) || mbi.State != MEM_COMMIT) { logf_("dump %s 0x%llx: not readable", name, a); continue; }
        logf_("dump %s 0x%llx", name, a);
        const uint8_t *p = (const uint8_t *)a;
        for (int i = 0; i < 0xd0; i += 8) {
            uint64_t q; memcpy(&q, p + i, 8);
            logf_("  +0x%02x %016llx (%u, %u)", i, (unsigned long long)q, (unsigned)(q & 0xffffffff), (unsigned)(q >> 32));
        }
    }
    fclose(f);
    return 0;
}

// Entry point for Lua's package.loadlib (lua_CFunction; the Lua state is not used).
__declspec(dllexport) int luaopen_dbfzslots(void *L) { (void)L; dbfzslots_init(); return 0; }

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r) { (void)h; (void)reason; (void)r; return TRUE; }
