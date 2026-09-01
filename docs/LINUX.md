# Linux application

HackMan3D Control Deck supports 64-bit Linux desktops through two packages.

## Easy installation

### Ubuntu, Debian and Linux Mint

Download `HackMan3D-Control-Deck-Linux-x86_64-1.5.5.deb` from the latest GitHub
release, double-click it and choose **Install**. The application then appears in
the desktop application menu.

It can also be installed from a terminal:

```bash
sudo apt install ./HackMan3D-Control-Deck-Linux-x86_64-1.5.5.deb
```

### Other Linux distributions

Download the `.AppImage`, make it executable and launch it:

```bash
chmod +x HackMan3D-Control-Deck-Linux-x86_64-1.5.5.AppImage
./HackMan3D-Control-Deck-Linux-x86_64-1.5.5.AppImage
```

The AppImage is portable and can be moved anywhere. AppImageLauncher can add it
to the application menu automatically, but is not required.

## USB access

Most distributions grant serial-device access to members of `dialout`. If the
deck is visible but cannot be opened, add the current user to this group, sign
out and sign back in:

```bash
sudo usermod -aG dialout "$USER"
```

The HCD application contains the official firmware, AVRDUDE and esptool. Arduino
IDE is not required. Open **Firmware** in the application to install or update a
compatible controller.

## Desktop integration

The Linux build supports:

- HCD-BASE, HCD Plus and HCD Pro over USB;
- profiles, short/long actions and automatic icon synchronization;
- installed applications from standard `.desktop` launchers;
- system audio through PipeWire (`wpctl`) or PulseAudio (`pactl`);
- media controls through `playerctl`;
- display brightness through `brightnessctl`;
- background operation from a compatible notification area.

Audio controls work on most current desktops without extra setup. Media and
brightness actions require the corresponding `playerctl` and `brightnessctl`
packages when they are not already provided by the distribution.

## Build from source

The release package is built on Ubuntu 22.04 using GitHub Actions. For a local
build, install Python 3.11 or newer, `avrdude`, `dpkg-deb` and AppImageKit's
`appimagetool`, then run:

```bash
cd software
APPIMAGETOOL=/path/to/appimagetool ./build_linux.sh
```

The resulting AppImage and Debian package are written to `software/dist`.
