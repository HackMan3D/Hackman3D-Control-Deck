#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PROJECT_DIR="${SCRIPT_DIR:h}"
CLI_DEFAULT="/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/arduino-cli"
ARDUINO_CLI="${HCD_ARDUINO_CLI:-$CLI_DEFAULT}"
BUILD_DIR="$PROJECT_DIR/work/arduino-build-branded"
OUTPUT_DIR="$PROJECT_DIR/work/firmware-build-branded"
FIRMWARE_DIR="$PROJECT_DIR/firmware/HackMan3DControlDeck"
PACKAGED_HEX="$SCRIPT_DIR/src/hackman_control_deck/assets/firmware/HackMan3DControlDeck-HCD-BASE-1.7.0.hex"

if [[ ! -x "$ARDUINO_CLI" ]]; then
  echo "Arduino CLI was not found. Set HCD_ARDUINO_CLI to its path." >&2
  exit 1
fi

mkdir -p "$BUILD_DIR" "$OUTPUT_DIR" "${PACKAGED_HEX:h}"
"$ARDUINO_CLI" compile \
  --fqbn arduino:avr:leonardo \
  --build-property 'build.usb_product="HackMan3D Control Deck"' \
  --build-property 'build.usb_manufacturer="HackMan3D"' \
  --build-path "$BUILD_DIR" \
  --output-dir "$OUTPUT_DIR" \
  "$FIRMWARE_DIR"
cp "$OUTPUT_DIR/HackMan3DControlDeck.ino.hex" "$PACKAGED_HEX"

echo "Firmware ready: $PACKAGED_HEX"
