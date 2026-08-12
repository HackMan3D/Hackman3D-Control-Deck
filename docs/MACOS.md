# macOS application

## Requirements

- macOS 12 Monterey or newer
- Python 3.11 or newer for building
- A data-capable USB connection for every HCD model

## Build the `.app`

Open Terminal in the project, then run:

```bash
cd software
chmod +x build_macos.sh
./build_macos.sh
```

The script creates an isolated Python environment, installs the declared
dependencies, packages the application and applies an ad-hoc signature. The
result is:

```text
software/dist/HackMan3D Control Deck.app
```

Move the application to `/Applications` if desired.

## Build the drag-to-Applications installer

After building the application, run:

```bash
./build_dmg.sh
```

This creates a branded `.dmg` containing HackMan3D Control Deck and an
Applications shortcut.

If several Python versions are installed, the script automatically prefers
3.13, 3.12 or 3.11. A specific interpreter can also be selected with:

```bash
HCD_PYTHON=/path/to/python3.12 ./build_macos.sh
```

After one successful build, the existing environment can be reused without a
network connection:

```bash
HCD_OFFLINE=1 ./build_macos.sh
```

Profiles normally live under the user's `Library/Application Support` folder.
For a portable or managed installation, `HCD_PROFILE_DIR` can point to another
writable profile folder before launching the application.

## Menu bar and login

Minimizing the window sends HackMan3D Control Deck to the macOS menu bar while
the Arduino heartbeat and assigned actions continue running. Click the native
menu-bar icon once to reopen the window. The Dock icon disappears automatically
in background mode and returns with the window. The macOS options control login
launch and minimized startup independently.

The **Start with Mac** option creates the per-user file
`~/Library/LaunchAgents/com.hackman3d.control-deck.plist`. Turning the option off
removes that file.

Move the application to `/Applications` before enabling **Start with Mac**, so
the saved login path continues to point to the final application location.

## First launch

The app needs macOS Accessibility permission to send configured shortcuts and
text to other applications:

1. Open **System Settings → Privacy & Security → Accessibility**.
2. Enable **HackMan3D Control Deck**.
3. Quit and reopen the app after changing the permission.

Serial device discovery does not normally require a separate permission. If
macOS blocks the first launch because the app is locally built, Control-click
the app, choose **Open**, then confirm once.

HCD Pro communicates entirely over USB. It does not request macOS Local Network
permission and does not require Wi-Fi credentials.

Building the application requires the Apple command-line tools license to be
accepted once. If `lipo` or `install_name_tool` reports a license error, run
`sudo xcodebuild -license accept` in Terminal before rebuilding.

## Distribution

The included build is ad-hoc signed for local use. Public distribution outside
the Mac that built it requires an Apple Developer ID signature and Apple
notarization.

## Completing a cross-platform release created on Windows

When the Windows installer has already created the release tag, first update
the local checkout and confirm that `APP_VERSION`, `pyproject.toml`, the
PyInstaller bundle metadata and `build_dmg.sh` all show the same version.

For version 1.5.4:

```bash
git switch main
git pull --ff-only origin main
cd software
./build_macos.sh
./build_dmg.sh
gh release upload v1.5.4 \
  "dist/HackMan3D-Control-Deck-macOS-1.5.4.dmg" \
  --repo HackMan3D/Hackman3D-Control-Deck --clobber
```

This adds or replaces only the macOS asset in the existing cross-platform
release. It preserves the Windows installer and keeps both downloads under the
same version number.
