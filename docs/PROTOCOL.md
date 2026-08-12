# HCD communication protocol

HCD-BASE, HCD Plus and HCD Pro use newline-delimited UTF-8/ASCII commands over
a 115200-baud USB serial connection. Fields are separated with `|`.

## App to device

| Message | Purpose |
| --- | --- |
| `HCD_PING` | Heartbeat, sent once per second |
| `HCD_GET_INFO` | Request product, model, firmware and control information |
| `HCD_SET_LED_HOLD|120` | Set the minimum physical feedback-light duration |
| `HCD_PRO_SYNC_BEGIN` | Lock the Pro update overlay before an atomic snapshot |
| `HCD_PRO_DISPLAY|1|0|0|0|1` | Set Pro icon size, reserved fields, second-fader state and slider mode |
| `HCD_PRO_COLORS|080808|171717|404040|FFFFFF|F02020` | Set Pro screen, key, outline, header and connection-indicator colors |
| `HCD_PRO_ICON_BEGIN|1|8192|1234abcd` | Begin a 64 × 64 RGB565 Pro icon transfer |
| `HCD_PRO_ICON_CHUNK|...` | Send one Base64 icon chunk |
| `HCD_PRO_ICON_END|1` | Finish one icon transfer |
| `HCD_PRO_ICON_CLEAR|1` | Clear one Pro icon |
| `HCD_PRO_SLIDER_STATE|1|512` | Mirror a host slider state on the Pro display |
| `HCD_PRO_SYNC_END` | Commit the visual snapshot and reveal the key grid |

## Device to app

| Message | Purpose |
| --- | --- |
| `HCD_PONG` | Heartbeat acknowledgement |
| `HCD_READY|1.7.1` | Device boot announcement |
| `HCD_INFO|HackMan3D Control Deck|HCD-BASE|1.7.1|9` | HCD-BASE information |
| `HCD_INFO|HackMan3D Control Deck Plus|HCD-PLUS|1.1.2|12|2` | HCD Plus information |
| `HCD_INFO|HackMan3D Control Deck Pro|HCD-PRO|1.3.6|28|0|...` | HCD Pro information and icon signatures |
| `HCD_KEY|1|DOWN` | Key or Pro touch-key pressed |
| `HCD_KEY|1|UP` | Key or Pro touch-key released |
| `HCD_POT_BUTTON|1|DOWN` | HCD Plus encoder switch pressed |
| `HCD_POT_BUTTON|1|UP` | HCD Plus encoder switch released |
| `HCD_ENCODER|1|LEFT` | HCD Plus encoder rotated counter-clockwise |
| `HCD_ENCODER|1|RIGHT` | HCD Plus encoder rotated clockwise |

Desktop lighting commands:

| Command | Purpose |
| --- | --- |
| `HCD_SET_CONNECTION_BRIGHTNESS|0..100` | Base/Plus red heartbeat LED PWM level |
| `HCD_SET_FEEDBACK_BRIGHTNESS|0..100` | White action bar PWM level on all models |
| `HCD_SET_LED_HOLD|0..2000` | Minimum action-bar duration in milliseconds |

The brightness commands change intensity only. They do not change when a light
is allowed to turn on.

HCD Pro firmware 1.3.6 replies with
`HCD_PRO_ICON_ACK|key|crc32` after a complete icon transfer, or
`HCD_PRO_ICON_NACK|key` after an incomplete transfer. The desktop retries icons
that are not acknowledged.

The firmware considers the desktop app connected after a valid `HCD_PING`. If
no heartbeat arrives for roughly three seconds, the connection indicator and
physical feedback light turn off. Pro touch events are ignored until the USB
heartbeat is active.

## USB discovery

The application probes compatible serial ports and accepts a device only after
receiving valid HCD protocol replies. It recognizes official Arduino USB IDs,
ESP32-S3 USB/JTAG devices and the Waveshare `USB Single Serial` bridge
(`1A86:55D3`). Windows asserts DTR when opening Arduino CDC ports and can detect
a different HCD model reusing the same COM number without restarting the app.
