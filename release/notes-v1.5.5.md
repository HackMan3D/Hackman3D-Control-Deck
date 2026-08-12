# HackMan3D Control Deck 1.5.5

This release adds model-specific lighting controls and makes HCD Pro icon
synchronization reliable on both macOS and Windows.

## Lighting

- HCD Base and HCD Plus expose independent brightness controls for the red
  connection LED and the white action-feedback strip.
- HCD Pro exposes brightness control for its white action-feedback strip.
- Settings are stored independently for Base, Plus and Pro.
- Brightness changes intensity only; each light keeps its normal connection or
  key-press behavior.

## HCD Pro icons

- Firmware now acknowledges each complete icon transfer with its CRC32.
- Missing or incomplete icons are retried automatically up to three times.
- The desktop no longer marks an icon as synchronized before the Pro confirms
  receipt.

## Bundled firmware

- HCD Base 1.7.1
- HCD Plus 1.1.2
- HCD Pro 1.3.6

## Validation

- All three firmware targets compile successfully.
- 84 automated desktop tests pass.
- macOS and Windows installers contain the same source features and bundled
  firmware images.
