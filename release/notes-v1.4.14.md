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
- HCD Pro firmware 1.2.44 adds a 10 mm corner-safe interface: the header,
  touch grid and faders are inset from the enclosure's rounded bezel.
- The Pro now keeps one stable scan-out framebuffer and applies bounded partial
  updates from an internal-memory render buffer, avoiding PSRAM contention and
  persistent artifacts during icon synchronization.
- Stale icon cache entries are discarded before replacement and scaled icon
  rendering uses less PSRAM bandwidth.
- The desktop app updates outdated Pro firmware before synchronizing its full
  display layout, preserving a safe recovery path.
- The display update was validated with 11 icons transferred in one session,
  without freezing or graphical artifacts.
