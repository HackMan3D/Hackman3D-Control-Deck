#pragma once

#include <Arduino.h>

namespace HcdProtocol {

void begin();
void update();
void sendKeyEvent(uint8_t keyId, bool pressed);
void sendSliderEvent(uint8_t sliderId, uint16_t value);

}  // namespace HcdProtocol
