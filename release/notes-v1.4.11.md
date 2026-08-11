# HackMan3D Control Deck 1.4.11

This update improves the Windows editor and HCD Pro display workflow while
also fixing community roadmap refreshes.

- The profiles, preview and action columns can be resized with two draggable
  separators. Their positions are saved for the next launch.
- Actions save automatically after selection or editing; the separate Save
  button is no longer required.
- HCD Pro icon conversion is now performed natively, unchanged layouts are not
  recalculated, and overlapping display uploads are discarded. Full 28-icon
  transfers are also substantially faster.
- HCD Pro firmware 1.2.37 adds customizable screen, key, outline, header and
  connection LED colors. The app provides presets and a complete color picker.
- The desktop preview mirrors the selected Pro colors.

- The public roadmap percentage is fetched at every application launch instead
  of reusing a six-hour-old value from local settings.
- The feed is checked again automatically every six hours while the application
  remains open.
- Requests continue to bypass the GitHub raw-file cache.
- Only the public percentage is downloaded. Donation amounts and targets remain
  private and are not included in the application or its public feed.

The current public roadmap progress is 4%.
