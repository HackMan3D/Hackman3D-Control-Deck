# HackMan3D Control Deck 1.4.17

## Hardware routing

- HCD Base and HCD Plus are Arduino/ATmega32U4 controllers and are now always
  probed over USB before any network discovery begins.
- HCD Pro is an ESP32-S3 controller. Wi-Fi discovery is used only when no
  compatible USB Base or Plus is present; USB remains available for initial Pro
  provisioning and recovery flashing.

## Windows fixes

- Replaces the unreliable Qt-only 1200-baud reset with the native pySerial
  sequence used by Arduino tooling. On the validated HCD Base, Windows moves
  from `Arduino Leonardo (COM9)` to `Arduino Micro bootloader (COM3)`, then
  returns to `COM9` after a verified flash.
- Keeps requesting device identity after USB reconnection until the Base replies
  with `HCD-BASE`, firmware `1.7.0` and its 9-control layout.
- Immediately returns to detection when a Deck is unplugged, clears the central
  Deck image while no controller is identified, and accepts a different Base or
  Plus connected without restarting the application.
- Ignores delayed HCD Pro Wi-Fi discovery replies while a Base or Plus USB port
  is being probed.
- Bundles AVRDUDE for Base/Plus and a standalone esptool 4.12.0 executable for
  HCD Pro, so Windows flashing does not require Arduino IDE or Python.

## macOS build handoff

The repository is already versioned for macOS 1.4.17. From an updated checkout
on the Mac, run:

```bash
git pull --ff-only origin main
cd software
./build_macos.sh
./build_dmg.sh
```

The expected artifact is:

```text
software/dist/HackMan3D-Control-Deck-macOS-1.4.17.dmg
```

Upload that DMG to the existing GitHub release `v1.4.17`; do not create a
second release or change the tag.
