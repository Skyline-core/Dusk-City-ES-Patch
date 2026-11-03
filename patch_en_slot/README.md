# Parche de espanol (sustituye el ingles)

No se agrega ningun idioma nuevo: el contenido en espanol **reemplaza** al ingles (mismos nombres de
archivo, codigo `en`, nombres de assets `*_EN`). En el menu la entrada del ingles se muestra como
"Espanol".

## Archivos que modifica

Todos los bundles generados viven bajo `patch_en_slot\files\` con la **misma ruta relativa** que en
`Dusk City_Data\StreamingAssets\aa\` (por ejemplo `StandaloneWindows64\…`, `DLC1\StandaloneWindows64\…`).

Como minimo incluye estos cuatro de localizacion (interfaz y menu):

- `StandaloneWindows64\localization-string-tables-english(en)_assets_all.bundle`
- `StandaloneWindows64\localization-asset-tables-english(en)_assets_all.bundle`
- `StandaloneWindows64\localization-assets-english(en)_assets_all_2226d8d2…bundle`
- `StandaloneWindows64\localization-locales_assets_all.bundle`

Si existe `translation\es_source_scripts.json`, el build tambien parchea bundles de escenas/CG/DLC
con textos de dialogo (`GameScript` / `m_commandDatas`).

El `catalog.json` y el `.hash` **no se tocan**.

## Por que no hace falta tocar el catalogo

Unity valida cada bundle contra el CRC32 de sus datos descomprimidos que figura en el catalogo.
`bundle_builder/crc_forge.py` anade al final de cada bundle editado un bloque de 4 bytes calculado
para que su CRC32 sea exactamente el original. Asi el catalogo original (y cualquier copia en cache
del juego) acepta los archivos.

## Uso

1. `..\build_all.ps1` (pregunta la ruta del juego; lee los originales, no los modifica).
2. `install.bat` / `install.ps1` (pregunta la ruta del juego, copia de seguridad en `_backup_es_patch\`).
3. `uninstall.bat` / `uninstall.ps1` restaura solo los archivos que existen en la copia de seguridad.

Cada vez que cambies traducciones (`es_source.json` o `es_source_scripts.json`), repite 1 y 2.

## Instalacion

- Comprueba que el juego no este en ejecucion.
- Comprueba que **cada** archivo del parche ya exista en tu instalacion (version incompatible si falta alguno).
- Muestra el tamano total aproximado del parche antes de confirmar.
- La primera instalacion guarda el original en `<juego>\_backup_es_patch\` (misma ruta relativa); una segunda instalacion **no** sobrescribe esa copia.
