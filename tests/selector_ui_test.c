// Offline test for selector-ui.dll: cave arithmetic with fake announcement objects,
// then install on the game exe mapped without running it (byte checks, jump chain,
// refusal on unexpected bytes). Usage: selector_ui_test.exe <game exe> <dll>
#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

typedef float (*test_fn)(const uint8_t *, float, int);
typedef int (*install_fn)(void *);
typedef void (*shift_fn)(float);
static int fails;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL: "); printf(__VA_ARGS__); printf("\n"); } else { printf("ok: "); printf(__VA_ARGS__); printf("\n"); } } while (0)

static void make(uint8_t *o, uint32_t state, const char *key) {
    memset(o, 0, 0x70); memcpy(o, &state, 4); strncpy((char *)o + 0x24, key, 31);
}

int wmain(int argc, wchar_t **argv) {
    setvbuf(stdout, NULL, _IONBF, 0);
    if (argc < 3) { printf("usage\n"); return 1; }
    HMODULE dll = LoadLibraryW(argv[2]);
    if (!dll) { printf("load dll failed %lu\n", GetLastError()); return 1; }
    test_fn t = (test_fn)GetProcAddress(dll, "selector_ui_test");
    install_fn inst = (install_fn)GetProcAddress(dll, "selector_ui_install_at");
    shift_fn setshift = (shift_fn)GetProcAddress(dll, "selector_ui_set_shift");
    CHECK(t && inst && setshift && GetProcAddress(dll, "selector_ui_preload"), "exports present");

    static uint8_t o[0x70];
    struct { uint32_t st; const char *key; int moved; } cases[] = {
        {1, "CHARASELECT_Announce", 1}, {1, "COLORSELECT_Announce", 1},
        {1, "CHARASELECT_", 1}, {0, "CHARASELECT_Announce", 0},
        {1, "CHARASELECTX", 0}, {1, "COLORSELECTX", 0}, {1, "CHARBSELECT_", 0},
        {1, "MAINMENU_Announce", 0}, {1, "", 0}, {2, "COLORSELECT_Announce", 0},
    };
    for (int g = 0; g < 2; g++)
        for (unsigned i = 0; i < sizeof cases / sizeof *cases; i++) {
            make(o, cases[i].st, cases[i].key);
            float in = g ? 29.0f - 140.0f : 1.0f - 140.0f;      // rest position before +764
            float want = in + 764.0f - (cases[i].moved ? 620.0f : 0.0f);
            float got = t(o, in, g);
            CHECK(got == want, "%s state=%u key='%s' -> %.1f (want %.1f)", g ? "guide" : "announce", cases[i].st, cases[i].key, got, want);
        }
    t(NULL, 0, 1); // null object must not crash
    CHECK(t(NULL, 5.0f, 0) == 769.0f, "null announce object leaves position unchanged");
    setshift(584.0f); make(o, 1, "CHARASELECT_Announce");
    CHECK(t(o, 0.0f, 1) == 180.0f, "configurable shift 584");
    setshift(5000.0f); CHECK(t(o, 0.0f, 1) == 64.0f, "shift clamped to 700");
    setshift(620.0f);

    typedef int (*roster_fn)(const wchar_t *, wchar_t *, int);
    roster_fn roster = (roster_fn)GetProcAddress(dll, "selector_ui_test_roster");
    wchar_t last[128] = L"";
    int nr = roster ? roster(L"D:\\Games\\Dragon Ball FighterZ\\RED\\Binaries\\Win64\\ue4ss\\Mods\\DBFZSlotsStore\\chara_mods.txt", last, 128) : -1;
    CHECK(nr == 14, "roster has %d extras", nr);
    CHECK(!wcscmp(last, L"/Game/UI/CharaSelect_S3/tex/CS_CharacterImage_EXG.CS_CharacterImage_EXG"), "last path %ls", last);

    HMODULE game = LoadLibraryExW(argv[1], NULL, DONT_RESOLVE_DLL_REFERENCES);
    if (!game) { printf("load game failed %lu\n", GetLastError()); return 1; }
    uint8_t *b = (uint8_t *)((uintptr_t)game & ~(uintptr_t)3);
    uint8_t before1[8], before2[9];
    { int32_t d; memcpy(&d, b + 0x453a7c + 1, 4); CHECK(b[0x453a7c] == 0xe8 && 0x453a81 + d == 0xc87930, "site 453a7c calls StaticFindObject"); }
    { int32_t d; memcpy(&d, b + 0x453cec + 1, 4); CHECK(b[0x453cec] == 0xe8 && 0x453cf1 + d == 0xc87930, "site 453cec calls StaticFindObject"); }
    memcpy(before1, b + 0x5c98ce, 8); memcpy(before2, b + 0x5ca236, 9);
    DWORD old; VirtualProtect(b + 0x5ca236, 9, PAGE_EXECUTE_READWRITE, &old);
    b[0x5ca236 + 8] ^= 0xff;
    CHECK(inst(b) == -1, "refuses when bytes differ");
    CHECK(!memcmp(b + 0x5c98ce, before1, 8), "first site untouched after refusal");
    b[0x5ca236 + 8] ^= 0xff; VirtualProtect(b + 0x5ca236, 9, old, &old);

    CHECK(inst(b) == 1, "installs on real exe image");
    uint32_t rv[4] = {0x5c98ce, 0x5ca236, 0x453a7c, 0x453cec}; int sz[4] = {8, 9, 5, 5};
    for (int i = 0; i < 4; i++) {
        uint8_t *p = b + rv[i];
        int nops = 1; for (int k = 5; k < sz[i]; k++) nops &= p[k] == 0x90;
        CHECK(p[0] == (i < 2 ? 0xe9 : 0xe8) && nops, "site +%x is %s rel32 + nops", rv[i], i < 2 ? "jmp" : "call");
        int32_t d; memcpy(&d, p + 1, 4); uint8_t *stub = p + 5 + d;
        uint64_t tgt; memcpy(&tgt, stub + 6, 8);
        CHECK(stub[0] == 0xff && stub[1] == 0x25 && !stub[2] && !stub[3] && !stub[4] && !stub[5], "stub %d is jmp [rip]", i);
        CHECK(tgt > (uint64_t)(uintptr_t)dll && tgt < (uint64_t)(uintptr_t)dll + 0x200000, "stub %d jumps into selector-ui.dll", i);
    }
    CHECK(inst(b) == 1, "second install is a no-op");
    CHECK(t(o, 0, 1) == -99999.0f, "test hook disabled after install");
    printf(fails ? "\n%d FAILED\n" : "\nALL PASSED\n", fails);
    return fails != 0;
}
