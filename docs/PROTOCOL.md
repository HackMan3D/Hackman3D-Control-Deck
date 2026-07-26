# HCD serial protocol

The HackMan3D Control Deck uses newline-delimited UTF-8/ASCII messages at 115200
baud. Fields are separated with `|`.

## App to device

| Message | Purpose |
| --- | --- |
| `HCD_PING` | Heartbeat, sent once per second |
| `HCD_GET_INFO` | Request product and firmware information |

## Device to app

| Message | Purpose |
| --- | --- |
| `HCD_PONG` | Heartbeat acknowledgement |
| `HCD_READY|1.1.0` | Device boot announcement |
| `HCD_INFO|HackMan3D Control Deck|1.1.0|9` | Device information |
| `HCD_KEY|1|DOWN` | MX key event; IDs are 1–9 |
| `HCD_KEY|1|UP` | MX key release |

The firmware considers the PC app connected after a valid `HCD_PING`. If no
heartbeat arrives for 3000 ms, the connection LED is turned off.
