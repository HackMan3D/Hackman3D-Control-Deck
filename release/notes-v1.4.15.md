# HackMan3D Control Deck 1.4.15

- Fixes an HCD Pro that could remain on `DISPLAY UPDATE` if a Windows network
  synchronization was interrupted before its final command.
- The desktop app now clears any unfinished display-update overlay immediately
  after reconnecting, including on HCD Pro firmware 1.2.44.
- Bundled HCD Pro firmware 1.2.45 automatically restores the normal interface
  if the app disconnects during synchronization.
- Firmware 1.2.45 also includes a 60-second safety timeout so an incomplete
  transfer can never leave the overlay visible permanently.
