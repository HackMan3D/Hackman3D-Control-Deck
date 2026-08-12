#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="${0:A:h}"
APP_PATH="$SCRIPT_DIR/dist/HackMan3D Control Deck.app"
OUTPUT_PATH="$SCRIPT_DIR/dist/HackMan3D-Control-Deck-macOS-1.5.4.dmg"
VOLUME_NAME="HackMan3D Control Deck 1.5.4"

if [[ ! -d "$APP_PATH" ]]; then
  "$SCRIPT_DIR/build_macos.sh"
fi

WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/hcd-dmg.XXXXXX")
STAGE_DIR="$WORK_DIR/stage"

cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

mkdir -p "$STAGE_DIR"
ditto --noextattr --noqtn "$APP_PATH" "$STAGE_DIR/HackMan3D Control Deck.app"
xattr -cr "$STAGE_DIR/HackMan3D Control Deck.app" 2>/dev/null || true
find "$STAGE_DIR/HackMan3D Control Deck.app" \
  -exec xattr -d com.apple.FinderInfo {} \; 2>/dev/null || true
find "$STAGE_DIR/HackMan3D Control Deck.app" \
  -exec xattr -d com.apple.ResourceFork {} \; 2>/dev/null || true
codesign --force --deep --sign - "$STAGE_DIR/HackMan3D Control Deck.app"
codesign --verify --deep --strict "$STAGE_DIR/HackMan3D Control Deck.app"
ln -s /Applications "$STAGE_DIR/Applications"
cp "$SCRIPT_DIR/dmg-arrow.png" "$STAGE_DIR/→.png"
if command -v SetFile >/dev/null 2>&1; then
  SetFile -a E "$STAGE_DIR/→.png"
fi
"$SCRIPT_DIR/.venv-macos/bin/python" \
  "$SCRIPT_DIR/scripts/create_dmg_layout.py" "$STAGE_DIR" "$VOLUME_NAME"

hdiutil create \
  -volname "$VOLUME_NAME" \
  -srcfolder "$STAGE_DIR" \
  -fs APFS \
  -format UDZO \
  -imagekey zlib-level=9 \
  -ov \
  "$OUTPUT_PATH" >/dev/null

echo "Installer complete: $OUTPUT_PATH"
