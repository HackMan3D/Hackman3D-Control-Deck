# HCD communication protocol

HCD-BASE and HCD Plus use a 115200-baud serial connection. HCD Pro uses the same
newline-delimited UTF-8/ASCII commands over a local TCP connection. Fields are
separated with `|`.

## App to device

| Message | Purpose |
| --- | --- |
| `HCD_PING` | Heartbeat, sent once per second |
| `HCD_GET_INFO` | Request product and firmware information |
| `HCD_PRO_LABEL|1|V29ya3NwYWNl` | Set a Pro touch-key label; the last field is Base64 UTF-8 |
| `HCD_PRO_DISPLAY|1|1|1` | Set Pro icon size (0–3), label visibility (0/1), and key style (0–2) |

## Device to app

| Message | Purpose |
| --- | --- |
| `HCD_PONG` | Heartbeat acknowledgement |
| `HCD_READY|1.7.0` | Device boot announcement |
| `HCD_INFO|HackMan3D Control Deck|HCD-BASE|1.7.0|9` | HCD-BASE information |
| `HCD_INFO|HackMan3D Control Deck Plus|HCD-PLUS|1.0.0|12|2` | HCD Plus information, including the potentiometer count |
| `HCD_INFO|HackMan3D Control Deck Pro|HCD-PRO|1.0.0|12|0` | HCD Pro Wi-Fi touch-screen information |
| `HCD_KEY|1|DOWN` | Physical key press; IDs are 1–9 on Base and 1–12 on Plus |
| `HCD_KEY|1|UP` | Physical key release |
| `HCD_POT_BUTTON|1|DOWN` | HCD Plus potentiometer push switch pressed |
| `HCD_POT_BUTTON|1|UP` | HCD Plus potentiometer push switch released |
| `HCD_POT|1|768` | HCD Plus analog value; range is 0–1023 |

The firmware considers the PC app connected after a valid `HCD_PING`. If no
heartbeat arrives for about 3000 ms, the connection LED is turned off.

## HCD Pro discovery

The app broadcasts `HCD_DISCOVER` on UDP port 42100. An available HCD Pro
answers the sender with:

```text
HCD_HERE|HackMan3D Control Deck Pro|HCD-PRO|1.0.0|12|0|42101
```

The app then opens TCP port 42101 and starts the normal heartbeat. The computer
and display must be on the same trusted local network; these ports must never be
forwarded to the public internet.

During the first USB installation, the app can send Wi-Fi credentials over the
ESP32-S3 serial port:

```text
HCD_WIFI_CONFIG|<base64-ssid>|<base64-password>
```

Credentials are stored in the ESP32 non-volatile preferences. They are never
sent over the normal network protocol.
