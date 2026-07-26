# Windows release build

HackMan3D Control Deck supports 64-bit Windows 10 and Windows 11.

## Local build

1. Install Python 3.11 or newer from python.org.
2. Install Inno Setup 6.
3. Open PowerShell in the project folder.
4. Run `software\build_windows.ps1`.

The finished installer is written to
`software\dist\HackMan3D-Control-Deck-Windows-0.17.0-Setup.exe`.

## GitHub build

The `Build Windows application` workflow can be launched manually from the
Actions page. It builds on a real Windows runner and publishes the installer as
a downloadable workflow artifact.
