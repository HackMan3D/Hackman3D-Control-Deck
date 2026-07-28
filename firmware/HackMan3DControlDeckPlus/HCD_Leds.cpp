#include "HCD_Leds.h"

#include <Arduino.h>

#include "HCD_Config.h"

namespace {

bool pcConnected = false;
bool anyKeyPressed = false;
bool feedbackWasTriggered = false;
unsigned long feedbackStartedAt = 0;
uint16_t feedbackHoldMs = HcdConfig::DEFAULT_FEEDBACK_HOLD_MS;

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

void updateFeedbackGate() {
  const bool holdActive = feedbackWasTriggered && !anyKeyPressed &&
                          millis() - feedbackStartedAt < feedbackHoldMs;
  writeGate(
      HcdConfig::FEEDBACK_MOSFET_GATE_PIN,
      pcConnected && (anyKeyPressed || holdActive));
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
  writeGate(HcdConfig::CONNECTION_MOSFET_GATE_PIN, connected);
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

}  // namespace HcdLeds
