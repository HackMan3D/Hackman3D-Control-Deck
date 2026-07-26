/*
 * HackMan3D Control Deck
 * Firmware for the HCD 3x3 programmable desktop controller.
 *
 * Hardware: Arduino Pro Micro / ATmega32U4
 */

#include "HCD_Buttons.h"
#include "HCD_Leds.h"
#include "HCD_Protocol.h"

void setup() {
  HcdLeds::begin();
  HcdButtons::begin();
  HcdProtocol::begin();
}

void loop() {
  HcdProtocol::update();
  HcdButtons::update();
  HcdLeds::update();
}
