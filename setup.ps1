# Deja el monorepo listo en Windows: venv, dependencias del puente, cerebro
# editable y Chromium. No toca tu cuenta de Tinkercad: eso es el login.
#
#   .\setup.ps1
#   $env:SKIP_BROWSER="1"; .\setup.ps1   # sin bajar Chromium
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "==> venv en .venv"
if (-not (Test-Path ".venv")) { python -m venv .venv }

$py = ".\.venv\Scripts\python.exe"
& $py -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) { throw "Python 3.11+ hace falta." }

Write-Host "==> pip"
& $py -m pip install --upgrade pip

Write-Host "==> dependencias del puente"
& $py -m pip install -r packages\bridge\requirements.txt

Write-Host "==> puente y cerebro (editables)"
& $py -m pip install -e packages\bridge -e packages\brain

if ($env:SKIP_BROWSER -ne "1") {
    Write-Host "==> Chromium de Playwright (~150 MB la primera vez)"
    & $py -m playwright install chromium
}

Write-Host @"

Listo. Falta entrar a tu cuenta una sola vez:

    .\.venv\Scripts\python.exe -m src.cli.login_cli

Eso abre Chrome en Tinkercad y guarda la sesión en
packages\bridge\.tinkercad_profile\ (esa carpeta es tu contraseña).

Comprueba que el servidor arranca:

    .\.venv\Scripts\python.exe packages\bridge\examples\check_mcp_stdio.py
"@
