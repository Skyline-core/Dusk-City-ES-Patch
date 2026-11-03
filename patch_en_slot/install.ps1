#Requires -Version 5.1
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    # Si se omite, el script pregunta la ruta de la carpeta del juego.
    [string]$GamePath = "",
    # Omite la confirmacion final (util para automatizar).
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Test-GameFolder {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath (Join-Path $Path "Dusk City.exe"))) {
        throw "No es una instalacion de Dusk City (falta Dusk City.exe): $Path"
    }
}

function Read-GamePath {
    $suggest = ""
    try {
        $cand = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
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
}

Test-GameFolder -Path $GamePath

$PatchRoot = $PSScriptRoot
$PatchFiles = Join-Path $PatchRoot "files"
$AaRoot = Join-Path $GamePath "Dusk City_Data\StreamingAssets\aa"
$BackupRoot = Join-Path $GamePath "_backup_es_patch"

if (-not (Test-Path -LiteralPath $PatchFiles)) {
    throw "Missing patch staging folder: $PatchFiles (run build_all.ps1 first)"
}

$sources = Get-ChildItem -LiteralPath $PatchFiles -Recurse -File
if ($sources.Count -eq 0) {
    throw "No patch files under $PatchFiles"
}

$totalBytes = ($sources | Measure-Object -Property Length -Sum).Sum
$totalMb = [math]::Round($totalBytes / 1MB, 2)

if (Get-Process -Name "Dusk City" -ErrorAction SilentlyContinue) {
    throw "El juego esta abierto. Cierralo e intentalo de nuevo."
}

# Cada archivo del parche debe existir ya en el juego (misma version)
$missingTargets = @()
foreach ($src in $sources) {
    $rel = $src.FullName.Substring($PatchFiles.Length).TrimStart('\', '/')
    $dest = Join-Path $AaRoot $rel
    if (-not (Test-Path -LiteralPath $dest)) {
        $missingTargets += $rel
    }
}
if ($missingTargets.Count -gt 0) {
    Write-Host "Esta instalacion no coincide con la version del juego. Faltan en el juego (primeros 20):" -ForegroundColor Red
    $missingTargets | Select-Object -First 20 | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    if ($missingTargets.Count -gt 20) {
        Write-Host "  ... y $($missingTargets.Count - 20) mas" -ForegroundColor Red
    }
    throw "Version del juego incompatible."
}

Write-Host ""
Write-Host "Carpeta del juego : $GamePath"
Write-Host "Se modificaran    : $($sources.Count) archivos (~$totalMb MB) en StreamingAssets\aa"
Write-Host "Copia de seguridad: $BackupRoot"
if (-not $Force -and -not $WhatIfPreference) {
    $ok = Read-Host "Continuar? (S/N)"
    if ($ok -notmatch '^(s|si|y|yes)$') {
        Write-Host "Cancelado. No se modifico nada."
        exit 0
    }
}

if (-not $WhatIfPreference) {
    New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
}

$n = 0
foreach ($src in $sources) {
    $n++
    $rel = $src.FullName.Substring($PatchFiles.Length).TrimStart('\', '/')
    $dest = Join-Path $AaRoot $rel
    $destDir = Split-Path -Parent $dest
    if (-not $WhatIfPreference -and -not (Test-Path -LiteralPath $destDir)) {
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
    }

    $relFromGame = $dest.Substring($GamePath.Length).TrimStart('\', '/')
    $backupPath = Join-Path $BackupRoot $relFromGame
    if (-not (Test-Path -LiteralPath $backupPath)) {
        if ($PSCmdlet.ShouldProcess($dest, "Back up to $backupPath")) {
            if (-not $WhatIfPreference) {
                $backupDir = Split-Path -Parent $backupPath
                New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
                Copy-Item -LiteralPath $dest -Destination $backupPath
            }
        }
    }

    if ($PSCmdlet.ShouldProcess($dest, "Install from $($src.FullName)")) {
        if (-not $WhatIfPreference) {
            Copy-Item -LiteralPath $src.FullName -Destination $dest -Force
        }
    }

    if ($n % 50 -eq 0) {
        Write-Host "  ... $n / $($sources.Count)"
    }
}

Write-Host "Spanish (en-slot) patch installed to: $GamePath"
Write-Host "Backups (first install only): $BackupRoot"
