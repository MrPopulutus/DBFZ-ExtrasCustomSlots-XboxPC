#include <windows.h>
#include <stdio.h>
#include <stdint.h>
typedef int (*install_fn)(void *, const wchar_t *);
typedef void (*set_fn)(void *obj, int side, int member, int id);
typedef void (*copy_fn)(void *obj, int side, int member, uint8_t *src);
int wmain(int argc, wchar_t **argv) {
    uint8_t *base = (uint8_t *)LoadLibraryExW(argv[1], NULL, DONT_RESOLVE_DLL_REFERENCES);
    HMODULE dll = LoadLibraryW(L"dbfzslots.dll");
    if (((install_fn)GetProcAddress(dll, "dbfzslots_install_at"))(base, argv[2]) != 1) return 2;
    static uint8_t obj[0x5000], p1[0x100], p2[0x100];
    *(uint8_t **)(obj + 0x45e0) = p1; *(uint8_t **)(obj + 0x45e8) = p2;
    ((set_fn)(base + 0x58e830))(obj, 1, 2, 0x33);
    uint8_t src[0x14] = {0}; src[1] = 0x35;
    ((copy_fn)(base + 0x58e850))(obj, 0, 1, src);
    printf("p2 member2 id=0x%x  p1 member1 id=0x%x\n", p2[0x29 + 2 * 0x14], p1[0x29 + 0x14]);
    return 0;
}
