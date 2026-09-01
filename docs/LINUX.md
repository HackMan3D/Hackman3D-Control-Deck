# Linux application

HackMan3D Control Deck supports x86_64 and ARM64 Linux desktops through two
packages for each architecture.

## Choose the correct architecture

Open a terminal and run `uname -m`:

- `x86_64` means that the filename must contain **x86_64**;
- `aarch64` or `arm64` means that the filename must contain **aarch64**.

Ubuntu virtual machines running on an Apple Silicon Mac normally use the
**aarch64** package. Ubuntu's App Center may silently refuse an x86_64 package
on such a VM.

## Easy installation

### Ubuntu, Debian and Linux Mint

Download the `.deb` matching the computer from the latest GitHub release,
double-click it and choose **Install**. The application then appears in the
desktop application menu.

It can also be installed from a terminal:

```bash
sudo apt install ./HackMan3D-Control-Deck-Linux-ARCHITECTURE-1.5.5.deb
```

### Other Linux distributions

Download the `.AppImage`, make it executable and launch it:

```bash
chmod +x HackMan3D-Control-Deck-Linux-ARCHITECTURE-1.5.5.AppImage
./HackMan3D-Control-Deck-Linux-ARCHITECTURE-1.5.5.AppImage
```

The AppImage is portable and can be moved anywhere. AppImageLauncher can add it
to the application menu automatically, but is not required.

## USB access

The `.deb` installer adds a limited USB-access rule for the Arduino, SparkFun,
Espressif and WCH serial devices used by HCD models. After installing or
updating the package, unplug and reconnect the Control Deck once.

AppImage users may still need membership of the `dialout` group. If the deck is
listed as `ttyACM0` or `ttyUSB0` but is not detected, run the command below,
then sign out and sign back in:

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
