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
    cat <<'EOF'
ERROR: Python Tk support is missing.
Install it with your distribution package manager, for example:
  Debian/Ubuntu: sudo apt install python3-tk python3-venv
  Fedora:        sudo dnf install python3-tkinter
  Arch:          sudo pacman -S tk
EOF
    exit 1
fi

VENV_DIR=".venv-linux"
if [[ -d "$VENV_DIR" && ! -x "$VENV_DIR/bin/python" ]]; then
    rm -rf -- "$VENV_DIR"
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    echo "First launch: creating the Linux virtual environment..."
    "$PYTHON_CMD" -m venv "$VENV_DIR" || {
        echo "ERROR: Failed to create the virtual environment. Install your distribution's python3-venv package."
        exit 1
    }
fi

VENV_PYTHON="$PWD/$VENV_DIR/bin/python"
if ! "$VENV_PYTHON" -c 'import litemapy, nbtlib' >/dev/null 2>&1; then
    echo "Installing application dependencies..."
    "$VENV_PYTHON" -m pip install --upgrade pip
    "$VENV_PYTHON" -m pip install -r requirements.txt
fi

export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$VENV_PYTHON" -m schem_nbt_converter --gui
