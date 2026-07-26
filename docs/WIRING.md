# Pro Micro wiring

All switch inputs use the ATmega32U4 internal pull-ups. Connect each switch
between its assigned pin and GND.

| Function | Pro Micro pin |
| --- | --- |
| Keys 1–9 | 2, 3, 4, 5, 6, 7, 8, 9, 10 |
| Connection MOSFET gate | 21 (A3) |
| Key-feedback MOSFET gate | 1 (TX) |

Pins 14, 15, 16, 18, 19 and 20 are unused in the V1 and reserved for future
expansion.

Both lights are switched on the low side by separate logic-level N-channel
MOSFETs. For each channel:

1. Connect the Pro Micro output to the MOSFET gate through a 100–220 Ω resistor.
2. Add a 10 kΩ resistor between gate and GND so the light remains off while the
   Pro Micro starts.
3. Connect the MOSFET source to GND.
4. Connect the MOSFET drain to the LED cathode (negative side).
5. Connect the LED anode to +5 V through its current-limiting resistor.

Each individual white LED still needs a suitable current-limiting resistor,
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
