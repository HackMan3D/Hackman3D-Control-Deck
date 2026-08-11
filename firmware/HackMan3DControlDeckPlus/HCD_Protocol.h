#pragma once

#include <Arduino.h>

namespace HcdProtocol {

void begin();
void update();
void sendKeyEvent(uint8_t keyId, bool pressed);
void sendPotButtonEvent(uint8_t potentiometerId, bool pressed);
void sendEncoderEvent(uint8_t encoderId, bool clockwise);

}  // namespace HcdProtocol
