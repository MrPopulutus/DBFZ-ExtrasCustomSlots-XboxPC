# El ADN del mod: qué es, qué hace y cómo funciona, paso a paso

**Aviso de IA: el código, las herramientas y la documentación de este mod se hicieron con ayuda de IA (Claude de Anthropic y ChatGPT/Codex de OpenAI) bajo la dirección de MrPopulutus. No contiene arte, audio ni voces generados con IA.**

Implementación para Microsoft Store / Xbox PC con parches nativos, módulos Lua y un conversor local de personajes. Consulta CREDITOS.md para la inspiración y las aportaciones.

Este documento es para dos tipos de personas:

- **Quien no quiere ejecutar nada sin saber qué hace.** Aquí está, paso a paso, todo lo que pasa en tu PC: qué se lee, qué se escribe, dónde y por qué. También cómo comprobarlo tú mismo y cómo instalarlo a mano.
- **Quien quiere entenderlo o construir algo más grande.** Aquí está la lógica completa, de dónde sale cada pieza y dónde tocar. Para las direcciones exactas del juego y cada parche, sigue con `HOW-IT-WORKS.md` (en inglés).

---

## 1. La idea en un párrafo

DBFZ tiene una lista fija de personajes. Cada uno tiene un **número** (su ID, de `0x00` a `0x2E`) y un **código de tres letras** (`GKS` es Goku Super Saiyan, `VGS` Vegeta, `BDN` Bardock…). Ese código es el nombre de su carpeta dentro del juego (`/Game/Chara/GKS/`), de sus imágenes y de sus textos. Casi todos los mods de personajes de GameBanana son **reemplazos**: sobrescriben los archivos de un personaje existente (Sol Badguy, por ejemplo, reemplaza a Yamcha). Este mod hace otra cosa: **le da a cada personaje nuevo su propio número (`0x31` a `0x3F`) y su propio código**, y añade una **cuarta fila** en la pantalla de selección. Así puedes tener hasta **15 personajes extra** sin perder ninguno de los originales.

Para que eso funcione hacen falta cuatro piezas:

1. **Un parche en memoria del juego** (`dbfzslots.dll`), para que acepte números nuevos.
2. **La pantalla de selección**: iconos de la 4ª fila, barra de ayuda y retratos grandes (módulos `DBFZSlotsIcons` y `DBFZSlotsUIFix`).
3. **La máscara del cursor** (`DBFZSlotsMask.pak`), que dice qué personaje hay bajo cada punto de la pantalla.
4. **Los personajes convertidos**: los archivos de cada mod copiados y renombrados a su código nuevo. Esos **no se incluyen**: los genera en tu PC el script, a partir de las descargas originales de cada autor.

---

## 2. Qué trae el zip, archivo por archivo

| Carpeta o archivo | Qué es | Quién lo hizo |
|---|---|---|
| `INSTALAR.cmd` | Dos líneas: ejecuta `tools\instalar.py` con el Python incluido y espera una tecla al final. Ábrelo con el Bloc de notas y lo verás. | Este proyecto |
| `LEEME-PRIMERO.txt` | Instrucciones cortas. | Este proyecto |
| `Game\` | Lo que se copia sobre la carpeta del juego. Ver la tabla siguiente. | Mezcla (ver abajo) |
| `tools\` | Scripts de Python: instalador, montaje de personajes, conversor, textos, retratos, reparación de precargas, comprobaciones. Todo en texto legible. | Este proyecto |
| `tools\reference-sha256.json` | Huellas SHA-256 del resultado probado: los 18 paks y 2 configuraciones que deben salir si usas las mismas descargas. | Este proyecto |
| `tools\technical-sha256.json` | Huellas de cada archivo de `Game\`. El instalador las comprueba antes de copiar nada: si alguien ha cambiado un archivo del zip, se para. | Este proyecto |
| `source\` | Código fuente en C y ensamblador de las dos DLL, y pruebas que funcionan sin abrir el juego. | Este proyecto |
| `runtime\python\` | Python 3.12.14 portátil de Windows (el oficial "embeddable") con Pillow, NumPy, etcpak, texture2ddecoder y archspec, sacados de PyPI. Solo se usa para ejecutar los scripts; no se instala en Windows. | Python Software Foundation y autores de cada librería |
| `docs\` | Esta guía, la técnica (`HOW-IT-WORKS.md`), la guía larga en español, versiones probadas y créditos. | Este proyecto |
| `licenses\` | Licencias de los componentes de terceros. | — |

Dentro de `Game\RED\Binaries\Win64\`:

| Archivo | Qué hace | Origen |
|---|---|---|
| `dwmapi.dll` | Cargador de UE4SS. Windows carga este archivo al abrir el juego porque está en su carpeta; él carga UE4SS. | Versión oficial de UE4SS (MIT) |
| `ue4ss\UE4SS.dll`, `UE4SS-settings.ini`, módulos Lua estándar | **UE4SS**, la herramienta de modding abierta que permite ejecutar código dentro de juegos de Unreal Engine. | Equipo UE4SS, sin cambios (MIT) |
| `ue4ss\MemberVariableLayout.ini` | Medidas internas del motor de esta versión del juego, que UE4SS necesita para no equivocarse. | Este proyecto |
| `ue4ss\Mods\mods.txt` | Lista de módulos activos. | Este proyecto |
| `ue4ss\Mods\DBFZSlotsStore\` | `dbfzslots.dll`, el parche de los espacios, el Lua que la carga y `chara_mods.txt`, la lista de personajes extra en orden. | Este proyecto |
| `ue4ss\Mods\DBFZSlotsIcons\` | Lua que dibuja los iconos de la 4ª fila, más `icons.txt`. | Este proyecto |
| `ue4ss\Mods\DBFZSlotsUIFix\` | `selector-ui.dll` (barra de ayuda arriba y retratos grandes), su `.ini` y su Lua. | Este proyecto |

Y en `Game\RED\Content\Paks\~mods\`: `DBFZSlotsMask.pak` (la máscara del cursor, una copia editada de un archivo del juego) y su `.sig`.

El instalador incluye una máscara de selección editada a partir de un recurso del juego. No incluye el ejecutable, los PAK originales del juego ni paquetes de mods de personajes. Los personajes se montan desde las descargas locales del usuario.

---

## 3. Qué pasa exactamente cuando abres `INSTALAR.cmd`

Todo pasa **sin conexión a internet**, **sin permisos de administrador** y **sin tocar el registro de Windows ni instalar servicios**. Hasta el paso 11, **tu juego no se modifica**.

1. **Arranca el Python incluido** (`runtime\python\python.exe`), no el de tu sistema. Está configurado (`python312._pth`) para usar solo sus propias carpetas.
2. **Idioma.** Mira el idioma de Windows: si está en español, todo sale en español; si no, en inglés. Puedes forzarlo con la variable `DBFZ_LANG=es` o `DBFZ_LANG=en`.
3. **Carpeta del juego.** Te la pide y comprueba que dentro esté `RED\Binaries\Win64\DRAGON_BALL_FighterZ.exe`. Si la ruta no es correcta, te la vuelve a pedir.
4. **Carpetas de descargas.** Te pide dónde tienes los mods descargados (pueden ser varias, separadas con `;`). Comprueba que existen.
5. **Comprueba las librerías.** Crea una imagen de 4×4 píxeles en memoria, la guarda y la lee, y la comprime como una textura. Si algo falla aquí, se para antes de hacer nada pesado.
6. **Comprueba tu juego y el paquete.**
   - Calcula la huella SHA-256 de tu `DRAGON_BALL_FighterZ.exe` y la compara con la versión probada. Si no coincide (otra versión, Steam…), **se para**: los parches solo valen para ese ejecutable.
   - Calcula la huella de cada archivo de `Game\` y la compara con `technical-sha256.json`. Si alguno falta o está cambiado, se para.
7. **Busca tus descargas.**
   - Recorre las carpetas que diste, subcarpetas incluidas.
   - Abre los `.zip` con Python y los `.rar`/`.7z` con el `tar.exe` que ya trae Windows, y los extrae a una carpeta temporal de Windows (`%TEMP%\dbfzx…`), nunca dentro de tus descargas.
   - Para cada `.pak` mira **tres cosas**: su nombre, qué carpetas de personaje contiene y su huella SHA-256. Así distingue, por ejemplo, la descarga correcta de DIO de otro archivo que se llame igual.
   - Si encuentra la versión exacta probada, usa esa. Si hay una sola versión distinta, la usa con un aviso. Si hay varias versiones distintas y ninguna es la probada, se salta ese personaje y te explica por qué.
   - Si falta algo que un personaje necesita, **se salta ese personaje** y te dice qué descargar y dónde. Los demás siguen adelante.
8. **Monta todo en una carpeta nueva** junto al zip extraído (`DBFZ-montaje-fecha`), **fuera del juego**:
   1. Copia allí los archivos de `Game\`. Si ya tenías `mods.txt`, conserva tus otras líneas y solo activa o desactiva las cuatro del mod.
   2. **Los 14 personajes** se convierten igual (Piccolo Naranja, Gohan Bestia, Goku Dios, Vegeta SSJ4, Raditz, DIO, Yugi, Sol, Sukuna, Omega, Super Vegito, Granolah, Goku SSJ3 y EX Goku): para cada uno lee los archivos del personaje base **desde tu propio juego**, les pone encima los del mod y lo renombra todo al código nuevo (ver sección 5). El resultado es un pak nuevo (`DBFZX_SBG.pak`, por ejemplo).
   3. **Reparación de precargas** para Sol y Granolah (`zzDBFZSlotsPreloadFix.pak`): corrige una lista interna que en los mods originales dejaba sin cargar unos materiales y animaciones. Sin ella, Sol cerraba el juego y Granolah se quedaba quieto en su Rolling Kick.
   4. **Werezaru** (opcional): pasa la apariencia de Werezaru a EX Goku, sin cambiar sus movimientos (`zzWerezaruEXG_P.pak`).
   5. **Textos:** lee las 13 tablas de idioma **de tu juego**, copia las entradas del personaje base al código nuevo, pone los nombres y añade los textos propios del mod (lista de comandos, asistencias). Resultado: `DBFZSlotsText.pak`.
   6. **Retratos e iconos:** toma los retratos de cada mod (o del juego si el mod no los trae) y los renombra al código nuevo. Raditz usa los retratos e icono de Bardock del propio juego. Resultado: `DBFZSlotsUI.pak`.
   7. Escribe `chara_mods.txt` e `icons.txt` solo con los personajes que se han montado, en orden. Los que faltan no dejan hueco.
9. **Freno de seguridad.** Revisa cada pak resultante y comprueba que **no cambia a ninguno de los 85 personajes originales del juego**. La única excepción es `VGF`: una carpeta sobrante del juego, sin personaje jugable, sobre la que ya está hecha la descarga de Vegeta SSJ4. Si algo más tocaría a un original (por ejemplo, porque bajaste el mod equivocado), **se para y no instala nada**.
10. **Comprueba el resultado.** Compara las huellas con `reference-sha256.json`. Si usaste exactamente las descargas probadas, los 20 archivos deben ser idénticos byte a byte. Si usaste las probadas y algo no coincide, se para. Escribe `informe-montaje.json` con todo: qué descarga usó, sus huellas y el resultado.
11. **Te pregunta si instalar.** Si pulsas Enter, se queda todo preparado en la carpeta de montaje y **no toca el juego**. Si escribes `S`:
    - Comprueba que el juego está cerrado (con una orden de PowerShell que solo mira si el proceso existe).
    - **Copia de seguridad:** guarda en `copia-antes-de-montar-fecha` todos los archivos del juego que se van a sobrescribir, comprobando cada copia con su huella, y deja un `manifest.json` con la lista.
    - Los archivos que dejó la versión 0.2.x con nombres antiguos (paks de personajes viejos, la máscara y la lista antiguas) pasan a esa copia, para que ningún personaje se cargue dos veces.
    - Copia los archivos al juego uno a uno y verifica cada uno con su huella. Si falla una copia, **deshace todo lo que había copiado** y restaura lo anterior.
    - Nunca escribe fuera de la carpeta del juego: lo comprueba archivo por archivo.
12. **Limpia** la carpeta temporal de Windows. Tus descargas no se modifican.

**Qué se escribe en tu PC en total:** la carpeta `DBFZ-montaje-fecha` y su `.log` (junto al zip extraído), una carpeta temporal que se borra al terminar y, solo si escribes `S`, los archivos del mod dentro del juego más la carpeta de copia de seguridad.

---

## 4. Qué pasa cuando abres el juego

1. **Windows carga `dwmapi.dll`** desde la carpeta del juego (lo hace con cualquier DLL de ese nombre que esté junto al ejecutable). Este cargador inicia **UE4SS**.
2. **UE4SS** lee `mods.txt` y ejecuta, en ese orden, los módulos activos. Los que importan aquí son:
   - **`DBFZSlotsStore`**: su Lua carga `dbfzslots.dll`. La DLL comprueba los bytes originales de **cada** sitio que va a cambiar y, si uno solo no coincide, no cambia nada y lo escribe en el registro. Si todo coincide, parchea **en memoria** (nunca en el `.exe` del disco):
     - amplía la tabla que traduce número ↔ código con los personajes de `chara_mods.txt`;
     - amplía la tabla que traduce "punto de la pantalla" → personaje, para la 4ª fila;
     - hace que el juego considere válidos los números nuevos en la selección, la validación y la preparación del combate.
   - **`DBFZSlotsIcons`**: cuando se abre la pantalla de selección, dibuja encima un icono por cada personaje extra. Es solo imagen: lo que decide qué eliges es la máscara.
   - **`DBFZSlotsUIFix`**: carga `selector-ui.dll`, que:
     - sube la barra de ayuda al borde de arriba solo en la selección de personaje y de color, para que no tape la 4ª fila (altura en `selector-ui.ini`);
     - carga los retratos grandes de los extras unos segundos después de arrancar y los deja en memoria. El juego solo buscaba retratos ya cargados, y por eso antes salía Goku Super Saiyan en todos los extras.
3. **El juego** monta todos los paks de `~mods` (personajes, textos, retratos, máscara) por encima de los suyos, como con cualquier mod.
4. **Registros** para ver qué pasó: `ue4ss\dbfzslots.log`, `ue4ss\selector-ui.log` y `ue4ss\UE4SS.log`.

Nada de esto se conecta a internet. Todo se ha probado **sin conexión**; el juego online no se ha probado.

---

## 5. Cómo se convierte un personaje a su propio espacio

Esto es lo que hace `tools\build_char.py`, el corazón del montaje:

1. Toma **del juego** todos los archivos del personaje base (`Chara/YMN/…` para Sol, que reemplaza a Yamcha).
2. Pone encima los archivos del mod para ese personaje.
3. **Renombra** cada ruta `/Game/Chara/YMN/` a `/Game/Chara/SBG/`, y los nombres internos de datos `BBS_YMN` y `COL_YMN` a `BBS_SBG` y `COL_SBG`. Como los códigos tienen siempre 3 letras, el tamaño de cada nombre no cambia y la estructura del archivo se mantiene. Recalcula las huellas internas de nombres que usa el motor.
4. Los archivos del mod que pertenecen **a otros personajes** no se copian, para no cambiarlos. Si el mod los necesita, se les da una **copia propia** con otro código: Sukuna usa una copia de Whis (`WTN` → `URA`) y Super Vegito una de Vegeta (`VGS` → `VGX`).
5. Los archivos compartidos **nuevos** se conservan; los que sobrescribirían archivos compartidos del juego se omiten, porque cambiarían a todos los personajes.
6. Las carpetas extra propias del mod (`SOL` de Sol, `YGI` de Yugi) se copian tal cual.

Después, los textos y los retratos se generan igual: se copia lo del personaje base con el código nuevo y se aplican los del mod.

---

## 6. Si no quieres ejecutar nada

- **Leerlo todo antes:** `INSTALAR.cmd` y todo `tools\` son texto. Ábrelos con cualquier editor. Busca, por ejemplo, `http`, `socket` o `urllib`: no hay código de red.
- **Solo lo que se copia al juego:** puedes copiar a mano el contenido de `Game\` sobre la carpeta del juego (antes, guarda tu carpeta `RED\Binaries\Win64\ue4ss` y tu `~mods`). Así tendrás el sistema de espacios sin haber ejecutado nada, pero sin personajes: esos los convierte el montaje con el script.
- **Comprobar huellas:** en PowerShell, `Get-FileHash -Algorithm SHA256 <archivo>`. Compáralas con `tools\technical-sha256.json` (archivos del paquete) y `docs\VERSIONES-PROBADAS.md` (descargas probadas).
- **Compilar las DLL tú mismo** desde `source\` (instrucciones en `source\README.md`) y pasar las pruebas sin juego antes de usarlas.
- **Montar sin instalar:** ejecuta `INSTALAR.cmd` y, al final, pulsa Enter en vez de `S`. Te quedas con todo preparado en `DBFZ-montaje-fecha` para revisarlo y copiarlo tú.

---

## 7. Desinstalar

- **Si instalaste con el script:** con el juego cerrado, copia el contenido de la carpeta `copia-antes-de-montar-fecha` sobre la del juego. Luego borra los archivos que el mod añadió; están todos en su `manifest.json`, marcados con `existed: false`.
- **A mano:** con el juego cerrado, borra `RED\Binaries\Win64\dwmapi.dll` y la carpeta `RED\Binaries\Win64\ue4ss`, y saca de `RED\Content\Paks\~mods` los paks del mod (`DBFZ*`, `zz*` y los de los personajes). El juego vuelve a estar como de fábrica.
- Abre siempre el juego desde el menú Inicio o la app de Xbox; abrir el `.exe` directamente da error de inicio de sesión.

---

## 8. Para construir algo más grande

- **Arquitectura completa, cada parche con su dirección y cómo llevarlo a otra versión:** `HOW-IT-WORKS.md`.
- **Reglas para modificarlo sin romperlo:** `../CONTRIBUTING.md`.
- **Añadir tu propio personaje:** convierte su mod con `build_char.py CÓDIGO BASE mod.pak`, añade sus retratos y textos, y pon su código en `chara_mods.txt` (máximo 15).
- **Límites actuales:** 15 espacios, solo en la cuadrícula principal de selección; los retratos grandes de los extras no tienen posición propia guardada en el juego.
- **Ideas:** más espacios (hace falta ampliar la máscara, las tablas y revisar cada comprobación), un selector de roster, o aplicar la misma técnica a otros juegos de Unreal Engine 4.

---

## 9. Glosario

- **Pak**: archivo contenedor de Unreal Engine con los recursos de un juego o de un mod. Los de `~mods` se cargan por encima de los del juego.
- **UE4SS**: herramienta abierta que permite ejecutar scripts Lua y DLL dentro de juegos de Unreal Engine.
- **ID / código**: número y nombre de tres letras con los que el juego identifica a cada personaje.
- **Máscara del cursor**: imagen invisible en la que cada punto de la selección tiene el número de un espacio.
- **Precarga**: lista interna de lo que un archivo necesita tener cargado antes de usarse.
- **SHA-256 (huella)**: número que identifica un archivo exacto; si cambia un solo byte, la huella cambia.
- **RootSet**: marca del motor que impide que un objeto se descargue de la memoria.

## 10. Licencia y créditos

El código, las herramientas y la documentación de este proyecto son **MIT** (`LICENSE.txt`): puedes usarlos, cambiarlos y compartirlos manteniendo el crédito. El juego y cada mod de personaje conservan sus autores y sus licencias. La mayoría son CC BY-NC-ND 4.0: pide permiso a sus autores antes de compartir versiones modificadas. Créditos completos con enlaces: `CREDITOS.md`. Hecho con ayuda de Claude (Anthropic) y ChatGPT/Codex (OpenAI).
