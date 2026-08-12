# Windows release build

HackMan3D Control Deck supports 64-bit Windows 10 and Windows 11.

## Local build

1. Install Python 3.11 or newer from python.org.
2. Install Inno Setup 6.
3. Open PowerShell in the project folder.
4. Run `software\build_windows.ps1`.

The finished installer is written to
`software\dist\HackMan3D-Control-Deck-Windows-1.5.4-Setup.exe`.

## Device detection

Detection is USB-only for HCD Base, HCD Plus and HCD Pro. The Pro is detected
through its ESP32-S3 USB serial bridge and no firewall permission is required.

On Windows, the app explicitly asserts DTR after opening an Arduino serial
port. The Base and Plus firmware requires DTR before it transmits `HCD_PONG`,
`HCD_INFO`, or control events, while QSerialPort does not always assert it by
default on Windows.

The app requests identity periodically and ignores identical replies. Windows
can therefore reuse the same COM number when swapping a Base and a Plus without
requiring an application restart. On disconnect, the central preview is cleared
until the newly connected model has identified itself.

## Firmware flashing

- Base and Plus use bundled AVRDUDE and a pySerial 1200-baud reset to enter the
  Caterina bootloader.
- Pro uses the bundled standalone esptool for installation and recovery over
  USB. The same USB cable then carries heartbeat, touch events, settings and
  icon synchronization during normal operation.

The packaged application does not require Arduino IDE or a separate Python
installation.

## Troubleshooting USB detection

In Device Manager, a Base or Plus should appear as an Arduino/Leonardo serial
device with a COM number. Close any other software that may own this COM port,
then reconnect the cable. The app probes compatible ports automatically and
accepts them only after receiving a valid `HCD-*` identity.

## GitHub build

The `Build Windows application` workflow can be launched manually from the
Actions page. It builds on a real Windows runner and publishes the installer as
a downloadable workflow artifact. It bundles the AVR and Espressif flashing
tools.

The generated installer contains the current Base, Plus and Pro firmware. It
does not need Arduino IDE, Python, Wi-Fi provisioning or a separate flashing
utility on the user's computer.
