# HackMan3D Control Deck 1.4.10

This update improves application icons and system-action editing on Windows.

## Windows fixes

- Start menu shortcuts are now resolved to their original icon file or
  executable before an icon is extracted. This avoids enlarging the small,
  low-resolution thumbnail embedded in a `.lnk` file.
- Application icons are still cropped and normalised before they are displayed
  in the desktop preview or transferred to HCD Pro.
- The selected system command is retained independently from the visible menu.
  Commands such as **Shut down computer** can now be saved reliably on every
  HCD Pro touch key, including key 28.
- Returning a selector to its empty entry now clears the previously selected
  value instead of retaining a stale command.

## Validation

The complete desktop test suite passes, including dedicated tests for Windows
shortcut icon resolution and saving the shutdown command on HCD Pro key 28.

HCD Plus and HCD Pro remain marked **in development** for prototype testing.
