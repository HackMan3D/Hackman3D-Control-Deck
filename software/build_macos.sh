#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR"
export PIP_CACHE_DIR="$SCRIPT_DIR/.pip-cache"
export PYINSTALLER_CONFIG_DIR="$SCRIPT_DIR/.pyinstaller-cache"

if [[ -n "${HCD_PYTHON:-}" ]]; then
  PYTHON_COMMAND="$HCD_PYTHON"
else
  PYTHON_COMMAND=""
  for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && \
       "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
      PYTHON_COMMAND="$candidate"
      break
    fi
  done
fi

if [[ -z "$PYTHON_COMMAND" ]]; then
  echo "Python 3.11 or newer is required." >&2
  exit 1
fi

if [[ ! -d .venv-macos ]]; then
  "$PYTHON_COMMAND" -m venv .venv-macos
fi

source .venv-macos/bin/activate
if [[ "${HCD_OFFLINE:-0}" != "1" ]]; then
  python -m pip install --upgrade pip
  python -m pip install -e ".[dev]"
fi

python scripts/build_app_icon.py
python -m PyInstaller --noconfirm --clean "HackMan3D Control Deck.spec"

APP_PATH="$SCRIPT_DIR/dist/HackMan3D Control Deck.app"
CLEAN_DIR=$(mktemp -d "$SCRIPT_DIR/dist/.hcd-app-clean.XXXXXX")
ditto --noextattr --noqtn "$APP_PATH" "$CLEAN_DIR/HackMan3D Control Deck.app"
rm -rf "$APP_PATH"
mv "$CLEAN_DIR/HackMan3D Control Deck.app" "$APP_PATH"
rmdir "$CLEAN_DIR"
xattr -cr "$APP_PATH" 2>/dev/null || true
if ! codesign --force --deep --sign - "$APP_PATH"; then
  echo "Warning: macOS restored Finder metadata in dist; the DMG builder will clean and sign its staged copy." >&2
fi

echo "Build complete: dist/HackMan3D Control Deck.app"
