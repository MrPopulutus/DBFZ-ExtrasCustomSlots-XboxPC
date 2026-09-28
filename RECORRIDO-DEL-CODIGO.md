# Recorrido del código

La DLL principal amplía los identificadores de personaje del ejecutable de Microsoft Store. Los módulos Lua dibujan los iconos adicionales y las herramientas Python convierten las descargas de personajes en el PC del usuario. La inspiración y las aportaciones de terceros figuran en [CREDITOS.md](CREDITOS.md).

Las direcciones son RVA del ejecutable de Microsoft Store comprobado. Los fragmentos están abreviados para explicar el funcionamiento y pueden omitir comprobaciones o usar marcadores; consulta los archivos fuente antes de modificar o compilar.

Índice:

1. [Cadena de arranque](#1-cadena-de-arranque)
2. [`lua/DBFZSlotsStore/main.lua`: cargar la DLL principal](#2-luadbfzslotsstoremainlua-cargar-la-dll-principal)
3. [`src/dbfzslots.c`: el parche principal](#3-srcdbfzslotsc-el-parche-principal)
4. [`src/caves.S`: las cuevas en ensamblador](#4-srccavess-las-cuevas-en-ensamblador)
5. [`lua/DBFZSlotsIcons/main.lua`: iconos de la 4ª fila](#5-luadbfzslotsiconsmainlua-iconos-de-la-4ª-fila)
6. [`lua/DBFZSlotsUIFix/main.lua` + `src/selector_ui.c` + `src/selector_ui.S`: barra y retratos](#6-el-arreglo-de-la-pantalla-barra-de-ayuda-y-retratos-grandes)
7. [`config/`: los archivos de datos](#7-config-los-archivos-de-datos)
8. [`tools/inspect_pak.py` y el formato pak](#8-toolsinspect_pakpy-y-el-formato-pak)
9. [`tools/build_char.py`: dar a un personaje su propio código](#9-toolsbuild_charpy-dar-a-un-personaje-su-propio-código)
10. [`tools/fix_preload_dependencies.py`: el arreglo de Sol y Granolah](#10-toolsfix_preload_dependenciespy-el-arreglo-de-sol-y-granolah)
11. [`tools/build_texts.py`: nombres y listas de comandos](#11-toolsbuild_textspy-nombres-y-listas-de-comandos)
12. [`tools/montar_extras.py`: el montaje con un solo comando](#12-toolsmontar_extraspy-el-montaje-con-un-solo-comando)
13. [`tools/instalar.py`: el instalador](#13-toolsinstalarpy-el-instalador)
14. [`tests/`: pruebas sin juego](#14-tests-pruebas-sin-juego)
15. [Dónde cambiar cada cosa](#15-dónde-cambiar-cada-cosa)

## 1. Cadena de arranque

```
Windows abre DRAGON_BALL_FighterZ.exe
  └─ carga dwmapi.dll desde la carpeta del juego (cargador de UE4SS)
       └─ UE4SS.dll lee ue4ss/Mods/mods.txt y ejecuta cada módulo Lua activo
            ├─ DBFZSlotsStore/Scripts/main.lua  → package.loadlib(dbfzslots.dll)  → parchea IDs, rejilla, validez y combate
            ├─ DBFZSlotsIcons/Scripts/main.lua  → dibuja los iconos de la 4ª fila al aparecer la selección
            └─ DBFZSlotsUIFix/Scripts/main.lua  → package.loadlib(selector-ui.dll) → barra de ayuda y retratos
```

Las dos DLL son DLL normales de Windows con una función exportada `luaopen_*`. `package.loadlib` de Lua las carga y llama a esa función una vez. No usan Lua para nada más: parchean el juego en marcha y se quedan fijas en memoria.

## 2. `lua/DBFZSlotsStore/main.lua`: cargar la DLL principal

```lua
local src = debug.getinfo(1, "S").source                       -- "@D:\...\DBFZSlotsStore\Scripts\main.lua"
local p = src:sub(2):gsub(string.char(92), "/")
local dir = p:match("^(.*)/[Ss]cripts/main%.lua$")             -- la carpeta del módulo
table.insert(candidates, dir .. "/dbfzslots.dll")
...
local init, e = package.loadlib(path, "luaopen_dbfzslots")
if init then init() ... return end
```

Saca su propia carpeta de la ruta del script (así no depende de la carpeta actual), prueba varias rutas posibles, carga la DLL y llama a `luaopen_dbfzslots`. Todo va dentro de `pcall`: si algo falla, se apunta en `UE4SS.log` en vez de parar UE4SS.

## 3. `src/dbfzslots.c`: el parche principal

### 3.1 Constantes y variables globales

```c
#define FIRST_EXTRA 0x31
#define MAX_EXTRAS 15  // IDs 0x31..0x3f; mask ids 45..59 (4th row)

uint32_t g_extra_end = FIRST_EXTRA;           // primer ID después del último extra (lo leen las cuevas)
__declspec(dllexport) uint64_t g_t[64];       // direcciones absolutas para volver al juego
static wchar_t g_codes[MAX_EXTRAS][8];        // "PCO", "GHB", ... leídos de chara_mods.txt
```

El juego usa `0x00`–`0x2E` para los personajes reales, `0x2F` para DMY (personaje vacío) y `0x30` para MAX/ninguno. Los extras empiezan en `0x31`, así las marcas del juego siguen significando lo mismo. Todas las cuevas comparan con `g_extra_end`.

### 3.2 Puntos de entrada

```c
__declspec(dllexport) int luaopen_dbfzslots(void *L) { (void)L; dbfzslots_init(); return 0; }

__declspec(dllexport) int dbfzslots_init(void) {
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN, ...);  // no descargar nunca
    GetModuleFileNameW(NULL, dir, MAX_PATH);  ...                                                    // carpeta Win64 del juego
    return dbfzslots_install_at(GetModuleHandleW(NULL), dir);
}
```

`GET_MODULE_HANDLE_EX_FLAG_PIN` es importante: cuando el juego ya salta a esta DLL, descargarla (por ejemplo, al recargar UE4SS con Ctrl+R) cerraría el juego. `GetModuleHandleW(NULL)` es la dirección donde está cargado el ejecutable del juego. `dbfzslots_install_at` abre `ue4ss\dbfzslots.log` y llama a `install()`. Las pruebas llaman directamente a `dbfzslots_install_at` con una copia del ejecutable cargada en memoria.

### 3.3 Primero la seguridad: `expect()` en cada sitio

```c
static int expect(uint32_t rva, const char *hex) {       // compara los bytes del juego con los esperados
    for (...) if (R(rva)[i] != (uint8_t)v) { logf_("MISMATCH at +0x%x ..."); return 0; }
    return 1;
}
...
static const struct { uint32_t rva; const char *hex; } sites[] = {
    {0x57ee26, "488d35c30db302"}, {0x57ee3a, "83f930"}, ...  // 34 sitios
};
for (...) if (!expect(sites[i].rva, sites[i].hex)) { logf_("unexpected game build, nothing patched"); return 0; }
```

Antes de escribir un solo byte, compara los 34 sitios con los bytes del ejecutable probado. Si hay una sola diferencia, no parchea nada. Por eso la DLL es segura en otra versión del juego: sencillamente no hace nada.

### 3.4 Leer el roster

```c
static void load_codes(void) {
    ... L"\\ue4ss\\Mods\\DBFZSlotsStore\\chara_mods.txt"
    while (g_nextras < MAX_EXTRAS && fgets(line, sizeof line, f)) {
        ... // quita espacios, salta líneas vacías, hasta 7 caracteres
        logf_("extra 0x%x = %.*s", FIRST_EXTRA + g_nextras, (int)n, p);
        g_nextras++;
    }
}
```

La línea N pasa a ser el ID `0x30 + N`, y `g_extra_end = FIRST_EXTRA + g_nextras`.

### 3.5 Herramientas que usan todos los parches

```c
static uint8_t *near_alloc_init(void)    // reserva 64 KB a menos de 2 GB del ejecutable
static void *near_take(size_t n)         // toma n bytes de ese bloque (alineados a 16)
static void retarget_rip(uint32_t rva, int doff, int len, void *abs)   // reescribe un desplazamiento relativo a rip
static void hook(uint32_t rva, int n, void *cave)                      // jmp rel32 -> stub de 14 bytes -> cueva
```

- Un `jmp rel32` solo alcanza ±2 GB, y la DLL puede estar más lejos. Por eso `hook()` escribe en el juego un `jmp` de 5 bytes a un **stub** que está en el bloque cercano, y ese stub hace `jmp qword ptr [rip+0]` con la dirección completa de 64 bits de la cueva. Los bytes sobrantes de la instrucción original se rellenan con `nop`.
- `retarget_rip()` cambia a dónde apunta una instrucción como `lea rsi, [rip+tabla]`: calcula el nuevo desplazamiento de 32 bits hacia nuestra copia de la tabla y lo escribe.
- `write_bytes()` hace `VirtualProtect` → `memcpy` → restaura la protección → `FlushInstructionCache`.

### 3.6 Parche 1: tabla ID ↔ código

```c
struct CodeEntry { int32_t id; int32_t pad; const wchar_t *code; };
struct CodeEntry *tab = near_take(sizeof(struct CodeEntry) * (48 + MAX_EXTRAS));
memcpy(tab, R(0x30afbf0), 48 * sizeof(struct CodeEntry));           // las 48 entradas del juego
for (i...) { tab[48 + i].id = FIRST_EXTRA + i; tab[48 + i].code = g_codes[i]; }
retarget_rip(0x57ee26, 3, 7, tab);            // IdToCode:  lea rsi, tabla
put8(0x57ee3a + 2, count);                    //            cmp ecx, count
retarget_rip(0x57ef31, 3, 7, (uint8_t *)tab + 8); // CodeToId: lea r15, tabla+8
put8(0x57effd + 3, count);                    //            cmp r14d, count
retarget_rip(0x57f019, 3, 7, tab);            //            lea rcx, tabla
```

El juego convierte IDs en códigos (`0x00` → `L"GKS"`) con una tabla de 48 entradas en `0x30AFBF0`, que leen `IdToCode` (`0x57EE00`) y `CodeToId` (`0x57EF00`). La copiamos, añadimos los extras y hacemos que las tres instrucciones `lea` y los dos límites de bucle apunten a la copia más grande. Desde ese momento el juego sabe que `0x31` es `L"PCO"`, y con eso construye todas las rutas de archivos (`/Game/Chara/PCO/...`).

### 3.7 Parche 2: máscara del cursor → personaje

```c
uint8_t *m45 = near_take(64), *m38 = near_take(64);
memset(m45, 0x30, 64); memset(m38, 0x30, 64);           // 0x30 = ninguno
memcpy(m45, R(0x41e7510), 0x2d); memcpy(m38, R(0x41e75b8), 0x26);
for (i...) { m45[0x2d + i] = FIRST_EXTRA + i; m38[0x2d + i] = FIRST_EXTRA + i; }
put8(0x455cae + 2, 0x2d + MAX_EXTRAS); retarget_rip(0x455cbc, 3, 7, m45);
...
```

La selección lee el byte de la textura de la máscara (`DBFZSlotsMask.pak`) que hay bajo el cursor y lo convierte en un ID de personaje con estas tablas. Hay dos (de 45 y 38 entradas) para dos disposiciones. Los valores 45–59 de la máscara (la 4ª fila que dibujamos en ella) apuntan ahora a `0x31`–`0x3F`, y se suben los límites (`cmp dl, 0x2D`) para que esos valores se acepten.

### 3.8 Parches 3 a 5: "¿es un personaje de verdad?"

```c
g_t[0] = (uint64_t)R(0x58783d); g_t[1] = (uint64_t)R(0x587845);
hook(0x587830, 13, cave_isvalid);                                   // IsCharaValid
g_t[2] = (uint64_t)R(0x453f48);  g_t[3] = (uint64_t)R(0x454032); hook(0x453f3f, 9, cave_453f3f);
... // 12 sitios más
```

Por todo el juego hay comprobaciones como `cmp edi, 0x2F / jge mal` ("un ID de 0x2F o más no es un personaje"). Cada una recibe una cueva que dice "≤ 0x2E **o** un extra". En cada sitio, `g_t[ok]` y `g_t[mal]` guardan las dos direcciones a las que habría saltado el código original. La lista completa está en la sección 3.2 de `HOW-IT-WORKS.md`.

El último comentario explica lo que **no** se parchea: los selectores en forma de lista (`0x74DDE0`, `0x72E2F0`) tienen 48 entradas, así que los extras solo salen en la rejilla principal.

## 4. `src/caves.S`: las cuevas en ensamblador

Ensamblador de GNU con sintaxis Intel. Todas las cuevas terminan en `jmp qword ptr [rip + g_t + 8*i]`, que vuelve al juego usando la tabla que se llenó en la sección 3.8.

### IsCharaValid

```asm
cave_isvalid:
    cmp ecx, 0x31
    jb 1f                                   ; por debajo de los extras -> código original
    cmp ecx, dword ptr [rip + g_extra_end]
    jae 1f                                  ; por encima del último extra -> código original
    mov al, 1                               ; es un extra: válido
    ret
1:  push rdi                                ; los 13 bytes originales que sobrescribimos
    sub rsp, 0x20
    mov edi, ecx
    cmp ecx, 0x2f
    jne 2f
    jmp qword ptr [rip + g_t + 8*0]
2:  jmp qword ptr [rip + g_t + 8*1]
```

### La comprobación genérica

```asm
.macro REAL_S reg, ok, bad
    cmp \reg, 0x2e
    jle 8f                                  ; personaje real del juego
    cmp \reg, 0x31
    jl 9f                                   ; DMY / ninguno
    cmp \reg, dword ptr [rip + g_extra_end]
    jge 9f                                  ; más allá del último extra
8:  jmp qword ptr [rip + g_t + 8*\ok]
9:  jmp qword ptr [rip + g_t + 8*\bad]
.endm
cave_453f3f: REAL_S edi, 2, 3
```

`REAL_U` es lo mismo con saltos sin signo. `COUNT_SITE` lo hace para el bucle que cuenta los miembros del equipo al preparar el combate (`cmp dword [rdx+desp], 0x2E`), guardando `rax` porque necesita un registro.

### Diagnóstico

`cave_4a69d0` protege el `LoadObject(FString)` del juego: con una ruta vacía el motor se cierra, así que la cueva apunta quién lo pidió y devuelve null. `cave_58e830` y `cave_58e850` apuntan cada llamada de "poner personaje en el lado/miembro X", y `cave_5d4804` los seis IDs del equipo al preparar el combate. Guardan y restauran todos los registros volátiles y los flags (`SAVE_VOLATILE`/`RESTORE_VOLATILE`) y alinean la pila a 16 bytes antes de llamar a C.

## 5. `lua/DBFZSlotsIcons/main.lua`: iconos de la 4ª fila

```lua
local CENTERS = { {117,629}, {195,631}, ... }            -- centros de los 15 espacios en píxeles de la máscara (1280x720)
for _, r in ipairs(readLines(MODS .. "/DBFZSlotsStore/chara_mods.txt", "^%s*(%w%w%w)%s*$")) do codes[#codes + 1] = r[1] end
for _, r in ipairs(readLines(MODS .. "/DBFZSlotsIcons/icons.txt", "^%s*(%w%w%w)%s+(%S+)")) do icons[r[1]] = r[2] end
```

```lua
local function addIcons(host)
    local canvas = host.Icon01.Slot.Parent                  -- el lienzo donde están los iconos del juego
    local imageClass = StaticFindObject("/Script/UMG.Image")
    local loadIcons = package.loadlib(MODS .. "/DBFZSlotsStore/dbfzslots.dll", "dbfz_load_icons")
    if loadIcons then loadIcons() end                       -- carga las texturas de icons.txt con el cargador del juego
    for i, code in ipairs(codes) do
        local tex = StaticFindObject(icons[code])
        local img = StaticConstructObject(imageClass, host.WidgetTree, FName("DBFZExtraIcon_" .. code))
        img:SetBrushFromTexture(tex, false)
        img:SetVisibility(4)                                -- HitTestInvisible: nunca le quita el cursor al juego
        canvas:AddChildToCanvas(img)
        img.Slot:SetAlignment({X = 0.5, Y = 0.5}); img.Slot:SetSize({X = 256, Y = 256})
        img.Slot:SetPosition({X = c[1] * 3, Y = c[2] * 3 + 256})   -- píxeles de la máscara -> unidades del lienzo
        img.Slot:SetZOrder(3)
    end
end
```

```lua
local selectSeen = package.loadlib(MODS .. "/DBFZSlotsUIFix/selector-ui.dll", "selector_ui_select_seen")
LoopAsync(500, function()                                   -- dos veces por segundo, solo lee un número
    if not searching and selectSeen(true) then              -- true una vez tras actividad nueva en la selección
        searching = true
        search(0)                                           -- FindAllOf y añade los iconos
    end
    return false
end)
```

`selector-ui.dll` cuenta las búsquedas de retratos de la pantalla de selección; `selector_ui_select_seen` devuelve su argumento una vez cuando esa cuenta cambia (no enlaza la API de Lua, así que devuelve 1 resultado, su propio argumento, o ninguno). Entonces `search()` busca las listas de iconos con `FindObjects` (que salta los objetos que se están destruyendo) cada 250 ms (hasta 30 veces) y añade una `Image` por cada extra, en el hilo del juego (`ExecuteInGameThread`), a cada una que ya tenga su `Icon01`. No escucha los objetos nuevos ni guarda un widget durante una espera: una versión anterior lo hacía, y el juego se cerraba al terminar un combate de Versus y al volver a la selección desde una revancha (arreglado en la 0.3.2 y la 0.3.3; desde la 0.3.3 `dbfz_load_icons` además deja las texturas de los iconos cargadas toda la sesión). Si falta `selector-ui.dll`, usa `pollEverySecond()`.

## 6. El arreglo de la pantalla: barra de ayuda y retratos grandes

### 6.1 `lua/DBFZSlotsUIFix/main.lua`

```lua
local init = package.loadlib(dir .. "/selector-ui.dll", "luaopen_selector_ui")
init()
local preload = package.loadlib(dir .. "/selector-ui.dll", "selector_ui_preload")
LoopAsync(8000, function()                                  -- cada 8 s, 6 veces
    runs = runs + 1
    ExecuteInGameThread(function() pcall(preload) end)
    return runs >= 6
end)
```

### 6.2 `src/selector_ui.c`: instalación

```c
static const struct Site { uint32_t rva, resume; int size; uint8_t expected[9]; } sites[] = {
    {0x5c98ce, 0x5c98d6, 8, {0xf3,0x0f,0x58,0x35,0x82,0x04,0xb1,0x02}},      // addss xmm6,[764.0]
    {0x5ca236, 0x5ca23f, 9, {0xf3,0x44,0x0f,0x58,0x05,0x19,0xfb,0xb0,0x02}}, // addss xmm8,[764.0]
    {0x453a7c, 0, 5, {0xe8,0xaf,0x3e,0x83,0x00}},                             // call StaticFindObject
    {0x453cec, 0, 5, {0xe8,0x3f,0x3c,0x83,0x00}},                             // call StaticFindObject
};
```

`selector_ui_install_at()`:

1. Hace `memcmp` de los cuatro sitios con `expected`; si alguno no coincide, lo apunta y devuelve `-1`.
2. En los dos sitios de la barra, además lee la constante que usa el `addss` y comprueba que sigue siendo `764.0`.
3. Reserva un bloque cercano y escribe un stub `jmp qword ptr [rip+0]` por sitio.
4. Hace escribibles los cuatro sitios, escribe `jmp rel32` (barra) o `call rel32` (retratos) más los `nop` de relleno y **solo entonces** restaura las protecciones, en orden inverso. Los dos sitios de los retratos están en la misma página de memoria: si se restaurara después del primero, el segundo quedaría en una página de solo lectura.

`luaopen_selector_ui()` fija la DLL en memoria, abre `ue4ss\selector-ui.log`, lee `[bar] shift` de `selector-ui.ini` (limitado a 0–700), lee `chara_mods.txt` en `portrait_paths[]` y llama a la instalación.

### 6.3 `src/selector_ui.S`: la cueva de la barra

```asm
.macro UI_ADJUST reg, destination
    addss \reg, dword ptr [rip + ui_original_base]  ; la instrucción que sustituimos: y += 764
    pushfq
    push rax
    mov rax, qword ptr [rip + ui_announce]          ; objeto del anuncio (RVA 0x46FA450)
    test rax, rax
    jz 9f
    cmp dword ptr [rax], 1                          ; ¿se está mostrando ahora?
    jne 9f
    cmp dword ptr [rax + 0x24], 0x52414843          ; la clave empieza por "CHAR"...
    ...                                             ; "CHARASELECT_" o "COLORSELECT_"
    subss \reg, dword ptr [rip + ui_top_shift]      ; y -= shift (620 por defecto)
9:  pop rax
    popfq
    jmp qword ptr [rip + \destination]              ; vuelve al juego, después de los bytes sustituidos
.endm
ui_guide_cave:    UI_ADJUST xmm6, ui_resume_guide
ui_announce_cave: UI_ADJUST xmm8, ui_resume_announce
```

El juego dibuja el anuncio y la guía de botones en `y = 764 − animación × 140`, en unidades de 1280×720. La cueva hace lo mismo y además resta `shift`, pero solo mientras se ve el anuncio con una clave de la selección, así que los demás menús no cambian. Conserva `rax` y los flags porque las instrucciones siguientes del juego los esperan intactos.

### 6.4 Retratos: `portrait_find()` y `selector_ui_preload()`

```c
static void *portrait_find(void *cls, void *outer, const wchar_t *name, uint8_t exact) {
    find_fn find = (find_fn)(game_base + 0xc87930);             // StaticFindObject
    int portrait = name && wcsstr(name, L"/CS_CharacterImage_") != NULL;
    if (portrait && portrait_count && !find(cls, outer, portrait_paths[0], exact)) {
        for (i...) { if (!find(...portrait_paths[i]...)) load_path(portrait_paths[i]); ... }   // carga los 14
    }
    void *r = find(cls, outer, name, exact);
    if (!r && portrait) { load_path(name); r = find(cls, outer, name, exact); }
    return r;
}
```

Las funciones del juego que ponen el retrato llaman a `StaticFindObject`, que solo devuelve objetos que ya están en memoria. Los retratos de los originales siempre lo están; los de los extras nunca, y por eso todos los extras mostraban a Goku Super Saiyan. `portrait_find` sustituye esas dos llamadas: si no encuentra el retrato, lo carga con el cargador del propio juego (`0x4A69D0`, `load_path()`) y vuelve a buscar.

```c
static int add_to_root(void *obj) {
    uint8_t *arr = game_base + GUOBJECTARRAY_RVA;                       // 0x4274390
    struct UObjectItem *items = *(struct UObjectItem **)(arr + 0x10);
    int32_t num = *(int32_t *)(arr + 0x1c), idx = *(int32_t *)((uint8_t *)obj + 0x0c);
    if (... idx < 0 || idx >= num || items[idx].object != obj) return 0;   // comprobación de estructura
    InterlockedOr(&items[idx].flags, ROOTSET_FLAG);                     // 1 << 30, igual que AddToRoot
    return 1;
}
```

`selector_ui_preload()` (la llama Lua 8 s después de arrancar) carga los 14 retratos una vez y marca cada uno como `RootSet` en la tabla de objetos del motor, lo mismo que hace el propio juego en su `AddToRoot` de `0x2459B5`. Así se quedan en memoria toda la sesión y entrar en la selección no tiene que cargarlos. Si la comprobación de estructura falla, simplemente no pone la marca.

## 7. `config/`: los archivos de datos

| Archivo | Formato |
|---|---|
| `chara_mods.txt` | Un código por línea, ASCII, sin BOM. Línea N = ID `0x30+N` = espacio N de la 4ª fila. |
| `icons.txt` | `CÓDIGO /Game/Ruta/Textura.Textura` por línea. |
| `selector-ui.ini` | `[bar]` `shift=620` (0 = posición original). |
| `MemberVariableLayout.ini` | Para UE4SS: la versión de Store tiene `TArray`/`FString` de 24 bytes, así que los campos de `UStruct`, `UFunction` y `UEnum` están 16 bytes más adelante de lo que UE4SS supone. Valores medidos. |
| `mods.txt` | Lista de módulos de UE4SS: `DBFZSlotsStore`, `DBFZSlotsIcons` y `DBFZSlotsUIFix` a `1`, en ese orden. |

## 8. `tools/inspect_pak.py` y el formato pak

```python
def read_pak(path, output=None):
    f.seek(-44, 2)
    magic, ver, offset, size, digest = struct.unpack('<IIQQ20s', f.read(44))   # pie del archivo
    assert magic == 0x5a6f12e1 and ver in (3, 4)
    f.seek(offset); index = f.read(size)                                        # índice
    mount = string(); count = ...
    for _ in range(count):
        name = string()
        pos, packed, raw, method = struct.unpack('<QQQI', r.read(28)); sha = r.read(20)
        if method: blocks = [struct.unpack('<QQ', r.read(16)) for _ in range(nb)]
        encrypted, blocksize = struct.unpack('<BI', r.read(5))
```

Un pak de UE4 (versión 3/4, la de DBFZ) tiene: los datos de los archivos, luego un índice (punto de montaje y una entrada por archivo con posición, tamaños, compresión, SHA-1 y bloques comprimidos) y al final un pie de 44 bytes con el número mágico `0x5A6F12E1`, dónde está el índice y su SHA-1. `write_pak()` de `build_char.py` escribe el mismo formato: zlib, un bloque por archivo, montaje `../../../`.

## 9. `tools/build_char.py`: dar a un personaje su propio código

`python build_char.py NUEVO BASE mod.pak [--keep A,B] [--sub VIEJO:NUEVO] [--keep-refs]`

### Los nombres de un asset y su huella

```python
def names(b):                                   # la tabla de nombres de un .uasset
    folderlen = struct.unpack_from('<i', b, 28)[0]
    p = 32 + folderlen + 4
    count, offset = struct.unpack_from('<ii', b, p)
    for _ in range(count):
        n = ...; size = abs(n) * (2 if n < 0 else 1); enc = 'utf-16-le' if n < 0 else 'utf8'
        yield text, offset, size, hpos, enc      # dónde está el texto y dónde su huella

def namehash(s, enc):                            # huella de FName de UE4: CRC del texto en mayúsculas + CRC32
    up = ''.join(chr(ord(c) - 32) if 'a' <= c <= 'z' else c for c in s)
    for b in up.encode(enc): h = (h >> 8) ^ table[(h ^ b) & 255]
    return (h & 65535) | ((zlib.crc32(s.encode('utf-32-le')) & 65535) << 16)
```

### Renombrar

```python
def make_conv(base, new):
    rx_path = re.compile(r'(/chara/)' + base + '(/|$)', re.I)       # /Game/Chara/YMN/... -> /Game/Chara/SBG/...
    rx_data = re.compile(r'^(BBS_|COL_)' + base + '(EF)?$', re.I)    # BBS_YMN -> BBS_SBG (scripts y colores)

def convert_uasset(b, conv, report, path):
    for s, start, size, hpos, enc in names(b):
        t = conv(s)
        data = (t + '\0').encode(enc); assert len(data) == size   # mismo tamaño: los códigos tienen 3 letras
        new[start:start + size] = data
        ... # mantiene el tipo de huella que usaba el archivo: 0, de 16 bits o de 32 bits
        struct.pack_into('<I', new, hpos, nh)

def convert_uexp(b, base, new):                  # reemplazo directo de /Chara/BASE/ en ASCII y UTF-16
```

Como el código viejo y el nuevo miden lo mismo, cada texto conserva su tamaño y las posiciones dentro del archivo no cambian nunca. Solo se reescriben el texto y su huella.

### `main()` paso a paso

1. Lee todos los archivos de `Chara/<BASE>/` **del juego** (`pakchunk0-WinAnvil.pak`).
2. Pone encima los del mod. Los de `Chara/<BASE>/` sustituyen a los del juego. Los de los personajes de `--sub` reciben su propia copia. Las carpetas de `--keep` se copian. Los archivos nuevos de `Shared/` se quedan. Los que sobrescriben archivos compartidos del juego y los de otros personajes se saltan y se apuntan en `report['skipped']`.
3. Renombra las rutas (`rename_path`) y el contenido (`convert_uasset`, `convert_uexp` y los reemplazos de `--sub`).
4. Comprueba que existe cada referencia `/Game/Chara/NUEVO/...` (`missing_refs`).
5. Escribe `paks/chars/DBFZX_<NUEVO>.pak` y un informe JSON.

## 10. `tools/fix_preload_dependencies.py`: el arreglo de Sol y Granolah

```python
CLASSES = {'REDPawnMaterials', 'REDMeshMaterialSet', 'REDAnimSet'}
def repair(b, x):
    ... # solo assets de un único export de esas clases
    # a su lista CreateBeforeSerializationDependencies le faltan imports que usa:
    # los añade y corrige los recuentos, el tamaño de la cabecera, SerialOffset y BulkDataStartOffset
```

Unreal carga lo que necesita un asset a partir de una lista de precarga que va en su cabecera. Las listas de materiales de colores de Sol y el conjunto de animaciones de Granolah usaban objetos que no estaban en esa lista, y por eso no se cargaban a tiempo: Sol se cerraba con `MI_BaseWep` y Granolah se quedaba quieto en el Rolling Kick. El script añade las entradas que faltan a la cabecera y deja el `.uexp` idéntico byte a byte. Se puede ejecutar dos veces sin que cambie nada.

## 11. `tools/build_texts.py`: nombres y listas de comandos

```python
def key_for(base, extra, key):
    pats = [(rf'^CMD{base}(\d\d\w*)$', rf'CMD{extra}\1'), (rf'^{base}_ASSIST_(\d\d)$', rf'{extra}_ASSIST_\1'),
            (rf'^CHARA_NAME_(L|S|DEMO)_{base}$', rf'CHARA_NAME_\1_{extra}'), ...]
```

`Localization/<IDIOMA>/REDGame.uexp` es un texto UTF-16 con pares `CLAVE\r\nVALOR\r\n`. Para cada uno de los 13 idiomas, `patch()` copia las claves del personaje base al código del extra y pone los nombres (las tablas en español reciben los nombres en español). Después aplica los textos propios del mod (`text.json` o su `REDGame`) y corrige los dos campos de longitud y el tamaño en el `.uasset`.

## 12. `tools/montar_extras.py`: el montaje con un solo comando

Los datos del principio lo dirigen todo:

```python
FUENTES = {  # cómo reconocer cada descarga
    'dio':    dict(pak='DIOCharacterMoveset.pak', chara='CEN', con=['CEN'], web=...),   # DIO sobre Cell: debe traer CEN
    'raditz': dict(pak='RaditzMoveset.pak', chara='MGS', con=['MGS'], web=...),
    ...
}
PROBADO = {'dio': 'ec688ed7...', ...}      # SHA-256 de cada descarga probada
ROSTER = [('PCO', dict(tipo='convertir', fuente='piccolo', base='PCN', args=[], ...)),
          ('DIO', dict(tipo='convertir', fuente='dio', base='CEN', args=['--keep', 'DIO,WLD'], ...)),
          ('YUG', dict(tipo='convertir', fuente='yugi', base='AVP', args=['--keep', 'YGI', '--keep-refs'], ...)), ...]
```

`main()`:

1. `comprobar()` prueba Pillow, NumPy y etcpak con una imagen de 4×4.
2. Con `--incluir-port`, `preparar_port()` (de `instalar.py`) comprueba la huella del ejecutable y las del paquete, y copia `Game/`.
3. `buscar()` recorre las carpetas de descargas, lee los `.zip` con `zipfile` y los `.rar/.7z` con el `tar.exe` de Windows en una carpeta temporal, y apunta cada pak con sus carpetas de personaje (`pak_charas`) y su SHA-256.
4. `elegir()` escoge un pak por fuente: primero el de la huella probada; si no, nombre + carpeta principal + reglas `con`/`sin`; si hay varias versiones desconocidas, se salta.
5. Los personajes a los que les falta algo salen del `roster`, y el resto se monta: `build_char.main()` para las 14 conversiones, `fix_preload_dependencies.main()`, `build_werezaru_exg.py`, `build_texts.main()` y `construir_ui()`.
6. Escribe `chara_mods.txt` e `icons.txt` con el roster montado.
7. `proteger_originales()` rechaza cualquier pak que toque alguna de las 85 carpetas de personajes del juego, salvo `VGF` en `DBFZX_VGF.pak`: una carpeta sobrante del juego sobre la que ya está hecha la descarga de Vegeta SSJ4.
8. Compara con `reference-sha256.json` y escribe `informe-montaje.json`.

## 13. `tools/instalar.py`: el instalador

- `pedir_juego()`: pregunta hasta que la carpeta tenga el ejecutable del juego.
- `preparar_port()`: la huella del ejecutable tiene que coincidir, igual que la de cada archivo de `Game/` con `technical-sha256.json`. Luego copia `Game/` a la salida y combina `mods.txt`.
- `main()`: ejecuta `montar_extras.py` como subproceso, muestra su salida en pantalla y en el `.log`, y pregunta si instalar.
- `instalar_salida()`: comprueba que el juego no está abierto (`Get-Process` de PowerShell) y hace copia de cada archivo que va a sobrescribir (comprobada por huella y apuntada en `manifest.json`). Después copia y comprueba cada archivo, y si hay un error restaura lo que ya había escrito. Rechaza cualquier destino fuera de la carpeta del juego. Los archivos que dejó la 0.2.x con nombres antiguos (`RETIRADOS`, `RENOMBRADOS`) van a esa misma copia.
- `idioma.py`: `t(es, en)` elige español o inglés según el idioma de Windows (`GetUserDefaultUILanguage`); `DBFZ_LANG` obliga a uno.

## 14. `tests/`: pruebas sin juego

- `selector_ui_test.c`: `LoadLibraryExW(exe, DONT_RESOLVE_DLL_REFERENCES)` carga el juego en memoria sin ejecutarlo. Prueba las cuevas de la barra con anuncios falsos (clave y estado correctos, clave equivocada, oculto, vacío), el límite del ini y la lectura del roster. Después instala sobre el ejecutable cargado, comprueba que cada sitio se convirtió en `jmp`/`call` hacia un stub que salta a la DLL, y que con un byte cambiado se niega sin escribir nada.
- `harness.c` (+ `cavetest.c`, `callsite.S`, `emptytest.c`, `settest.c`): lo mismo para `dbfzslots.dll`. Aplica los parches al ejecutable cargado y ejecuta la consulta de máscara y `IsCharaValid` ya parcheadas.
- `check_lua.py`: comprueba la sintaxis de los módulos con Lua 5.4.

## 15. Dónde cambiar cada cosa

| Quiero… | Cambia |
|---|---|
| Añadir o reordenar personajes | `config/chara_mods.txt` + `icons.txt`, y dale a cada código sus paks (`build_char.py`) |
| Mover la barra de ayuda | `config/selector-ui.ini` → `shift` |
| Mover los iconos de la 4ª fila | `CENTERS` en `lua/DBFZSlotsIcons/main.lua`, y las zonas de la máscara en `DBFZSlotsMask.pak` para que coincidan |
| Más de 15 extras | `MAX_EXTRAS`, el tamaño de las tablas y cada sitio de la sección 3 de `HOW-IT-WORKS.md`, más zonas nuevas en la máscara |
| Otro ejecutable (un parche, otra edición) | Volver a encontrar cada sitio y actualizar las tablas `sites[]` y todas las RVA (`HOW-IT-WORKS.md` §9); nunca quitar las comprobaciones de bytes |
| Añadir un personaje al montaje automático | `FUENTES`, `PROBADO` y `ROSTER` en `tools/montar_extras.py`, y luego actualizar `reference-sha256.json` |
