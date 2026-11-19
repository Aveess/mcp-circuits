#!/usr/bin/env bash
# Deja el monorepo listo: venv, dependencias del puente, cerebro editable y
# Chromium. No toca tu cuenta de Tinkercad: eso es `src.cli.login_cli`.
#
#   ./setup.sh                 # todo
#   SKIP_BROWSER=1 ./setup.sh  # sin bajar Chromium (ya lo tienes)
set -euo pipefail

cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "No encuentro '$PYTHON'. Instala Python 3.11+ o pasa PYTHON=/ruta/python3." >&2
    exit 1
fi

"$PYTHON" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit(
        f"Python 3.11+ hace falta (tienes {sys.version.split()[0]})."
    )
PY

echo "==> venv en .venv"
[ -d .venv ] || "$PYTHON" -m venv .venv

PY_BIN=".venv/bin/python"
[ -x "$PY_BIN" ] || PY_BIN=".venv/Scripts/python.exe"

echo "==> pip"
"$PY_BIN" -m pip install --upgrade pip

echo "==> dependencias del puente"
"$PY_BIN" -m pip install -r packages/bridge/requirements.txt

# Los dos en editable: el puente deja `src` importable (de ahi sale
# `python -m src.main`) y el cerebro queda como libreria.
echo "==> puente y cerebro (editables)"
"$PY_BIN" -m pip install -e packages/bridge -e packages/brain

if [ "${SKIP_BROWSER:-0}" != "1" ]; then
    echo "==> Chromium de Playwright (~150 MB la primera vez)"
    "$PY_BIN" -m playwright install chromium
fi

cat <<'FIN'

Listo. Falta entrar a tu cuenta una sola vez:

    .venv/bin/python -m src.cli.login_cli

Eso abre Chrome en Tinkercad y guarda la sesión en
packages/bridge/.tinkercad_profile/ (esa carpeta es tu contraseña).

Comprueba que el servidor arranca:

    .venv/bin/python packages/bridge/examples/check_mcp_stdio.py
FIN
