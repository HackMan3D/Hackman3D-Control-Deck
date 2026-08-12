# HCD Pro — ESP32-S3 7-inch touch controller

HCD Pro targets the Waveshare-compatible **ESP32-S3 7-inch capacitive touch
display** with an 800 × 480 RGB panel, 8 MB flash and 8 MB octal PSRAM. The
firmware profile uses the ST7262 display controller and GT911 touch controller.

## USB connection

HCD Pro version 1.3.3 and later is USB-only. One data-capable USB-C cable carries:

- application discovery and the `HCD_PING` / `HCD_PONG` heartbeat;
- touch-key and slider events;
- profiles, colors, settings and icon synchronization;
- complete firmware installation and recovery.

Wi-Fi credentials, local-network permission, UDP discovery and OTA updates are
not required.

## First installation

1. Connect the ESP32-S3 display to the computer with a data-capable USB cable.
2. Open **Firmware** in HackMan3D Control Deck 1.5.4 or newer.
3. Select **HCD Pro** and the ESP32-S3 USB port.
4. Click **Install firmware**. The app writes the complete 8 MB image; Arduino
   IDE and a separate ESP flashing program are not required.
5. Leave the board connected while it restarts and the app synchronizes the
   active profile.

The display first shows **Waiting for USB sync**, then **Display update** while
the profile is transferred. The normal key grid is revealed only after the
atomic synchronization has finished.

## Normal operation

The screen has no additional physical buttons. It can display either 28
programmable touch keys with one vertical slider, or 24 programmable touch keys
with two vertical sliders. The sliders can control speaker volume, microphone
level or display brightness. Icons are synchronized from the active
model-specific desktop profile.

A red indicator in the upper-right corner turns on only while the desktop
heartbeat is active. Touch events are ignored when the app is not connected,
matching the safety behavior of the other HCD models.

## Display synchronization

The desktop app sends a protected snapshot over USB. Transfers are paced to
avoid starving the RGB display task, the first icon is retried automatically,
and the firmware keeps the update overlay visible for up to three minutes if a
large profile is being transferred. Disconnecting USB safely cancels an active
update.

## Developer build

The firmware uses ESP32 Arduino core 3.3.10, ESP32_Display_Panel 1.0.4,
ESP32_IO_Expander 1.1.1, esp-lib-utils 0.2.3 and LVGL 9.5.0. Running
`software/build_firmware.sh` installs the pinned dependencies, builds all three
HCD targets and packages the merged HCD Pro image inside both desktop apps.
