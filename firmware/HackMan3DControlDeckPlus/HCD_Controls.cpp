#include "HCD_Controls.h"

#include <Arduino.h>

#include "HCD_Config.h"
#include "HCD_Leds.h"
#include "HCD_Mcp23017.h"
#include "HCD_Protocol.h"

namespace {

struct ButtonState {
  bool rawPressed;
  bool stablePressed;
  unsigned long changedAt;
};

ButtonState keys[HcdConfig::KEY_COUNT];
ButtonState potButtons[HcdConfig::POT_BUTTON_COUNT];
uint8_t encoderStates[HcdConfig::ENCODER_COUNT];
int8_t encoderSteps[HcdConfig::ENCODER_COUNT];
uint8_t pressedControlCount = 0;

constexpr int8_t ENCODER_TRANSITION_TABLE[16] = {
    0, -1, 1, 0,
    1, 0, 0, -1,
    -1, 0, 0, 1,
    0, 1, -1, 0,
};

bool bitPressed(uint16_t inputs, uint8_t bit) {
  return (inputs & (static_cast<uint16_t>(1) << bit)) == 0;
}

void updateFeedback() {
  HcdLeds::setAnyKeyPressed(pressedControlCount > 0);
}

void applyKeyChange(uint8_t index, bool pressed) {
  keys[index].stablePressed = pressed;
  if (pressed) {
    if (pressedControlCount < HcdConfig::KEY_COUNT + HcdConfig::POT_BUTTON_COUNT) {
      ++pressedControlCount;
    }
  } else if (pressedControlCount > 0) {
    --pressedControlCount;
  }
  updateFeedback();
  HcdProtocol::sendKeyEvent(index + 1, pressed);
}

void applyPotButtonChange(uint8_t index, bool pressed) {
  potButtons[index].stablePressed = pressed;
  if (pressed) {
    if (pressedControlCount < HcdConfig::KEY_COUNT + HcdConfig::POT_BUTTON_COUNT) {
      ++pressedControlCount;
    }
  } else if (pressedControlCount > 0) {
    --pressedControlCount;
  }
  updateFeedback();
  HcdProtocol::sendPotButtonEvent(index + 1, pressed);
}

void updateButton(
    ButtonState& state,
    bool pressed,
    unsigned long now,
    void (*apply)(uint8_t, bool),
    uint8_t index) {
  if (pressed != state.rawPressed) {
    state.rawPressed = pressed;
    state.changedAt = now;
  }
  if (pressed != state.stablePressed &&
      now - state.changedAt >= HcdConfig::DEBOUNCE_MS) {
    apply(index, pressed);
  }
}

uint8_t readEncoderState(uint8_t index) {
  return (digitalRead(HcdConfig::ENCODER_A_PINS[index]) == HIGH ? 2 : 0) |
         (digitalRead(HcdConfig::ENCODER_B_PINS[index]) == HIGH ? 1 : 0);
}

void updateEncoders() {
  for (uint8_t index = 0; index < HcdConfig::ENCODER_COUNT; ++index) {
    const uint8_t current = readEncoderState(index);
    const uint8_t transition = (encoderStates[index] << 2) | current;
    encoderStates[index] = current;
    encoderSteps[index] += ENCODER_TRANSITION_TABLE[transition];
    if (encoderSteps[index] >= HcdConfig::ENCODER_TRANSITIONS_PER_DETENT) {
      encoderSteps[index] = 0;
      HcdProtocol::sendEncoderEvent(index + 1, true);
    } else if (encoderSteps[index] <= -HcdConfig::ENCODER_TRANSITIONS_PER_DETENT) {
      encoderSteps[index] = 0;
      HcdProtocol::sendEncoderEvent(index + 1, false);
    }
  }
}

}  // namespace

namespace HcdControls {

void begin() {
  HcdMcp23017::begin();
  const unsigned long now = millis();
  const uint16_t inputs = HcdMcp23017::readInputs();

  for (uint8_t index = 0; index < HcdConfig::KEY_COUNT; ++index) {
    const bool pressed = bitPressed(inputs, HcdConfig::MCP_KEY_BITS[index]);
    keys[index] = {pressed, pressed, now};
    if (pressed) {
      ++pressedControlCount;
    }
  }
  for (uint8_t index = 0; index < HcdConfig::POT_BUTTON_COUNT; ++index) {
    const bool pressed = bitPressed(
        inputs, HcdConfig::MCP_POT_BUTTON_BITS[index]);
    potButtons[index] = {pressed, pressed, now};
    if (pressed) {
      ++pressedControlCount;
    }
  }
  for (uint8_t index = 0; index < HcdConfig::ENCODER_COUNT; ++index) {
    pinMode(HcdConfig::ENCODER_A_PINS[index], INPUT_PULLUP);
    pinMode(HcdConfig::ENCODER_B_PINS[index], INPUT_PULLUP);
    encoderStates[index] = readEncoderState(index);
    encoderSteps[index] = 0;
  }
  updateFeedback();
}

void update() {
  const unsigned long now = millis();
  const uint16_t inputs = HcdMcp23017::readInputs();
  if (HcdMcp23017::isAvailable()) {
    for (uint8_t index = 0; index < HcdConfig::KEY_COUNT; ++index) {
      updateButton(
          keys[index],
          bitPressed(inputs, HcdConfig::MCP_KEY_BITS[index]),
          now,
          applyKeyChange,
          index);
    }
    for (uint8_t index = 0; index < HcdConfig::POT_BUTTON_COUNT; ++index) {
      updateButton(
          potButtons[index],
          bitPressed(inputs, HcdConfig::MCP_POT_BUTTON_BITS[index]),
          now,
          applyPotButtonChange,
          index);
    }
  }
  updateEncoders();
}

}  // namespace HcdControls
