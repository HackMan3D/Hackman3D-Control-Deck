# HCD Pro — ESP32-S3 7-inch touch controller

HCD Pro v1.0 targets the Waveshare-compatible **ESP32-S3 7-inch capacitive
touch display** with an 800 × 480 RGB panel, 8 MB flash and 8 MB octal PSRAM.
The firmware profile uses the ST7262 display controller and GT911 touch
controller found on this board family.

## First installation

1. Connect the ESP32-S3 display to the computer with a data-capable USB cable.
2. Open **Firmware** in HackMan3D Control Deck 1.2.0 or newer.
3. Select **HCD Pro**, the ESP32-S3 USB port and the Wi-Fi network used by the
   computer.
4. Click **Install firmware**. The app writes the complete 8 MB image; Arduino
   IDE and a separate ESP flashing program are not required.
5. Leave the board connected while it restarts and receives the Wi-Fi settings.

If USB provisioning is interrupted, connect to the temporary Wi-Fi network
named `HCD-PRO-SETUP-xxxx`, open `http://192.168.4.1`, enter the local Wi-Fi
details and let the display restart.

## Normal operation

The display and computer must be on the same local network. The desktop app
broadcasts discovery packets on UDP port **42100**, then opens a TCP connection
to the deck on port **42101**. No manual IP address is required.

The screen has no additional physical buttons. It can display either 28
programmable touch keys with one vertical slider, or 24 programmable touch keys
with two vertical sliders. The sliders can control functions such as speaker
volume, microphone level or display brightness. Icons are synchronised from the
active desktop profile. A red indicator in the upper-right corner turns on only
while the desktop heartbeat is active. Touch events are ignored when the app is
not connected, matching the safety behaviour of the other HCD models.

The current local-network protocol is intended for a trusted home or workshop
network. Do not expose TCP port 42101 to the internet. Guest Wi-Fi isolation,
VPN rules or a firewall may prevent automatic discovery.

## Developer build

The firmware uses ESP32 Arduino core 3.3.10, ESP32_Display_Panel 1.0.4,
ESP32_IO_Expander 1.1.1, esp-lib-utils 0.2.3 and LVGL 9.5.0. Running
`software/build_firmware.sh` installs the pinned dependencies, builds all three
HCD targets and packages the merged HCD Pro image inside the desktop app.
