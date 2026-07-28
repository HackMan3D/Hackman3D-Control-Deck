# HCD Plus wiring

HCD Plus uses an Arduino Pro Micro (ATmega32U4, 5 V / 16 MHz) and one
MCP23017 I/O expander at address `0x20`. The firmware uses the Arduino `Wire`
library directly; no third-party MCP23017 library is required.

## Pro Micro connections

| Function | Pro Micro pin |
| --- | --- |
| MCP23017 SDA | D2 / SDA |
| MCP23017 SCL | D3 / SCL |
| Potentiometer 1 wiper | A0 |
| Potentiometer 2 wiper | A1 |
| Connection-light MOSFET gate | A3 / D21 |
| Key-feedback MOSFET gate | TX / D1 |
| MCP23017 and potentiometer supply | VCC (5 V) |
| Common ground | GND |

Connect each potentiometer's two outer terminals to VCC and GND, and its
centre wiper to the assigned analog input. Reverse the two outer terminals if
the direction is opposite to the intended behaviour.

## MCP23017 connections

Tie `A0`, `A1` and `A2` on the MCP23017 to GND to select address `0x20`.
Connect `RESET` to VCC. Power the expander from the Pro Micro's VCC and GND.
Place a 100 nF ceramic decoupling capacitor directly between the MCP23017 VDD
and VSS pins.

All controls are active-low and use the MCP23017's internal pull-ups. Connect
the other side of every switch to the common GND.

| Control | MCP23017 input |
| --- | --- |
| Key 1 | GPA0 |
| Key 2 | GPA1 |
| Key 3 | GPA2 |
| Key 4 | GPA3 |
| Key 5 | GPA4 |
| Key 6 | GPA5 |
| Key 7 | GPA6 |
| Key 8 | GPA7 |
| Key 9 | GPB0 |
| Key 10 | GPB1 |
| Key 11 | GPB2 |
| Key 12 | GPB3 |
| Potentiometer 1 click | GPB4 |
| Potentiometer 2 click | GPB5 |

`GPB6` and `GPB7` remain available for a later hardware revision.

## Status lights

The two IRLB8721 low-side MOSFET circuits are identical to HCD-BASE:

- A3/D21 drives the red connection light through a 100 Ω gate resistor.
- TX/D1 drives the white action-feedback light through a 100 Ω gate resistor.
- Each MOSFET source connects to GND.
- Each MOSFET drain connects to the negative side of its light.
- The positive side of each light connects to 5 V with the appropriate
  current limiting.

All grounds must be common. The white feedback light only operates while the
desktop app heartbeat is active.
