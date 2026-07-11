#!/usr/bin/env bash
set -Eeuo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

find_python() {
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1; then
            printf '%s' "$candidate"
            return 0
        fi
    done
    return 1
}

PYTHON_CMD="$(find_python || true)"
if [[ -z "$PYTHON_CMD" ]]; then
    echo "ERROR: Python 3.10 or newer was not found."
    exit 1
fi

if ! "$PYTHON_CMD" -c 'import tkinter' >/dev/null 2>&1; then
    echo "ERROR: Python Tk support is missing. Install python3-tk or the equivalent package."
    exit 1
fi

VENV_DIR=".venv-linux-build"
if [[ -d "$VENV_DIR" && ! -x "$VENV_DIR/bin/python" ]]; then
    rm -rf -- "$VENV_DIR"
fi
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    "$PYTHON_CMD" -m venv "$VENV_DIR"
fi

VENV_PYTHON="$PWD/$VENV_DIR/bin/python"
"$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel
"$VENV_PYTHON" -m pip install -r requirements-dev.txt
"$VENV_PYTHON" -m pytest -q
"$VENV_PYTHON" -m PyInstaller --noconfirm --clean --onefile --windowed \
    --name SchemNBTConverter \
    --collect-all litemapy \
    --collect-all nbtlib \
    --collect-all tkinterdnd2 \
    --paths src \
    launcher.py

echo "SUCCESS: dist/SchemNBTConverter was created."
