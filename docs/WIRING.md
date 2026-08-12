# Pro Micro wiring

![HackMan3D Control Deck V1 wiring diagram](images/HCD_Wiring_Diagram_V1.svg)

The diagram above is validated against `HCD_Config.h` from firmware 1.7.1.
The original draft used sequential key numbers; the firmware deliberately
reverses each physical row so the front-panel numbering matches the 3 × 3
software preview.

All switch inputs use the ATmega32U4 internal pull-ups. Connect each switch
between its assigned pin and GND.

| Front-panel control | Pro Micro pin |
| --- | --- |
| Key 1 | D4 |
| Key 2 | D3 |
| Key 3 | D2 |
| Key 4 | D7 |
| Key 5 | D6 |
| Key 6 | D5 |
| Key 7 | D10 |
| Key 8 | D9 |
| Key 9 | D8 |
| Connection MOSFET gate | 21 (A3) |
| Key-feedback MOSFET gate | 1 (TX) |

Pins 14, 15, 16, 18, 19 and 20 are unused in the V1 and reserved for future
expansion.

Both lights are switched on the low side by separate logic-level N-channel
MOSFETs. For each channel:

1. Connect the Pro Micro output to the MOSFET gate through a 100 Ω resistor.
2. Connect the MOSFET source to GND.
3. Connect the MOSFET drain to the LED cathode (negative side).
4. Connect the LED anode to +5 V through its current-limiting resistor.

Each individual bare LED still needs a suitable current-limiting resistor,
typically 150–330 Ω at 5 V depending on its forward voltage and desired current.
For a ready-made 5 V LED module or strip that already includes resistors, do not
add a second series resistor. The LED supply and Pro Micro must share GND.

Use MOSFETs that switch fully from a 5 V logic signal, such as a 2N7000 for a
small indicator LED or an AO3400A for a higher-current light. No flyback diode is
needed for a purely LED load.

Both MOSFET gate outputs are active-high. Pin 0 remains unused. Native USB
serial on the Pro Micro does not consume pins 0 and 1.

The connection channel turns on after the desktop app sends `HCD_PING`. It turns
off if no heartbeat is received for three seconds. The feedback channel only
operates while that app connection is active: it turns on while at least one of
the nine keys is held and turns off after the last key is released. With no app
heartbeat, both lights remain off.
