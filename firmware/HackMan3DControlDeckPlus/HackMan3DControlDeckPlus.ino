/*
 * HackMan3D Control Deck Plus
 * Firmware for the 12-key controller with two clickable rotary encoders.
 *
 * Hardware: Arduino Pro Micro / ATmega32U4 + MCP23017
 */

#include "HCD_Controls.h"
#include "HCD_Leds.h"
#include "HCD_Protocol.h"

void setup() {
  HcdLeds::begin();
  HcdControls::begin();
  HcdProtocol::begin();
}

void loop() {
  HcdProtocol::update();
  HcdControls::update();
  HcdLeds::update();
}
