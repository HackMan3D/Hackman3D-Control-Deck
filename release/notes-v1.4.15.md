# HackMan3D Control Deck 1.4.15

- Test release for Windows. Please report any remaining freeze or firmware
  installation problem before this version is marked stable.
- Prevents background device discovery from reopening the COM port while the
  integrated firmware installer is flashing HCD-BASE or HCD Plus.
- An automatic BASE retry now restarts the Caterina bootloader and redetects
  its live COM port instead of reusing a stale Windows port name.
- Windows volume, brightness and microphone polling now runs outside the user
  interface thread, and Start Menu icons are loaded only when selected.
- Fixes an HCD Pro that could remain on `DISPLAY UPDATE` if a Windows network
  synchronization was interrupted before its final command.
- The desktop app now clears any unfinished display-update overlay immediately
  after reconnecting, including on HCD Pro firmware 1.2.44.
- Bundled HCD Pro firmware 1.2.45 automatically restores the normal interface
  if the app disconnects during synchronization.
- Firmware 1.2.45 also includes a 60-second safety timeout so an incomplete
  transfer can never leave the overlay visible permanently.
