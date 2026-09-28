// Offline test: map the game exe (no code run), apply the patches, dump the result and
// exercise the self-contained patched functions (mask lookup, IsCharaValid for extras).
#include <windows.h>
#include <stdio.h>
#include <stdint.h>

typedef int (*install_fn)(void *, const wchar_t *);
typedef uint32_t (*lookup_fn)(void *obj, int x, int y);
typedef uint8_t (*isvalid_fn)(int id);

int wmain(int argc, wchar_t **argv) {
    // argv[1] = game exe, argv[2] = test dir (with ue4ss\Mods\DBFZSlotsStore\chara_mods.txt), argv[3] = mask raw file
    HMODULE game = LoadLibraryExW(argv[1], NULL, DONT_RESOLVE_DLL_REFERENCES);
    if (!game) { printf("load game failed %lu\n", GetLastError()); return 1; }
    uint8_t *base = (uint8_t *)game;
    printf("game mapped at %p\n", base);
    HMODULE dll = LoadLibraryW(L"dbfzslots.dll");
    if (!dll) { printf("load dll failed %lu\n", GetLastError()); return 1; }
    install_fn inst = (install_fn)GetProcAddress(dll, "dbfzslots_install_at");
    int r = inst(base, argv[2]);
    printf("install -> %d\n", r);
    if (r != 1) return 2;

    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + ((IMAGE_DOS_HEADER *)base)->e_lfanew);
    FILE *f = _wfopen(L"patched.img", L"wb"); fwrite(base, 1, nt->OptionalHeader.SizeOfImage, f); fclose(f);

    // Mask lookup with the real new mask.
    static uint8_t mask[1280 * 720];
    f = _wfopen(argv[3], L"rb"); fread(mask, 1, sizeof mask, f); fclose(f);
    static uint8_t info[0x200]; static uint8_t obj[0x300];
    *(uint8_t **)(info + 0x118) = mask; *(int *)(info + 0x128) = 1280; *(int *)(info + 0x12c) = 720;
    *(uint8_t **)(obj + 0x260) = info; *(float *)(obj + 0x268) = 1.0f / 3; *(float *)(obj + 0x26c) = 1.0f / 3;
    lookup_fn l45 = (lookup_fn)(base + 0x455c40), l38 = (lookup_fn)(base + 0x455bb0);
    // centers (mask pixels) of a few regular slots and the 4th row, in 3840x2160 screen units
    int pts[][2] = {{116, 444}, {638, 450}, {678, 514}, {117, 629}, {195, 631}, {578, 639}, {701, 639}, {1162, 629}, {1239, 629}, {5, 5}};
    for (unsigned i = 0; i < sizeof pts / sizeof *pts; i++) {
        int x = pts[i][0], y = pts[i][1];
        printf("mask(%4d,%3d)=%3u  l45=0x%02x  l38=0x%02x\n", x, y, mask[y * 1280 + x], l45(obj, x * 3, y * 3), l38(obj, x * 3, y * 3));
    }
    isvalid_fn iv = (isvalid_fn)(base + 0x587830);
    for (int id = 0x31; id <= 0x40; id++) if (id <= 0x40) printf("IsCharaValid(0x%x)=%u\n", id, iv(id));
    return 0;
}
