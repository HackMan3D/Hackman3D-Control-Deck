# HackMan3D Control Deck 1.4.14

- Profiles are now isolated by hardware model. HCD-BASE, HCD-PLUS and HCD-PRO
  each keep their own profile list and assignments.
- HCD Plus now supports two clickable EC11 rotary encoders instead of analog
  potentiometers.
- Each encoder has one simple mode selector: output volume, microphone volume
  or screen brightness. Encoder 1 defaults to sound and encoder 2 to microphone.
- Microphone-volume increase and decrease commands are available on macOS and
  Windows.
- The HCD Plus preview now matches the physical layout: two encoders on the
  left and twelve keys in a 4 × 3 grid.
- Bundled HCD Plus firmware 1.1.1 adds quadrature decoding tuned for the
  two transitions produced by each module detent and retains the
  robust MCP23017 address detection introduced in the previous test build.
- HCD Pro firmware 1.2.40 adds a 10 mm corner-safe interface: the header,
  touch grid and faders are inset from the enclosure's rounded bezel.
- The Pro now draws into two complete display buffers and swaps them between
  panel scans, preventing a partially redrawn interface from becoming visible.
