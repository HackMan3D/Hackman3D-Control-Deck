#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"
VERSION=$(python3 -c 'import pathlib,re; text=pathlib.Path("src/hackman_control_deck/constants.py").read_text(); print(re.search(r"APP_VERSION = \"([^\"]+)", text).group(1))')
PYTHON_COMMAND=${HCD_PYTHON:-python3}
APP_NAME="HackMan3D Control Deck"
case "$(uname -m)" in
  x86_64|amd64)
    LINUX_ARCH="x86_64"
    DEB_ARCH="amd64"
    ;;
  aarch64|arm64)
    LINUX_ARCH="aarch64"
    DEB_ARCH="arm64"
    ;;
  *)
    echo "Unsupported Linux architecture: $(uname -m)" >&2
    exit 1
    ;;
esac
APP_SLUG="HackMan3D-Control-Deck-Linux-$LINUX_ARCH-$VERSION"
TOOLS_DIR="src/hackman_control_deck/assets/tools/linux"

if [[ ! -d .venv-linux ]]; then
  "$PYTHON_COMMAND" -m venv .venv-linux
fi
source .venv-linux/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]" esptool

rm -rf "$TOOLS_DIR" build/linux-tools dist/linux AppDir package/linux
mkdir -p "$TOOLS_DIR/lib" build/linux-tools dist/linux package/linux

AVRDUDE=$(command -v avrdude)
cp -L "$AVRDUDE" "$TOOLS_DIR/avrdude"
AVRDUDE_CONF=""
for candidate in /etc/avrdude.conf /etc/avrdude/avrdude.conf; do
  if [[ -f "$candidate" ]]; then AVRDUDE_CONF="$candidate"; break; fi
done
if [[ -z "$AVRDUDE_CONF" ]]; then
  echo "avrdude.conf was not found" >&2
  exit 1
fi
cp "$AVRDUDE_CONF" "$TOOLS_DIR/avrdude.conf"

while read -r library; do
  [[ -f "$library" ]] && cp -Ln "$library" "$TOOLS_DIR/lib/" || true
done < <(ldd "$AVRDUDE" | awk '/=> \// {print $3} /^\// {print $1}')

python -m PyInstaller \
  --noconfirm --clean --onefile --console \
  --name esptool \
  --distpath build/linux-tools/dist \
  --workpath build/linux-tools/work \
  --specpath build/linux-tools \
  scripts/esptool_entry.py
cp build/linux-tools/dist/esptool "$TOOLS_DIR/esptool"

python -m PyInstaller \
  --noconfirm --clean --windowed \
  --name "$APP_NAME" \
  --paths src \
  --add-data "src/hackman_control_deck/assets:hackman_control_deck/assets" \
  --collect-submodules pynput \
  --distpath dist/linux \
  --workpath build/linux-main \
  run.py

PACKAGED_TOOLS="dist/linux/$APP_NAME/_internal/hackman_control_deck/assets/tools/linux"
for required in avrdude avrdude.conf esptool; do
  if [[ ! -f "$PACKAGED_TOOLS/$required" ]]; then
    echo "Missing packaged Linux firmware tool: $required" >&2
    exit 1
  fi
done

mkdir -p "AppDir/usr/lib/hackman3d-control-deck" "AppDir/usr/bin"
cp -a "dist/linux/$APP_NAME/." "AppDir/usr/lib/hackman3d-control-deck/"
cp linux/AppRun AppDir/AppRun
chmod +x AppDir/AppRun
cat > AppDir/usr/bin/hackman3d-control-deck <<'EOF'
#!/bin/sh
APP_LIB="$(dirname "$0")/../lib/hackman3d-control-deck"
TOOL_ROOT="$APP_LIB/_internal/hackman_control_deck/assets/tools/linux"
export LD_LIBRARY_PATH="$TOOL_ROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export HCD_AVRDUDE="$TOOL_ROOT/avrdude"
export HCD_AVRDUDE_CONF="$TOOL_ROOT/avrdude.conf"
export HCD_ESPTOOL="$TOOL_ROOT/esptool"
exec "$APP_LIB/HackMan3D Control Deck" "$@"
EOF
chmod +x AppDir/usr/bin/hackman3d-control-deck
cp linux/hackman3d-control-deck.desktop AppDir/hackman3d-control-deck.desktop
cp src/hackman_control_deck/assets/hcd_app_icon_rounded.png AppDir/hackman3d-control-deck.png
ln -s hackman3d-control-deck.png AppDir/.DirIcon

APPIMAGETOOL=${APPIMAGETOOL:-appimagetool}
ARCH="$LINUX_ARCH" "$APPIMAGETOOL" AppDir "dist/$APP_SLUG.AppImage"

DEB_ROOT="package/linux/hackman3d-control-deck"
mkdir -p "$DEB_ROOT/DEBIAN" "$DEB_ROOT/usr/lib/hackman3d-control-deck" \
  "$DEB_ROOT/usr/bin" "$DEB_ROOT/usr/share/applications" \
  "$DEB_ROOT/usr/share/icons/hicolor/512x512/apps" \
  "$DEB_ROOT/usr/lib/udev/rules.d"
cp -a "dist/linux/$APP_NAME/." "$DEB_ROOT/usr/lib/hackman3d-control-deck/"
cp AppDir/usr/bin/hackman3d-control-deck "$DEB_ROOT/usr/bin/"
cp linux/hackman3d-control-deck.desktop "$DEB_ROOT/usr/share/applications/"
cp src/hackman_control_deck/assets/hcd_app_icon_rounded.png \
  "$DEB_ROOT/usr/share/icons/hicolor/512x512/apps/hackman3d-control-deck.png"
cat > "$DEB_ROOT/usr/lib/udev/rules.d/60-hackman3d-control-deck.rules" <<'EOF'
# Arduino, SparkFun, Espressif and WCH USB serial devices used by HCD models.
SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", TAG+="uaccess", GROUP="dialout", MODE="0660"
SUBSYSTEM=="tty", ATTRS{idVendor}=="2a03", TAG+="uaccess", GROUP="dialout", MODE="0660"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1b4f", TAG+="uaccess", GROUP="dialout", MODE="0660"
SUBSYSTEM=="tty", ATTRS{idVendor}=="303a", TAG+="uaccess", GROUP="dialout", MODE="0660"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", TAG+="uaccess", GROUP="dialout", MODE="0660"
EOF
cat > "$DEB_ROOT/DEBIAN/control" <<EOF
Package: hackman3d-control-deck
Version: $VERSION-2
Section: utils
Priority: optional
Architecture: $DEB_ARCH
Maintainer: HackMan3D <hackman3d.pro@gmail.com>
Depends: libegl1, libxcb-cursor0, libxkbcommon-x11-0
Description: HackMan3D Control Deck desktop application
 Configure profiles, actions, diagnostics and integrated firmware updates.
EOF
cat > "$DEB_ROOT/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
udevadm control --reload-rules 2>/dev/null || true
udevadm trigger --subsystem-match=tty 2>/dev/null || true
exit 0
EOF
chmod 755 "$DEB_ROOT/DEBIAN/postinst"
dpkg-deb --build --root-owner-group "$DEB_ROOT" "dist/$APP_SLUG.deb"

echo "Linux packages created:"
echo "  dist/$APP_SLUG.AppImage"
echo "  dist/$APP_SLUG.deb"
