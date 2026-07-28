#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="${0:A:h}"
APP_PATH="$SCRIPT_DIR/dist/HackMan3D Control Deck.app"
OUTPUT_PATH="$SCRIPT_DIR/dist/HackMan3D-Control-Deck-macOS-1.1.0.dmg"
VOLUME_NAME="HackMan3D Control Deck 1.1.0"

if [[ ! -d "$APP_PATH" ]]; then
  "$SCRIPT_DIR/build_macos.sh"
fi

WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/hcd-dmg.XXXXXX")
STAGE_DIR="$WORK_DIR/stage"
HYBRID_DMG="$WORK_DIR/HackMan3D-Control-Deck-hybrid.dmg"

cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

mkdir -p "$STAGE_DIR"
ditto --noextattr --noqtn "$APP_PATH" "$STAGE_DIR/HackMan3D Control Deck.app"
xattr -cr "$STAGE_DIR/HackMan3D Control Deck.app" 2>/dev/null || true
codesign --force --deep --sign - "$STAGE_DIR/HackMan3D Control Deck.app"
ln -s /Applications "$STAGE_DIR/Applications"
cp "$SCRIPT_DIR/dmg-arrow.png" "$STAGE_DIR/→.png"
if command -v SetFile >/dev/null 2>&1; then
  SetFile -a E "$STAGE_DIR/→.png"
fi
"$SCRIPT_DIR/.venv-macos/bin/python" \
  "$SCRIPT_DIR/scripts/create_dmg_layout.py" "$STAGE_DIR" "$VOLUME_NAME"

hdiutil makehybrid \
  -hfs \
  -hfs-volume-name "$VOLUME_NAME" \
  -hfs-openfolder "$STAGE_DIR" \
  -o "$HYBRID_DMG" \
  "$STAGE_DIR" >/dev/null
hdiutil convert \
  "$HYBRID_DMG" \
  -format UDZO \
  -imagekey zlib-level=9 \
  -o "$OUTPUT_PATH" \
  -ov >/dev/null

echo "Installer complete: $OUTPUT_PATH"
