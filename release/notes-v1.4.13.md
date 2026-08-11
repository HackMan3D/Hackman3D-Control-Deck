# HackMan3D Control Deck 1.4.13

This maintenance release corrects the bundled HCD Plus input mapping so it
matches the validated physical build.

- HCD Plus keys 1–8 now use MCP23017 PB0–PB7.
- HCD Plus keys 9–12 now use MCP23017 PA0–PA3.
- Encoder clicks remain fully supported on PA4 and PA5, even when they
  are not physically connected yet.
- The HCD Plus wiring diagram and documentation now show this exact mapping.
- HCD Plus firmware is updated to version 1.0.2 and remains flashable directly
  from the desktop application.
- The firmware now detects module addresses 0x20–0x27, retries a module that
  was not ready during startup, enables all PB0–PB7 pull-ups and uses a more
  reliable 100 kHz I²C clock.
