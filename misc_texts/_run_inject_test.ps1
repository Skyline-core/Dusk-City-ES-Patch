$env:DUSK_GAME_PATH = "G:\SteamLibrary\steamapps\common\Dusk City"
$py = "C:\Users\ah_3m\AppData\Local\Programs\Python\Python312\python.exe"
$root = Split-Path $PSScriptRoot -Parent
$out = Join-Path $PSScriptRoot "_test_out"
$out2 = Join-Path $PSScriptRoot "_test_out_chain"
if (Test-Path $out) { Remove-Item -Recurse -Force $out }
if (Test-Path $out2) { Remove-Item -Recurse -Force $out2 }

& $py "$PSScriptRoot\inject_misc_texts.py" --use-test-source --limit 5 --self-test --out $out
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Chain: second pass reads patched bundles from same --out (idempotent re-apply)
& $py "$PSScriptRoot\inject_misc_texts.py" --use-test-source --limit 5 --self-test --out $out
exit $LASTEXITCODE
