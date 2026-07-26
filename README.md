# HackMan3D Control Deck

HackMan3D Control Deck (HCD) is a programmable desktop controller built around an
Arduino Pro Micro. The repository contains the Windows and macOS configuration
app, the branded HackMan interface and the device firmware.

## Download version 0.17.0

The project is currently private. These downloads are available only to people
who have access to this repository.

- [Download for macOS (.dmg)](https://github.com/HackMan3D/Hackman3D-Control-Deck/releases/download/v0.17.0/HackMan3D-Control-Deck-macOS-0.17.0.dmg)
- [Download for Windows (.exe)](https://github.com/HackMan3D/Hackman3D-Control-Deck/releases/download/v0.17.0/HackMan3D-Control-Deck-Windows-0.17.0-Setup.exe)

## Interface

![HackMan3D Control Deck main interface](docs/screenshots/main-window.png)

Select any key on the 3D preview to configure its short-press and long-press
actions from the editor.

![HackMan3D Control Deck key editor](docs/screenshots/key-editor.png)

## How it works

1. Connect the HCD to the computer and keep the desktop application running.
2. The application detects the controller and maintains the connection LED
   through the `HCD_PING` / `HCD_PONG` heartbeat.
3. Create or select a profile, then click one of the nine keys in the 3D
   preview.
4. Assign a shortcut, system command, text, website or application to the short
   press and, optionally, a different action to the long press.
5. Minimize the application to the macOS menu bar or Windows notification area;
   profiles and actions continue to work in the background.

## Hardware target

- 9 MX switches in a 3 × 3 layout
- 1 white PC-connection LED
- 1 white key-feedback LED
- Arduino Pro Micro (ATmega32U4, 5 V / 16 MHz)

The connection LED is controlled by the app heartbeat. It turns off about three
seconds after the app stops responding. The feedback LED remains on while one or
more of the nine MX keys is held, but only while the desktop app is connected.

The V1 deliberately has no rotary encoders. Pins D14 through D20 remain free for
a possible V2.

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

The progress indicators in the application show only a percentage. No donation
amount or financial target is stored or displayed. The exact feature set will
evolve after prototype testing and community feedback.

### HCD Plus

The Plus edition is intended to expand the base experience while keeping the
controller simple and accessible:

- more physical controls or a larger configurable layout;
- richer white or RGB visual feedback;
- improved enclosure, ergonomics and customization;
- stronger multi-profile and multi-deck workflows;
- full compatibility with the existing HCD desktop application.

### HCD Pro

The Pro edition is the longer-term, advanced-workflow direction:

- dynamic visual identification of actions;
- additional rotary, touch or display-based controls;
- deeper application and automation integrations;
- faster profile switching and advanced status feedback;
- premium construction and options intended for intensive daily use.

Support for the current HCD directly contributes to the research and prototypes
needed to explore these Plus and Pro editions.

## Repository layout

```text
firmware/HackMan3DControlDeck/   Arduino firmware
software/                      PySide6 desktop app
docs/                          protocol and wiring notes
```

## Desktop app

Python 3.11 or newer is recommended. The application supports Windows and
macOS.

```powershell
cd software
py -m venv .venv
.venv\Scripts\activate
python -m pip install -e .
hackman3d-control-deck
```

The app scans serial ports automatically. Profiles are stored in the user's
application-data folder and can be edited from the right-hand action panel.
Arduino and USB serial ports are prioritised during discovery, and unsuitable
ports are skipped quickly. The red software indicator mirrors the physical
connection light on the Control Deck.
The monochrome links beside the HackMan logo open the official Creality Cloud,
MakerWorld, TikTok, Instagram and YouTube pages, the contact email composer and
the PayPal support page.
A translated support banner explains that the project is shared free of charge
and provides direct actions for sending feedback or supporting continued work.
The app can check a release manifest in the background and offer the correct
macOS or Windows download when a newer desktop version is available.
The same manifest supplies the HCD Plus and HCD Pro roadmap percentages. Only
the percentages are transmitted and displayed; no donation amount or financial
target is stored by the application.
The serial port is identified through the HCD protocol. The interface displays
the product name reported by the firmware instead of the operating-system port
such as `cu.usbmodem101`; `HCD-BASE` identifies the current hardware model and
leaves room for future V2 or Pro variants.
The firmware manager embeds HCD-BASE firmware 1.7.0 and the official AVRDUDE
tool for macOS and Windows. It can safely update an identified Control Deck or,
after an explicit warning, install HCD on a new 5 V / 16 MHz ATmega32U4
Leonardo/Pro Micro. The application remains open throughout bootloader
detection, upload and verification, then reconnects automatically.
For keyboard actions, the editor offers common shortcuts while still accepting
custom combinations. The shortcut list adapts to macOS or Windows and shows the
purpose beside every key combination. System commands provide volume up/down,
mute, play/pause, previous/next track and screen brightness controls. For launch
actions on macOS, it lists the applications
installed in the Applications folders and keeps the manual file picker available.
Selecting an application fills its name automatically and displays its native
icon directly over the matching key on the central 3D Control Deck preview.
Clicking a key in the preview opens its editor. Profiles can be created,
renamed and deleted from the sidebar; deletion always requires confirmation.
Profiles can also be duplicated, exported as portable `.hcdprofile` files,
imported on another computer, or included in a complete `.hcdbackup` archive.
Applications can be dragged directly from Finder or Explorer onto a preview
key to create a launch action and retrieve the native application icon.
Each key has separate **Short press** and **Long press** editor tabs. Both tabs
support their own single action and test button; the long-press tab also
provides a configurable hold duration. Older sequence-based profiles are
migrated by preserving the first short-press and long-press action.
The preview's red connection LED follows the live heartbeat, and its white front
bar remains illuminated while at least one physical key is held down.
On macOS, volume up, volume down and mute use the native audio command and do
not require Accessibility permission. Keyboard injection, brightness and media
key events still require macOS Accessibility authorization.
A live diagnostics window reports the HCD model, firmware, serial port,
heartbeat, all nine physical key states and both LED states.
When an older compatible HCD firmware is detected, the application offers to
open the integrated firmware manager and install the included update.
Changing the action type clears the previous editor values to avoid mixing two
configurations. A centered button below the 3D preview resets all nine key
assignments in the current profile after confirmation.
The editor reports duplicate short-press or long-press assignments in the
current profile. Optional local-only statistics count short and long key uses
without storing action values, typed text, URLs or application names.
The macOS permissions assistant reports Accessibility status and opens the
correct System Settings page.
The minimum white feedback LED duration is adjustable from 0 to 2000 ms. The
setting is sent automatically to HCD-BASE firmware 1.7.0 at every connection.
The language selector in the profile sidebar updates the interface immediately
and supports English, French, Italian, Spanish, Portuguese, Chinese, German,
Hindi, Arabic, Bengali, Indonesian, Russian, Japanese, Korean, Turkish,
Vietnamese and Thai. Arabic automatically switches the interface to a
right-to-left layout.
On Windows, the **Run in background** button hides the window while keeping the
serial heartbeat and configured actions active. Use the notification-area icon
to reopen or fully quit the app.

On macOS, the yellow minimize button sends HCD directly to the menu bar. The
Dock icon disappears while HCD runs in the background; the menu-bar icon reopens
the window and restores its Dock icon. HCD intercepts the native yellow button
before AppKit starts miniaturizing, so no blank or separate window thumbnail is
created in the Dock.
If the user pins HCD with **Keep in Dock**, clicking that launcher restores the
existing interface instead of creating a blank window.
**Start with Mac** installs a per-user
login agent. **Start minimized in menu bar** separately controls whether HCD
opens its window or starts directly in the macOS menu bar.

### Release feed

`release/manifest.example.json` documents the optional feed used for desktop
updates and the Plus/Pro roadmap. The feed is disabled by default while the
project is private. It can be tested by setting `HCD_RELEASE_MANIFEST_URL`
without publishing any repository. Publishing a new version requires changing
`latest_version`, the two platform download links and, when appropriate, the
two integer roadmap percentages. The feed deliberately contains no donation
amounts.

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
`software\dist\HackMan3D-Control-Deck-Windows-0.17.0-Setup.exe`. The installer is
per-user, requires no administrator rights, includes the HCD firmware and AVRDUDE,
and provides clean Start menu, optional desktop and uninstall entries.

## Firmware

Open `firmware/HackMan3DControlDeck/HackMan3DControlDeck.ino` in Arduino IDE, select
Arduino Leonardo (or the matching Pro Micro board definition), then upload.
The firmware uses only the standard Arduino core.

`software/build_firmware.sh` produces the branded firmware bundled with the
app. It sets the USB product to **HackMan3D Control Deck** and the manufacturer to
**HackMan3D**.

See [docs/WIRING.md](docs/WIRING.md) before connecting switches or LEDs.
