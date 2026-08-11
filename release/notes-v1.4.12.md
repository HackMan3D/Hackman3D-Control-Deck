# HackMan3D Control Deck 1.4.12

This update expands HCD Pro display customization with seven additional
ready-made color themes.

- **Arctic** — pale background with cool blue outlines.
- **Ruby** — deep black-red interface with bright red accents.
- **Emerald** — dark green interface with vivid green accents.
- **Violet** — dark purple interface with luminous violet outlines.
- **Amber** — warm black and orange interface.
- **Cyberpunk** — navy, cyan, magenta and yellow accents.
- **Snow** — bright white interface with dark text.
- Every theme now includes a visual palette preview in the selector.
- Every preset remains fully editable through the existing color wheel.
- Large HCD Pro style changes now use a protected display-update screen and
  one clean final redraw, avoiding intermediate Windows refresh artefacts.
- Consecutive layout changes are queued safely instead of dropping the newest
  appearance while a previous icon transfer is still running.
- Assigning a shortcut no longer restarts the HCD Pro or reloads its complete
  interface; only the changed content is transferred and redrawn.

HCD Pro firmware 1.2.38 adds the protected atomic display synchronization.
