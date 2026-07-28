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
| `HCD_READY|1.7.0` | Device boot announcement |
| `HCD_INFO|HackMan3D Control Deck|HCD-BASE|1.7.0|9` | HCD-BASE information |
| `HCD_INFO|HackMan3D Control Deck Plus|HCD-PLUS|1.0.0|12|2` | HCD Plus information, including the potentiometer count |
| `HCD_KEY|1|DOWN` | Physical key press; IDs are 1–9 on Base and 1–12 on Plus |
| `HCD_KEY|1|UP` | Physical key release |
| `HCD_POT_BUTTON|1|DOWN` | HCD Plus potentiometer push switch pressed |
| `HCD_POT_BUTTON|1|UP` | HCD Plus potentiometer push switch released |
| `HCD_POT|1|768` | HCD Plus analog value; range is 0–1023 |

The firmware considers the PC app connected after a valid `HCD_PING`. If no
heartbeat arrives for 3000 ms, the connection LED is turned off.
