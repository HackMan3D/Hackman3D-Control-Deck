# HackMan3D Control Deck 1.5.4

This release unifies the Windows and macOS applications around the same USB
implementation for HCD-BASE, HCD Plus and HCD Pro.

## HCD Pro USB

- HCD Pro now uses USB for discovery, heartbeat, touch events, sliders, settings
  and icon synchronization.
- Wi-Fi discovery, provisioning, OTA updates and local-network permissions have
  been removed.
- Firmware 1.3.3 displays **Waiting for USB sync** at startup and a protected
  **Display update** screen while the active profile is transferred.
- The desktop app paces large icon transfers and retries the first icon to avoid
  an empty first key after synchronization.

## Windows

- Compatible Arduino ports explicitly assert DTR before probing.
- USB hot swapping works when Windows assigns the same COM number to another
  HCD model.
- The installer bundles AVRDUDE, ESP32 esptool and all three firmware images;
  Arduino IDE and Python are not required.
- The Waveshare `USB Single Serial` bridge is recognized for HCD Pro.

## macOS

- The Windows USB detection and hot-swap improvements are included in the shared
  app.
- HCD Pro no longer requests Local Network permission.
- The existing menu-bar background behavior and macOS actions are preserved.

## Validation

- 81 automated desktop tests pass.
- The macOS 1.5.4 application was built, signed locally, installed and launched.
- The Windows 1.5.4 installer was built successfully on GitHub's Windows runner.
