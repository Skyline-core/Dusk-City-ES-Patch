# Dusk City - Parche de traduccion al espanol (LATAM)

Parche **no oficial** para *Dusk City* (Unity 2022.3 / IL2CPP / Addressables). El espanol **reemplaza** al
ingles (codigo `en`, mismos nombres `*_EN`); en el menu de idioma la entrada del ingles aparece como "Espanol".
No se modifica `catalog.json` ni el `.hash`: cada bundle parchado conserva su CRC original.

> Este repositorio **no contiene el juego**. Hace falta tu propia copia legitima.

**Version actual: 0.1b (beta).**

## Instalar (solo jugar)

1. Descarga `Dusk_City_ES_patch_v0.1b.zip` desde *Releases* y descomprimelo.
2. Cierra el juego y ejecuta `install.bat`. Te pide la ruta de la carpeta del juego (la que contiene `Dusk City.exe`).
3. Se hace una copia de seguridad de los archivos originales en `<juego>\_backup_es_patch\`.
4. Abre el juego. Para volver al original: `uninstall.bat`.

Requisitos: Windows con PowerShell 5.1+ (viene con Windows 10/11) y la **misma version del juego** con la que se compilo
el parche (Unity 2022.3.62f2, catalogo `2026.06.x`). No hace falta Python.

## Que esta traducido

- Interfaz y menus (771 textos), lineas de voz de escenas H (2385).
- Dialogos e historia (3818 textos de `GameScript`), nombres de personajes, opciones y objetos.
- Menus de interaccion (grafos de dialogo, 365 textos); las opciones largas se parten en dos lineas.
- Menu de idioma ("Espanol").

Pendiente: 88 imagenes con texto en ingles (tips, creditos, botones...). Ver `images/README.md`.

## Estructura

| Carpeta / archivo | Funcion |
|---|---|
| `es_source.json` | Interfaz + lineas H (en/ja/es) |
| `es_source_scripts.json` | Dialogos de los guiones |
| `es_source_dialogues.json` | Opciones de menus de interaccion |
| `es_source_misc.json` | Textos menores |
| `build_all.ps1` | Compila todo el parche (lee el juego, no lo modifica) |
| `patch_en_slot/` | Instalador (`install.bat`, `uninstall.bat`); `files/` se genera al compilar |
| `bundle_builder/`, `catalog_tool/` | Clonado de bundles y herramientas de catalogo + `crc_forge.py` |
| `script_texts/`, `script_injector/` | Extraccion e inyeccion de textos de guiones |
| `dialogue_graphs/`, `misc_texts/`, `ui_label/`, `ui_layout/` | Grafos de dialogo, textos menores, etiqueta de idioma, ajuste de lineas |
| `images/` | Exportar / inyectar imagenes traducidas |
| `research/` | Notas e informes tecnicos |

## Compilar desde cero

Requisitos: Python 3.12 y `pip install UnityPy lz4 pillow`.
**Usa una copia limpia (sin parche) del juego**, porque los inyectores buscan el texto original.

```powershell
.\build_all.ps1 -GamePath "C:\ruta\a\la\copia\limpia\Dusk City"
```

Genera `patch_en_slot\files\`. Luego `patch_en_slot\install.bat`.

Flujo de traduccion: rellenar el campo `es` de los `es_source_*.json` (conservando etiquetas `<...>`, `{...}`, `\n`, `\u3000`),
validar con `validate_translation.py` / `validate_scripts_translation.py`, compilar e instalar.

## Aviso

Proyecto de aficionados, sin relacion con los creadores del juego. Los bundles del parche contienen datos del juego
modificados; usalos solo con una copia que poseas.
