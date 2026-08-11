#include "HCD_Protocol.h"

#include <Arduino.h>
#include <stdlib.h>
#include <string.h>

#include "HCD_Config.h"
#include "HCD_Leds.h"

namespace {

char inputLine[HcdConfig::SERIAL_LINE_LENGTH];
uint8_t inputLength = 0;
unsigned long lastHeartbeatAt = 0;
bool pcConnected = false;

void setConnected(bool connected) {
  if (pcConnected == connected) {
    return;
  }
  pcConnected = connected;
  HcdLeds::setPcConnected(connected);
}

void sendInfo() {
  Serial.print(F("HCD_INFO|"));
  Serial.print(HcdConfig::PRODUCT_NAME);
  Serial.print('|');
  Serial.print(HcdConfig::MODEL_IDENTIFIER);
  Serial.print('|');
  Serial.print(HcdConfig::FIRMWARE_VERSION);
  Serial.print('|');
  Serial.print(HcdConfig::KEY_COUNT);
  Serial.print('|');
  Serial.println(HcdConfig::POTENTIOMETER_COUNT);
}

void handleLine(const char* line) {
  if (strcmp(line, "HCD_PING") == 0) {
    lastHeartbeatAt = millis();
    setConnected(true);
    Serial.println(F("HCD_PONG"));
    return;
  }
  if (strcmp(line, "HCD_GET_INFO") == 0) {
    sendInfo();
    return;
  }

  constexpr char LED_HOLD_PREFIX[] = "HCD_SET_LED_HOLD|";
  if (strncmp(line, LED_HOLD_PREFIX, sizeof(LED_HOLD_PREFIX) - 1) == 0) {
    const unsigned long requested = strtoul(
        line + sizeof(LED_HOLD_PREFIX) - 1, nullptr, 10);
    const uint16_t duration = requested > HcdConfig::MAX_FEEDBACK_HOLD_MS
                                  ? HcdConfig::MAX_FEEDBACK_HOLD_MS
                                  : static_cast<uint16_t>(requested);
    HcdLeds::setFeedbackHoldMs(duration);
    Serial.print(F("HCD_LED_HOLD|"));
    Serial.println(duration);
  }
}

void readSerial() {
  while (Serial.available() > 0) {
    const char character = static_cast<char>(Serial.read());
    if (character == '\r') {
      continue;
    }
    if (character == '\n') {
      inputLine[inputLength] = '\0';
      if (inputLength > 0) {
        handleLine(inputLine);
      }
      inputLength = 0;
      continue;
    }
    if (inputLength < HcdConfig::SERIAL_LINE_LENGTH - 1) {
      inputLine[inputLength++] = character;
    } else {
      inputLength = 0;
    }
  }
}

}  // namespace

namespace HcdProtocol {

void begin() {
  Serial.begin(HcdConfig::SERIAL_BAUD_RATE);
  Serial.print(F("HCD_READY|"));
  Serial.println(HcdConfig::FIRMWARE_VERSION);
}

void update() {
  readSerial();
  if (pcConnected &&
      millis() - lastHeartbeatAt > HcdConfig::HEARTBEAT_TIMEOUT_MS) {
    setConnected(false);
  }
}

void sendKeyEvent(uint8_t keyId, bool pressed) {
  Serial.print(F("HCD_KEY|"));
  Serial.print(keyId);
  Serial.print('|');
  Serial.println(pressed ? F("DOWN") : F("UP"));
}

void sendPotButtonEvent(uint8_t potentiometerId, bool pressed) {
  Serial.print(F("HCD_POT_BUTTON|"));
  Serial.print(potentiometerId);
  Serial.print('|');
  Serial.println(pressed ? F("DOWN") : F("UP"));
}

void sendEncoderEvent(uint8_t encoderId, bool clockwise) {
  Serial.print(F("HCD_ENCODER|"));
  Serial.print(encoderId);
  Serial.print('|');
  Serial.println(clockwise ? F("RIGHT") : F("LEFT"));
}

}  // namespace HcdProtocol
