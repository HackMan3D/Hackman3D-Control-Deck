# Brand assets

`hcd_logo_original.png` is the original HackMan3D Control Deck artwork.
`hcd_logo.png` is the optimized header version loaded by the desktop app. Both
files are packaged into Windows and macOS builds automatically.

`hcd_app_icon.icns` is the macOS application icon used by the packaging script.
It is derived from the supplied HackMan3D Control Deck artwork with a transparent
macOS-style rounded mask. `hcd_app_icon_rounded.png` is its full-size preview.
Run `scripts/build_app_icon.py` after changing the source logo.

`hcd_tray.svg` is the compact HCD monogram used in the Windows notification
area and the macOS menu bar.

`firmware/` contains the branded HCD-BASE and HCD Plus Intel HEX images bundled
with the desktop application. `tools/macos/` and `tools/windows/` contain the
official Arduino AVRDUDE 8.0 binaries, configuration and licence used by the
firmware manager.
