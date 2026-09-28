#include <windows.h>
#include <stdio.h>
#include <stdint.h>
typedef int (*install_fn)(void *, const wchar_t *);
typedef void *(*load_fn)(void *fstr);
int wmain(int argc, wchar_t **argv) {
    uint8_t *base = (uint8_t *)LoadLibraryExW(argv[1], NULL, DONT_RESOLVE_DLL_REFERENCES);
    HMODULE dll = LoadLibraryW(L"dbfzslots.dll");
    if (((install_fn)GetProcAddress(dll, "dbfzslots_install_at"))(base, argv[2]) != 1) return 2;
    static uint8_t fs[24] = {0};
    void *r = ((load_fn)(base + 0x4a69d0))(fs);
    printf("empty load -> %p\n", r);
    return 0;
}
