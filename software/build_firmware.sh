#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PROJECT_DIR="${SCRIPT_DIR:h}"
CLI_DEFAULT="/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/arduino-cli"
ARDUINO_CLI="${HCD_ARDUINO_CLI:-$CLI_DEFAULT}"
BUILD_ROOT="$PROJECT_DIR/work/arduino-build-branded"
OUTPUT_ROOT="$PROJECT_DIR/work/firmware-build-branded"
PACKAGE_DIR="$SCRIPT_DIR/src/hackman_control_deck/assets/firmware"

if [[ ! -x "$ARDUINO_CLI" ]]; then
  echo "Arduino CLI was not found. Set HCD_ARDUINO_CLI to its path." >&2
  exit 1
fi

build_firmware() {
  local sketch_name="$1"
  local model="$2"
  local version="$3"
  local product="$4"
  local firmware_dir="$PROJECT_DIR/firmware/$sketch_name"
  local build_dir="$BUILD_ROOT/$model"
  local output_dir="$OUTPUT_ROOT/$model"
  local packaged_hex="$PACKAGE_DIR/HackMan3DControlDeck-$model-$version.hex"

  mkdir -p "$build_dir" "$output_dir" "$PACKAGE_DIR"
  "$ARDUINO_CLI" compile \
    --fqbn arduino:avr:leonardo \
    --build-property "build.usb_product=\"$product\"" \
    --build-property 'build.usb_manufacturer="HackMan3D"' \
    --build-path "$build_dir" \
    --output-dir "$output_dir" \
    "$firmware_dir"
  cp "$output_dir/$sketch_name.ino.hex" "$packaged_hex"
  echo "Firmware ready: $packaged_hex"
}

build_firmware "HackMan3DControlDeck" "HCD-BASE" "1.7.0" "HackMan3D Control Deck"
build_firmware "HackMan3DControlDeckPlus" "HCD-PLUS" "1.0.0" "HackMan3D Control Deck Plus"
