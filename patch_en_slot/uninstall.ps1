#Requires -Version 5.1
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    # Si se omite, el script pregunta la ruta de la carpeta del juego.
    [string]$GamePath = "",
    # Omite la confirmacion final.
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

if (Get-Process -Name "Dusk City" -ErrorAction SilentlyContinue) {
    throw "El juego esta abierto. Cierralo e intentalo de nuevo."
}

$BackupRoot = Join-Path $GamePath "_backup_es_patch"

if (-not (Test-Path -LiteralPath $BackupRoot)) {
    Write-Warning "No hay carpeta de respaldo en $BackupRoot - nada que restaurar."
    exit 0
}

$backups = Get-ChildItem -LiteralPath $BackupRoot -Recurse -File
if ($backups.Count -eq 0) {
    Write-Warning "La carpeta de respaldo esta vacia."
    exit 0
}

Write-Host ""
Write-Host "Carpeta del juego : $GamePath"
Write-Host "Se restauraran    : $($backups.Count) archivos desde $BackupRoot"
if (-not $Force -and -not $WhatIfPreference) {
    $ok = Read-Host "Continuar? (S/N)"
    if ($ok -notmatch '^(s|si|y|yes)$') {
        Write-Host "Cancelado. No se modifico nada."
        exit 0
    }
}

foreach ($file in $backups) {
    $rel = $file.FullName.Substring($BackupRoot.Length).TrimStart('\', '/')
    $dest = Join-Path $GamePath $rel
    $destDir = Split-Path -Parent $dest
    if ($PSCmdlet.ShouldProcess($dest, "Restore from $($file.FullName)")) {
        if (-not $WhatIfPreference) {
            if (-not (Test-Path -LiteralPath $destDir)) {
                New-Item -ItemType Directory -Force -Path $destDir | Out-Null
            }
            Copy-Item -LiteralPath $file.FullName -Destination $dest -Force
        }
    }
}

Write-Host "Restaurados $($backups.Count) archivo(s) desde $BackupRoot"
