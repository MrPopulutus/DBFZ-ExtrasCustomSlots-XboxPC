# Montar los 14 extras desde las descargas originales

Modified by MrPopulutus

`montar_extras.py` genera en tu PC los personajes, textos, retratos, precargas y la apariencia Werezaru sobre EX Goku. No incluye ni descarga movesets. No usa Unverum para instalar; puede leer las descargas que tengas en su carpeta.

## Paquete completo y repositorio de código

Este repositorio de código no incluye `INSTALAR.cmd`, `Game/` ni `runtime/`. Las instrucciones siguientes corresponden al ZIP completo del instalador. Los scripts no pueden reconstruir todos esos componentes a partir del repositorio por sí solos.

## Para usarlo sin instalar herramientas

Extrae el ZIP completo y abre **INSTALAR.cmd**, en la carpeta superior. Ya incluye Python portátil, las librerías, UE4SS y el cargador compatibles. El instalador actual no necesita el mod de espacios de Steam. Descarga por separado los personajes que quieras.

Las descargas **no tienen que estar junto al script**. Indica sus carpetas cuando el instalador las pida, separadas por `;`. Puede leer ZIP directamente y RAR/7z con el lector integrado de Windows. También acepta carpetas ya extraídas.

Puedes indicar directamente tu carpeta de Unverum, por ejemplo `C:\Mis mods\Unverum\Mods\Dragon Ball FighterZ`. El buscador entra en todas sus subcarpetas. Si hay dos ZIP del mismo personaje, identifica cada PAK por su nombre, el código de personaje que contiene y su SHA-256 completo. Si una copia coincide con la referencia, elige esa; no intenta adivinar cuál es más reciente por su nombre. Si hay varias versiones diferentes y ninguna coincide, omite ese personaje y muestra las rutas y hashes para que elijas una o descargues la referencia. Si solo existe una versión desconocida, puede usarla con un aviso: su compatibilidad no está comprobada. El PAK, `text.json` y `.sig` se toman de la misma carpeta interna del ZIP.

Antes de convertir, se comprueba que las librerías pueden abrir un PNG y comprimir una textura. El instalador guarda un registro `.log` junto a la carpeta de salida y muestra su ruta. Una importación aislada correcta no equivale a haber comprobado todo el montaje.

El instalador genera todo fuera del juego y comprueba los hashes. Después pregunta si quieres instalarlo: `S` copia el resultado con respaldo; Enter lo deja preparado. No modifica las descargas y no elimina mods ajenos. Cierra el juego antes de instalar y ábrelo después desde Inicio de Windows.

Los personajes incompletos se omiten con una explicación. Sin Werezaru, EX Goku conserva su aspecto normal. Si no hay ningún personaje completo, se detiene.

## Uso avanzado del script

Desde la carpeta raíz del paquete:

```powershell
.\runtime\python\python.exe -B .\tools\montar_extras.py --descargas "C:\Mis mods" "C:\Otro directorio" --juego "D:\Games\Dragon Ball FighterZ" --salida "C:\DBFZ-montaje-nuevo" --incluir-port
```

`--incluir-port` añade el sistema de espacios y UE4SS incluidos para partir de un juego sin este sistema instalado. Sin esa opción se generan solo los extras. La plantilla SIG se obtiene del propio paquete, no de una instalación anterior. `--instalar` copia además el resultado; sin él no se escribe en el juego.

La salida debe estar vacía y fuera del juego. `RED/` contiene lo instalable e `informe-montaje.json` los resultados. `reference-sha256.json` verifica los 18 PAK y dos configuraciones de extras; `technical-sha256.json` verifica los componentes incluidos del sistema de espacios. Las precargas parciales y los perfiles reducidos tienen un contenido distinto al perfil completo.

`requirements.txt` es una referencia para desarrolladores que quieran usar su propio Python. **No hace falta ejecutarlo para instalar el mod.** La referencia usa Python 3.12.14 y zlib 1.3.2, incluidos. Las licencias del runtime están en `../runtime/python/LICENSE.txt`, los directorios `.dist-info` de sus librerías y `../licenses/`.

## Opciones y modificación

- `--solo SBG,GRN`: genera esos personajes y un roster reducido. No elimina otros PAK que ya tengas instalados. Se genera el parche de precarga correspondiente aunque solo esté Sol o solo Granolah.
- `--sin-werezaru`: EX Goku mantiene su apariencia original. Cambia el resultado respecto al perfil completo.
- `ROSTER`: códigos, personaje base, fuente, nombres, referencias conservadas y conversiones auxiliares.
- `FUENTES` y `PROBADO`: nombres/rutas de origen y SHA-256 completo de cada versión comprobada. No cambies un hash solo para ocultar una discrepancia.
- `build_char.py --keep YGI --keep-refs`: conserva las referencias de YGI sin convertir AVP a YUG. Necesario para reproducir el Yugi instalado.
- Los 14 personajes se convierten igual: `build_char.py` pasa cada descarga a su propio código (por ejemplo, DIO de `CEN` a `DIO`, Gohan Bestia de `GHU` a `GHB`) sin tocar al personaje original.
- En la descarga de Raditz usada por esta receta no se encontraron retratos propios: `raditz_desde_juego()` usa los de Bardock del juego.
- Los iconos de los seis primeros extras conservan `ext/`; los siguientes tienen carpeta por código. Los recursos WRZ heredados se conservan para reproducir el PAK de referencia aunque no se añada WRZ al roster.
- `fix_preload_dependencies.py` corrige las dependencias de Sol y Granolah; `build_werezaru_exg.py` conserva los registros de movimientos y efectos de EX Goku.
- `build_texts.py` genera los textos de 13 idiomas desde el juego y los mods originales.

Para ampliar el sistema, consulta `../HOW-IT-WORKS.md`. No basta con añadir un nombre: se deben revisar referencias de assets, códigos, textos, iconos, roster y límites de la DLL. Las herramientas auxiliares históricas pueden ejecutar trabajo al importarse; utiliza `montar_extras.py` como entrada normal.

## Créditos y límites

El código propio conserva la licencia MIT indicada en `../LICENSE.txt`. El código se escribió con ayuda de IA (Claude y ChatGPT/Codex) bajo la dirección de MrPopulutus; el paquete no contiene arte, audio ni voces generados con IA. Las licencias y créditos de los mods fuente no cambian. No publiques los PAK resultantes de otros autores sin su autorización. Créditos y enlaces: `../CREDITOS.md`.

La comparación sin juego valida datos y reproducibilidad. No sustituye una prueba de cada movimiento, equipo y color.
