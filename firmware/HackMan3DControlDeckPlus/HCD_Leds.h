#pragma once

#include <Arduino.h>

namespace HcdLeds {

void begin();
void update();
void setPcConnected(bool connected);
void setAnyKeyPressed(bool pressed);
void setFeedbackHoldMs(uint16_t durationMs);
void setConnectionBrightness(uint8_t percentage);
void setFeedbackBrightness(uint8_t percentage);

}  // namespace HcdLeds
