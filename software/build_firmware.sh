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

build_pro_firmware() {
  local sketch_name="HackMan3DControlDeckPro"
  local model="HCD-PRO"
  local version="1.2.45"
  local firmware_dir="$PROJECT_DIR/firmware/$sketch_name"
  local build_dir="$BUILD_ROOT/$model"
  local output_dir="$OUTPUT_ROOT/$model"
  local packaged_bin="$PACKAGE_DIR/HackMan3DControlDeck-$model-$version.bin"
  local packaged_ota_bin="$PACKAGE_DIR/HackMan3DControlDeck-$model-$version-ota.bin"

  "$ARDUINO_CLI" core install esp32:esp32@3.3.10
  "$ARDUINO_CLI" lib install \
    "ESP32_Display_Panel@1.0.4" \
    "ESP32_IO_Expander@1.1.1" \
    "esp-lib-utils@0.2.3" \
    "lvgl@9.5.0"

  mkdir -p "$build_dir" "$output_dir" "$PACKAGE_DIR"
  "$ARDUINO_CLI" compile \
    --fqbn 'esp32:esp32:esp32s3:CDCOnBoot=cdc,FlashSize=8M,PartitionScheme=default_8MB,PSRAM=opi,FlashMode=qio,USBMode=hwcdc' \
    --build-property "tools.gen_esp32part.cmd=ruby $SCRIPT_DIR/scripts/generate_esp32_partitions.rb" \
    --build-path "$build_dir" \
    --output-dir "$output_dir" \
    "$firmware_dir"
  cp "$output_dir/$sketch_name.ino.merged.bin" "$packaged_bin"
  cp "$output_dir/$sketch_name.ino.bin" "$packaged_ota_bin"
  local esptool_source="$HOME/Library/Arduino15/packages/esp32/tools/esptool_py/5.3.0/esptool"
  local esptool_target="$SCRIPT_DIR/src/hackman_control_deck/assets/tools/macos/esptool"
  if [[ -x "$esptool_source" ]]; then
    cp "$esptool_source" "$esptool_target"
    chmod +x "$esptool_target"
  fi
  echo "Firmware ready: $packaged_bin"
  echo "OTA firmware ready: $packaged_ota_bin"
}

build_firmware "HackMan3DControlDeck" "HCD-BASE" "1.7.0" "HackMan3D Control Deck"
build_firmware "HackMan3DControlDeckPlus" "HCD-PLUS" "1.1.1" "HackMan3D Control Deck Plus"
build_pro_firmware
