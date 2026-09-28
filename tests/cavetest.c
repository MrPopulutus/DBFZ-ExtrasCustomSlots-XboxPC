#include <windows.h>
#include <stdio.h>
#include <stdint.h>
extern uint32_t call_site(void *site, uint64_t rdi, uint64_t rax, uint64_t rdx, uint64_t r13);
extern void t_ok(void), t_bad(void);
typedef int (*install_fn)(void *, const wchar_t *);
int wmain(int argc, wchar_t **argv) {
    uint8_t *base = (uint8_t *)LoadLibraryExW(argv[1], NULL, DONT_RESOLVE_DLL_REFERENCES);
    HMODULE dll = LoadLibraryW(L"dbfzslots.dll");
    if (((install_fn)GetProcAddress(dll, "dbfzslots_install_at"))(base, argv[2]) != 1) return 2;
    uint64_t *gt = (uint64_t *)GetProcAddress(dll, "g_t");
    for (int i = 2; i < 26; i += 2) { gt[i] = (uint64_t)t_ok; gt[i + 1] = (uint64_t)t_bad; }
    static int32_t team[3];
    struct { uint32_t rva; int kind; } s[] = {
        {0x453f3f, 0}, {0x453f80, 0}, {0x4541df, 0}, {0x454220, 0},   // edi
        {0x74f5a0, 1},                                                // al
        {0x5d4810, 2}, {0x5d4818, 3}, {0x5d481f, 4},                  // dword [rdx-4|0|4]
        {0x5d5436, 5}, {0x5d5605, 5},                                 // edx
        {0x5cff1b, 6},                                                // r13d
    };
    int ids[] = {0, 0x2e, 0x2f, 0x30, 0x31, 0x36, 0x37, 0x3f, -1};
    for (unsigned k = 0; k < sizeof s / sizeof *s; k++) {
        printf("%06x:", s[k].rva);
        for (unsigned j = 0; j < sizeof ids / sizeof *ids; j++) {
            int id = ids[j]; uint32_t r;
            if (s[k].kind == 0) r = call_site(base + s[k].rva, (uint32_t)id, 0, 0, 0);
            else if (s[k].kind == 1) r = call_site(base + s[k].rva, 0, (uint8_t)id, 0, 0);
            else if (s[k].kind <= 4) { team[0] = team[1] = team[2] = id; r = call_site(base + s[k].rva, 0, 0, (uint64_t)&team[1], 0); }
            else if (s[k].kind == 5) r = call_site(base + s[k].rva, 0, 0, (uint32_t)id, 0);
            else r = call_site(base + s[k].rva, 0, 0, 0, (uint32_t)id);
            printf(" %x:%s", id & 0xff, r == 1 ? "ok" : r == 2 ? "--" : "??");
        }
        printf("\n");
    }
    return 0;
}
