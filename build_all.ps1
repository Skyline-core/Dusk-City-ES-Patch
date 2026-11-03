# Compila el parche de la fase 1 (espanol en la ranura del ingles).
# Solo LEE el juego (originales); escribe en translation\patch_en_slot\files\.
# Uso:
#   .\build_all.ps1                         # pregunta la ruta del juego
#   .\build_all.ps1 -GamePath "D:\Juegos\Dusk City"
[CmdletBinding()]
param(
    [string]$GamePath = "",
    [string]$PythonPath = "",
    [switch]$Extract
)

$ErrorActionPreference = "Stop"
$TranslationRoot = $PSScriptRoot

# ---------- Ruta del juego ----------
function Read-GamePath {
    $suggest = ""
    try {
        $cand = (Resolve-Path (Join-Path $TranslationRoot "..")).Path
        if (Test-Path -LiteralPath (Join-Path $cand "Dusk City.exe")) { $suggest = $cand }
    } catch {}
    while ($true) {
        if ($suggest) {
            $in = Read-Host "Ruta de la carpeta del juego (donde esta 'Dusk City.exe') [Enter = $suggest]"
        } else {
            $in = Read-Host "Ruta de la carpeta del juego (donde esta 'Dusk City.exe')"
        }
        $in = $in.Trim().Trim('"').Trim("'")
        if (-not $in -and $suggest) { $in = $suggest }
        if (-not $in) { Write-Host "Escribe una ruta." -ForegroundColor Yellow; continue }
        if (-not (Test-Path -LiteralPath (Join-Path $in "Dusk City.exe"))) {
            Write-Host "No se encontro 'Dusk City.exe' en: $in" -ForegroundColor Yellow
            continue
        }
        return (Resolve-Path -LiteralPath $in).Path
    }
}

if ([string]::IsNullOrWhiteSpace($GamePath)) {
    $GamePath = Read-GamePath
} else {
    $GamePath = $GamePath.Trim().Trim('"')
    if (-not (Test-Path -LiteralPath (Join-Path $GamePath "Dusk City.exe"))) {
        throw "No se encontro 'Dusk City.exe' en: $GamePath"
    }
    $GamePath = (Resolve-Path -LiteralPath $GamePath).Path
}
$env:DUSK_GAME_PATH = $GamePath   # lo leen los scripts de Python
Write-Host "Juego: $GamePath"

# ---------- Verificar que es la misma version del juego ----------
$aa = Join-Path $GamePath "Dusk City_Data\StreamingAssets\aa"
$expected = @(
    "catalog.json",
    "StandaloneWindows64\catalog_2026.06.23.02.23.07.hash",
    "StandaloneWindows64\localization-locales_assets_all.bundle",
    "StandaloneWindows64\localization-string-tables-english(en)_assets_all.bundle",
    "StandaloneWindows64\localization-asset-tables-english(en)_assets_all.bundle",
    "StandaloneWindows64\localization-assets-english(en)_assets_all_2226d8d2b0d3da2279c40b114f5b8f8c.bundle"
)
$missing = $expected | Where-Object { -not (Test-Path -LiteralPath (Join-Path $aa $_)) }
if ($missing) {
    Write-Host "Esta instalacion no coincide con la version para la que se hizo el parche (build 2026.06.23). Faltan:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    throw "Version del juego incompatible."
}

# ---------- Python ----------
function Find-Python {
    if ($PythonPath -and (Test-Path -LiteralPath $PythonPath)) { return $PythonPath }
    $default = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
    if (Test-Path -LiteralPath $default) { return $default }
    foreach ($name in "python", "python3") {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        # Ignorar el alias falso de la Microsoft Store
        if ($cmd -and $cmd.Source -notmatch "WindowsApps") { return $cmd.Source }
    }
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        $exe = & $py.Source -3 -c "import sys;print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $exe) { return $exe.Trim() }
    }
    return $null
}
$Python = Find-Python
if (-not $Python) {
    throw "No se encontro Python 3. Instalalo y ejecuta 'pip install UnityPy', o usa -PythonPath 'C:\ruta\python.exe'."
}
& $Python -c "import UnityPy" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Falta UnityPy. Ejecuta: `"$Python`" -m pip install UnityPy"
}
Write-Host "Python: $Python"

$BundleBuilder = Join-Path $TranslationRoot "bundle_builder\build_es_bundles.py"
$CatalogTool = Join-Path $TranslationRoot "catalog_tool\catalog_tool.py"
$PatchRoot = Join-Path $TranslationRoot "patch_en_slot"
$PatchFiles = Join-Path $PatchRoot "files"
$HijackOut = Join-Path $PatchFiles "StandaloneWindows64"
$TestOut = Join-Path $PatchRoot "_test_hijack_out"

# Limpiar salidas anteriores (solo dentro de files\)
if (Test-Path -LiteralPath $PatchFiles) {
    Write-Host "=== limpiar staging anterior (patch_en_slot\files) ==="
    Remove-Item -LiteralPath $PatchFiles -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $HijackOut | Out-Null

if ($Extract) {
    Write-Host "=== extraer textos (regenera es_source.json: SE PERDERAN tus traducciones) ==="
    $ans = Read-Host "Esto sobreescribe translation\es_source.json. Continuar? (S/N)"
    if ($ans -match '^(s|si|y|yes)$') {
        & $Python (Join-Path $TranslationRoot "extract_source.py")
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

Write-Host "=== catalog_tool roundtrip ==="
& $Python $CatalogTool roundtrip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== hijack-en self-test (test strings) ==="
if (Test-Path -LiteralPath $TestOut) {
    Remove-Item -LiteralPath $TestOut -Recurse -Force
}
& $Python $BundleBuilder --hijack-en --out $TestOut --use-test-source --self-test
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Remove-Item -LiteralPath $TestOut -Recurse -Force

Write-Host "=== hijack-en production build ==="
& $Python $BundleBuilder --hijack-en --out $HijackOut --self-test
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== language menu label (English -> Espanol) ==="
$LabelScript = Join-Path $TranslationRoot "ui_label\patch_language_label.py"
& $Python $LabelScript
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Copy-Item -LiteralPath (Join-Path $TranslationRoot "ui_label\out\localization-locales_assets_all.bundle") -Destination $HijackOut -Force

$ScriptSource = Join-Path $TranslationRoot "es_source_scripts.json"
$ScriptRefs = Join-Path $TranslationRoot "research\script_refs.json"
if (Test-Path -LiteralPath $ScriptSource) {
    Write-Host "=== GameScript injection (es_source_scripts.json) ==="
    if (-not (Test-Path -LiteralPath $ScriptRefs)) {
        Write-Host "AVISO: falta $ScriptRefs — omitiendo inject_scripts" -ForegroundColor Yellow
    } else {
        $InjectScript = Join-Path $TranslationRoot "script_injector\inject_scripts.py"
        & $Python $InjectScript --self-test
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
} else {
    Write-Host "=== GameScript injection: omitido (no hay es_source_scripts.json) ==="
}

$DlgSource = Join-Path $TranslationRoot "es_source_dialogues.json"
$DlgRefs = Join-Path $TranslationRoot "research\dialogue_refs.json"
if ((Test-Path -LiteralPath $DlgSource) -and (Test-Path -LiteralPath $DlgRefs)) {
    Write-Host "=== Dialogue graphs / menus de interaccion (es_source_dialogues.json) ==="
    # Debe ir DESPUES de inject_scripts: continua sobre los bundles ya parchados (encadenado).
    & $Python (Join-Path $TranslationRoot "dialogue_graphs\inject_dialogues.py") --self-test
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "=== Dialogue graphs: omitido (no hay es_source_dialogues.json) ==="
}

$MiscSource = Join-Path $TranslationRoot "es_source_misc.json"
$MiscRefs = Join-Path $TranslationRoot "research\misc_refs.json"
if ((Test-Path -LiteralPath $MiscSource) -and (Test-Path -LiteralPath $MiscRefs)) {
    Write-Host "=== Textos menores (es_source_misc.json) ==="
    # Tambien encadenado: debe ir despues de scripts y dialogos.
    & $Python (Join-Path $TranslationRoot "misc_texts\inject_misc_texts.py") --self-test
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$ImgTranslated = Join-Path $TranslationRoot "images\translated"
if ((Test-Path -LiteralPath $ImgTranslated) -and (Get-ChildItem -LiteralPath $ImgTranslated -Filter *.png -ErrorAction SilentlyContinue)) {
    Write-Host "=== Imagenes traducidas (images\translated\*.png) ==="
    & $Python (Join-Path $TranslationRoot "images\inject_images.py") --game $GamePath --self-test
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "=== Imagenes: omitido (no hay PNG en images\translated) ==="
}

Write-Host "=== ajustar CRC de los bundles al original (el catalogo NO se modifica) ==="
& $Python (Join-Path $TranslationRoot "bundle_builder\forge_patch_crcs.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "=== Resumen ==="
Write-Host "Parche en: $PatchFiles"
$all = Get-ChildItem -LiteralPath $PatchFiles -Recurse -File -Filter "*.bundle"
$totalBytes = ($all | Measure-Object -Property Length -Sum).Sum
Write-Host "Bundles: $($all.Count) ($totalBytes bytes total)"
$all | ForEach-Object {
    $rel = $_.FullName.Substring($PatchFiles.Length).TrimStart('\', '/')
    Write-Host "  $rel ($($_.Length) bytes)"
}
Write-Host ""
Write-Host "Siguiente paso: patch_en_slot\install.ps1 (te pedira la ruta del juego)."
Write-Host "El juego NO fue modificado por este script."
