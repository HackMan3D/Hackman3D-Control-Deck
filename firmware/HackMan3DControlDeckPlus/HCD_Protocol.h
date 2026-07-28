#pragma once

#include <Arduino.h>

namespace HcdProtocol {

void begin();
void update();
void sendKeyEvent(uint8_t keyId, bool pressed);
void sendPotButtonEvent(uint8_t potentiometerId, bool pressed);
void sendPotentiometerEvent(uint8_t potentiometerId, uint16_t value);

}  // namespace HcdProtocol
