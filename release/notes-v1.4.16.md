# HackMan3D Control Deck 1.4.16

- Fixes HCD-BASE recognition on Windows when the connection heartbeat works
  but the first device-information response is lost during USB enumeration.
- The application now requests the controller identity again until the model,
  firmware version and control count are received.
- The firmware manager updates live when a connected BASE is identified; it no
  longer needs to be closed and reopened.
- AVR flashing now rejects a normal application COM port until the real
  Caterina bootloader has appeared.
- The flash status displays the exact bootloader port selected for upload,
  making hardware and driver problems easier to diagnose.
- Includes HCD-BASE firmware 1.7.0, HCD Plus firmware 1.1.1 and HCD Pro
  firmware 1.2.45 directly in both desktop applications.
