#include "HCD_Buttons.h"

#include <Arduino.h>

#include "HCD_Config.h"
#include "HCD_Leds.h"
#include "HCD_Protocol.h"

namespace {

struct ButtonState {
  bool rawPressed;
  bool stablePressed;
  unsigned long changedAt;
};

ButtonState keys[HcdConfig::KEY_COUNT];
uint8_t pressedKeyCount = 0;

void applyKeyChange(uint8_t index, bool pressed) {
  keys[index].stablePressed = pressed;
  if (pressed) {
    if (pressedKeyCount < HcdConfig::KEY_COUNT) {
      ++pressedKeyCount;
    }
  } else if (pressedKeyCount > 0) {
    --pressedKeyCount;
  }
  HcdLeds::setAnyKeyPressed(pressedKeyCount > 0);
  HcdProtocol::sendKeyEvent(index + 1, pressed);
}

}  // namespace

namespace HcdButtons {

void begin() {
  const unsigned long now = millis();
  for (uint8_t index = 0; index < HcdConfig::KEY_COUNT; ++index) {
    pinMode(HcdConfig::KEY_PINS[index], INPUT_PULLUP);
    const bool pressed = digitalRead(HcdConfig::KEY_PINS[index]) == LOW;
    keys[index] = {pressed, pressed, now};
    if (pressed) {
      ++pressedKeyCount;
    }
  }
  HcdLeds::setAnyKeyPressed(pressedKeyCount > 0);
}

void update() {
  const unsigned long now = millis();
  for (uint8_t index = 0; index < HcdConfig::KEY_COUNT; ++index) {
    const bool pressed = digitalRead(HcdConfig::KEY_PINS[index]) == LOW;
    if (pressed != keys[index].rawPressed) {
      keys[index].rawPressed = pressed;
      keys[index].changedAt = now;
    }
    if (pressed != keys[index].stablePressed &&
        now - keys[index].changedAt >= HcdConfig::DEBOUNCE_MS) {
      applyKeyChange(index, pressed);
    }
  }
}

}  // namespace HcdButtons
