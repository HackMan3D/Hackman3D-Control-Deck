#include "HCD_Leds.h"

#include <Arduino.h>

#include "HCD_Config.h"

namespace {

bool pcConnected = false;
bool anyKeyPressed = false;
bool feedbackWasTriggered = false;
unsigned long feedbackStartedAt = 0;
uint16_t feedbackHoldMs = HcdConfig::DEFAULT_FEEDBACK_HOLD_MS;
uint8_t connectionDuty = 255;
uint8_t feedbackDuty = 255;

uint8_t gateLevel(bool on) {
  return (on == HcdConfig::MOSFET_GATE_ACTIVE_HIGH) ? HIGH : LOW;
}

void configureGate(uint8_t pin) {
  digitalWrite(pin, gateLevel(false));
  pinMode(pin, OUTPUT);
}

void writeGate(uint8_t pin, bool on) {
  digitalWrite(pin, gateLevel(on));
}

void writePwmGate(uint8_t pin, bool on, uint8_t duty, unsigned long phase) {
  if (!on || duty == 0) {
    writeGate(pin, false);
  } else if (duty == 255) {
    writeGate(pin, true);
  } else {
    const unsigned long onTime =
        (HcdConfig::LED_PWM_PERIOD_US * static_cast<unsigned long>(duty)) / 255UL;
    writeGate(pin, phase < onTime);
  }
}

void updateFeedbackGate() {
  const bool holdActive = feedbackWasTriggered && !anyKeyPressed &&
                          millis() - feedbackStartedAt < feedbackHoldMs;
  const unsigned long phase = micros() % HcdConfig::LED_PWM_PERIOD_US;
  writePwmGate(
      HcdConfig::CONNECTION_MOSFET_GATE_PIN,
      pcConnected,
      connectionDuty,
      phase);
  writePwmGate(
      HcdConfig::FEEDBACK_MOSFET_GATE_PIN,
      pcConnected && (anyKeyPressed || holdActive),
      feedbackDuty,
      phase);
}

}  // namespace

namespace HcdLeds {

void begin() {
  configureGate(HcdConfig::CONNECTION_MOSFET_GATE_PIN);
  configureGate(HcdConfig::FEEDBACK_MOSFET_GATE_PIN);
  setPcConnected(false);
  setAnyKeyPressed(false);
}

void update() { updateFeedbackGate(); }

void setPcConnected(bool connected) {
  pcConnected = connected;
  updateFeedbackGate();
}

void setAnyKeyPressed(bool pressed) {
  anyKeyPressed = pressed;
  if (pressed) {
    feedbackWasTriggered = true;
    feedbackStartedAt = millis();
  }
  updateFeedbackGate();
}

void setFeedbackHoldMs(uint16_t durationMs) {
  feedbackHoldMs = durationMs > HcdConfig::MAX_FEEDBACK_HOLD_MS
                       ? HcdConfig::MAX_FEEDBACK_HOLD_MS
                       : durationMs;
  updateFeedbackGate();
}

void setConnectionBrightness(uint8_t percentage) {
  connectionDuty = static_cast<uint8_t>(
      (static_cast<uint16_t>(min(percentage, static_cast<uint8_t>(100))) * 255U) /
      100U);
  updateFeedbackGate();
}

void setFeedbackBrightness(uint8_t percentage) {
  feedbackDuty = static_cast<uint8_t>(
      (static_cast<uint16_t>(min(percentage, static_cast<uint8_t>(100))) * 255U) /
      100U);
  updateFeedbackGate();
}

}  // namespace HcdLeds
