# HackMan3D Control Deck

![Version](https://img.shields.io/badge/Version-1.5.5-0A84FF?style=flat-square)
![Platforms](https://img.shields.io/badge/Platforms-macOS%20%7C%20Windows-0A84FF?style=flat-square)
![Hardware](https://img.shields.io/badge/Hardware-ATmega32U4%20%7C%20ESP32--S3-00979D?style=flat-square&logo=arduino&logoColor=white)
![Firmware](https://img.shields.io/badge/Firmware-Integrated%20Flashing-39A845?style=flat-square)
![Controls](https://img.shields.io/badge/Controls-9%20MX%20Keys-7B61FF?style=flat-square)
![Status](https://img.shields.io/badge/Status-Private%20Preview-555555?style=flat-square)
[![Support](https://img.shields.io/badge/Support-HackMan3D-EA6D2F?style=flat-square&logo=paypal&logoColor=white)](https://paypal.me/Hackman3D)

HackMan3D Control Deck (HCD) is a family of programmable desktop controllers.
HCD-BASE and HCD Plus use an Arduino Pro Micro; HCD Pro uses an ESP32-S3
touchscreen. This repository contains the shared Windows/macOS configuration
app, the branded interface and the firmware for all three models.

## Download the app — version 1.5.5

The project is currently private. These downloads are available only to people
who have access to this repository.

- [Download for macOS (.dmg)](https://github.com/HackMan3D/Hackman3D-Control-Deck/releases/download/v1.5.5/HackMan3D-Control-Deck-macOS-1.5.5.dmg)
- [Download for Windows (.exe)](https://github.com/HackMan3D/Hackman3D-Control-Deck/releases/download/v1.5.5/HackMan3D-Control-Deck-Windows-1.5.5-Setup.exe)

## Quick start — recommended

You do not need Python, Arduino IDE or a manual AVRDUDE installation to build a
working HackMan3D Control Deck.

1. Assemble the controller using the
   [wiring diagram](docs/images/HCD_Wiring_Diagram_V1.svg) and
   [wiring notes](docs/WIRING.md).
2. Download and install the HCD application for
   [macOS](https://github.com/HackMan3D/Hackman3D-Control-Deck/releases/download/v1.5.5/HackMan3D-Control-Deck-macOS-1.5.5.dmg)
   or
   [Windows](https://github.com/HackMan3D/Hackman3D-Control-Deck/releases/download/v1.5.5/HackMan3D-Control-Deck-Windows-1.5.5-Setup.exe).
3. Connect the compatible Arduino Pro Micro to the computer by USB.
4. Open **Firmware** in the application, select **HCD-BASE** and click
   **Install firmware**.
5. Wait for the upload and automatic reconnection, then assign actions to the
   keys from the 3D editor.

The application contains the official HCD firmware and flashing tools. Once the
installation is complete, keep the app running in the background so it can
maintain the heartbeat and execute the configured actions.

> **For developers:** compiling the desktop app or firmware from source is
> optional. The build instructions later in this README are only needed to
> modify or contribute to the project.

## HCD-BASE gallery

The screenshots below show the **HCD-BASE only**: nine physical MX keys in a
3 × 3 layout, the connection indicator and the white key-feedback bar. HCD Plus
and HCD Pro are not shown because their hardware guides are still in
development.

### HCD-BASE desktop application

![HCD-BASE main application interface](docs/screenshots/main-window.jpg)

The central preview reproduces the nine controls of the BASE model. Profiles
are managed on the left and the selected key is configured on the right.

### HCD-BASE key editor

![HCD-BASE key editor with the first MX key selected](docs/screenshots/key-editor.jpg)

Select any key on the 3D preview to configure its short-press and long-press
actions, test the command and save it to the current HCD-BASE profile.

### HCD-BASE hardware preview

![HCD-BASE hardware with nine MX keys](software/src/hackman_control_deck/assets/hcd_device_render_off.png)

## How it works

1. Connect the HCD to the computer and keep the desktop application running.
2. Install or update the integrated HCD firmware directly from the application's
   **Firmware** manager. Arduino IDE is not required.
3. The application detects the controller and maintains the connection LED
   through the `HCD_PING` / `HCD_PONG` heartbeat.
4. Create or select a profile, then click one of the nine keys in the 3D
   preview.
5. Assign a shortcut, system command, text, website or application to the short
   press and, optionally, a different action to the long press.
6. Minimize the application to the macOS menu bar or Windows notification area;
   profiles and actions continue to work in the background.

## HCD-BASE hardware

- 9 MX switches in a 3 × 3 layout
- 1 red PC-connection LED
- 1 white key-feedback LED
- Arduino Pro Micro (ATmega32U4, 5 V / 16 MHz)

The connection LED is controlled by the app heartbeat. It turns off about three
seconds after the app stops responding. The feedback LED remains on while one or
more of the nine MX keys is held, but only while the desktop app is connected.

The V1 deliberately has no rotary encoders. Pins D14 through D20 remain free for
a possible V2.

## Wiring

![HackMan3D Control Deck V1 wiring diagram](docs/images/HCD_Wiring_Diagram_V1.svg)

The nine switches use the Pro Micro's internal pull-ups and share a common
ground. The connection LED and key-feedback light are switched by separate
IRLB8721 MOSFETs. See the [complete wiring notes](docs/WIRING.md) before
powering the controller.

## Future hardware previews

The firmware manager shows **HCD Plus (in development)** and
**HCD Pro (in development)** so the planned product family is visible. These
entries are development previews. Their firmware remains selectable for
HackMan3D prototype testing, but the hardware and assembly guides are not ready
for users. Regular users should build and flash only **HCD-BASE**.

## Support matters

HackMan3D Control Deck is designed, developed and shared free of charge.
Donations help fund prototypes, electronics, printing tests and the time needed
to improve the firmware and the macOS/Windows applications. Feedback and social
media follows are also important: they help validate ideas and make the project
visible.

- [Support development with PayPal](https://paypal.me/Hackman3D)
- [Send feedback by email](mailto:hackman3d.pro@gmail.com?subject=HackMan3D%20Control%20Deck%20feedback)
- [Creality Cloud](https://www.crealitycloud.com/user/5221417142)
- [MakerWorld](https://makerworld.com/fr/@HackMan3D)
- [TikTok](https://www.tiktok.com/@hackman3d)
- [Instagram](https://www.instagram.com/hackman_3dprint/)
- [YouTube](https://www.youtube.com/@hackman3D)

## HCD roadmap

HackMan3D Control Deck is developed and shared free of charge. Community
support helps fund the prototypes, components and development time needed for
the next editions.

The application displays one community progress bar from 0 to 100%:

- **HCD Plus** is the milestone shown at 50%;
- **HCD Pro** is the final milestone shown at 100%;
- the bar is updated through the HackMan3D release feed as support is received;
- only the resulting percentage is public. Donation totals and financial
  targets are never included in the application, its public feed or the source
  repository.

The application does not collect payments. The support button only opens the
external HackMan3D PayPal page. The exact feature set will continue to evolve
after prototype testing and community feedback.

### HCD Plus

The Plus edition expands the physical controls while keeping the same software
and the same two status lights:

- 12 physical buttons;
- separate short-press and long-press assignments, providing up to 24 functions;
- 2 clickable rotary encoders, independently configurable for output volume,
  microphone volume, brightness or other actions;
- the same connection LED and action-feedback LED as HCD-BASE;
- configuration and integrated firmware installation from the HCD application.

### HCD Pro

The Pro edition focuses on direct visual identification and a more compact,
interactive surface:

- no additional physical buttons;
- 28 programmable touch buttons with one vertical slider; or
- 24 programmable touch buttons with two vertical sliders;
- labels synchronised automatically from the active desktop profile;
- a direct USB connection for discovery, heartbeat, actions and icon transfer;
- configurable sliders for functions such as speaker volume, microphone level
  or display brightness;
- the same connection LED and action-feedback LED as HCD-BASE and HCD Plus;
- configuration and integrated firmware installation from the HCD application.

Support for the current HCD directly contributes to the research and prototypes
needed to explore these Plus and Pro editions.

## Repository layout

```text
firmware/HackMan3DControlDeck/       HCD-BASE firmware
firmware/HackMan3DControlDeckPlus/   HCD Plus firmware
firmware/HackMan3DControlDeckPro/    HCD Pro ESP32-S3 USB firmware
software/                            shared PySide6 desktop app
docs/                                protocol and wiring notes
```

## Desktop app

The same PySide6 application runs on Windows and macOS. It detects the connected
Control Deck, keeps its heartbeat active and provides one place to manage
profiles, actions, diagnostics and firmware.

### Run from source

Python 3.11 or newer is recommended.

**Windows**

```powershell
cd software
py -m venv .venv
.venv\Scripts\activate
python -m pip install -e .
hackman3d-control-deck
```

**macOS**

```bash
cd software
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
hackman3d-control-deck
```

### Profiles and actions

- Create, rename, duplicate and delete profiles.
- Import or export a portable `.hcdprofile`, or create a complete
  `.hcdbackup` archive.
- Configure separate **Short press** and **Long press** actions for every key.
- Assign keyboard shortcuts, text, websites, applications and system commands
  such as volume, media playback and screen brightness.
- Actions are saved automatically as they are selected or edited.
- Test an action directly in the editor and detect conflicting assignments.
- Drag an application from Finder or Explorer directly onto a key. Its name and
  native icon are added automatically.
- Reset all key assignments in the current profile with one confirmation.

The shortcut catalogue adapts to Windows or macOS and shows the purpose of each
combination. Custom key combinations remain available when a preset is not
listed.

### Device, firmware and diagnostics

- Automatic serial discovery prioritises compatible Arduino and USB devices.
- The app displays the model reported by the firmware, such as `HCD-BASE`,
  instead of a system port name such as `cu.usbmodem101`.
- The integrated firmware manager installs HCD-BASE without Arduino IDE.
  HCD Plus and HCD Pro remain visible as clearly marked development previews.
  Their firmware can be selected for prototype testing, but their public
  assembly guides are not available yet.
- Compatible firmware updates are detected automatically and offered through a
  pop-up.
- The diagnostics page displays the model, firmware version, serial port,
  heartbeat, physical controls, LED states and HCD Plus encoder activity.
- The 3D preview mirrors the red connection LED and the white key-feedback
  light in real time.

The firmware manager includes AVRDUDE for Base/Plus and esptool for Pro on both
Windows and macOS. It can update an identified deck or install the selected
firmware on compatible new hardware without Arduino IDE.

### Interface and personalisation

- Drag the two vertical separators to resize the profiles, preview and action
  columns. Their positions are restored at the next launch.
- HCD Pro colors can be selected from ready-made palettes or a full color
  picker for the screen, keys, outlines, header and connection LED.
- HCD Pro icon conversion and synchronization are cached, coalesced and paced
  to keep the Windows editor responsive and avoid overlapping display updates.
- The minimum white feedback-light duration is adjustable from 0 to 2000 ms.
- Optional local statistics count short and long presses without recording
  shortcuts, text, URLs or application names.
- Social, feedback and PayPal buttons are available beside the HackMan3D logo.
- The update feed supplies desktop update notifications and the HCD Plus/Pro
  roadmap percentages. It never stores or displays donation amounts.
- The interface supports English, French, Italian, Spanish, Portuguese,
  Chinese, German, Hindi, Arabic, Bengali, Indonesian, Russian, Japanese,
  Korean, Turkish, Vietnamese and Thai. Arabic uses a right-to-left layout.

### Background operation

**Windows:** **Run in background** hides the window while keeping the heartbeat
and configured actions active. The notification-area icon reopens or quits the
application.

**macOS:** the yellow minimize button sends HCD to the menu bar without creating
a blank Dock window. The menu-bar icon restores the existing interface.
**Keep in Dock**, **Start with Mac** and **Start minimized in menu bar** can be
configured independently.

Native macOS volume controls do not require Accessibility permission. Keyboard
injection, brightness and media-key actions do; the built-in permissions
assistant checks their status and opens the correct System Settings page.

### Release feed

`release/manifest.example.json` documents the optional feed used for desktop
updates and the Plus/Pro roadmap. The feed is disabled by default while the
project is private. It can be tested by setting `HCD_RELEASE_MANIFEST_URL`
without publishing any repository. Publishing a new version requires changing
`latest_version`, the two platform download links and, when appropriate, the
the public roadmap percentage. The feed deliberately contains no donation
amounts.

Donation totals and targets can remain private in
`release/roadmap.private.json` (this file is ignored by Git). Copy
`release/roadmap.private.example.json`, enter the private values, then run
`python3 release/build_public_manifest.py`. The generated public manifest
contains only the two rounded percentages. Users can read the percentages used
by the application, but cannot access the private amounts or modify the feed.

### macOS application

On a Mac, run the packaging script to create the native application bundle:

```bash
cd software
./build_macos.sh
```

The result is `software/dist/HackMan3D Control Deck.app`. Detailed installation
and permission notes are in [docs/MACOS.md](docs/MACOS.md).

Run `./build_dmg.sh` afterward to create the branded drag-to-Applications
installer.

### Windows application

On a Windows 10 or Windows 11 computer, install Python 3.11 or newer and Inno
Setup 6, then run `software\build_windows.ps1` from PowerShell. The script builds
the portable application and creates
`software\dist\HackMan3D-Control-Deck-Windows-1.5.5-Setup.exe`. The installer is
per-user, requires no administrator rights, includes the HCD firmware and AVRDUDE,
and provides clean Start menu, optional desktop and uninstall entries.

## Firmware

The desktop application contains the HCD-BASE firmware and flashes it directly
from the **Firmware** manager. Arduino IDE is not required for normal
installation or updates. HCD Plus and HCD Pro are shown in the selector as
**in development**. Their firmware remains selectable for prototype testing,
although their public assembly documentation is not ready.

The source sketch remains available in
`firmware/HackMan3DControlDeck/HackMan3DControlDeck.ino` and
`firmware/HackMan3DControlDeckPlus/HackMan3DControlDeckPlus.ino`, plus the
ESP32-S3 source in `firmware/HackMan3DControlDeckPro/`, for firmware development.

`software/build_firmware.sh` produces the branded firmware bundled with the
app. It gives each model its own USB product name and sets the manufacturer to
**HackMan3D**.

See the [HCD-BASE wiring notes](docs/WIRING.md) or the
[HCD Plus wiring notes](docs/HCD_PLUS_WIRING.md) before connecting hardware.
HCD Pro setup and USB requirements are documented in
[docs/HCD_PRO.md](docs/HCD_PRO.md).
Its optional physical feedback light is driven through a MOSFET from the
accessible `AD / IO6` signal on the rear Sensor AD connector.
