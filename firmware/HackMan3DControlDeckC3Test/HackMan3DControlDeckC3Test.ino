/*
 * HackMan3D Control Deck — ESP32-C3 nine-button hardware test.
 * Connect nine normally-open buttons between GPIO0/1/2/3/4/5/6/7/10 and GND.
 * Connect a red status LED to GPIO20 through a 220 ohm resistor, then to GND.
 * Connect GPIO21 to the gate of the MOSFET controlling the white feedback strip.
 */

#include <Arduino.h>
#include <string.h>

namespace {

constexpr char PRODUCT_NAME[] = "HackMan3D Control Deck C3 Test";
constexpr char MODEL_IDENTIFIER[] = "HCD-C3-TEST";
constexpr char FIRMWARE_VERSION[] = "0.4.0";
constexpr uint8_t BUTTON_COUNT = 9;
constexpr uint8_t BUTTON_PINS[BUTTON_COUNT] = {0, 1, 2, 3, 4, 5, 6, 7, 10};
constexpr uint8_t CONNECTION_LED_PIN = 20;
constexpr uint8_t FEEDBACK_STRIP_PIN = 21;
constexpr unsigned long DEBOUNCE_MS = 20;
constexpr unsigned long HEARTBEAT_TIMEOUT_MS = 3000;

bool rawPressed[BUTTON_COUNT] = {};
bool stablePressed[BUTTON_COUNT] = {};
bool pcConnected = false;
unsigned long changedAt[BUTTON_COUNT] = {};
unsigned long lastHeartbeatAt = 0;
char inputLine[64];
uint8_t inputLength = 0;

bool anyButtonPressed() {
  for (uint8_t index = 0; index < BUTTON_COUNT; ++index) {
    if (stablePressed[index]) {
      return true;
    }
  }
  return false;
}

void sendInfo() {
  Serial.print(F("HCD_INFO|"));
  Serial.print(PRODUCT_NAME);
  Serial.print('|');
  Serial.print(MODEL_IDENTIFIER);
  Serial.print('|');
  Serial.print(FIRMWARE_VERSION);
  Serial.print('|');
  Serial.println(BUTTON_COUNT);
}

void handleLine(const char* line) {
  if (strcmp(line, "HCD_PING") == 0) {
    lastHeartbeatAt = millis();
    pcConnected = true;
    digitalWrite(CONNECTION_LED_PIN, HIGH);
    digitalWrite(FEEDBACK_STRIP_PIN, anyButtonPressed() ? HIGH : LOW);
    Serial.println(F("HCD_PONG"));
  } else if (strcmp(line, "HCD_GET_INFO") == 0) {
    sendInfo();
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
    } else if (inputLength < sizeof(inputLine) - 1) {
      inputLine[inputLength++] = character;
    } else {
      inputLength = 0;
    }
  }
}

void updateButtons() {
  const unsigned long now = millis();
  for (uint8_t index = 0; index < BUTTON_COUNT; ++index) {
    const bool pressed = digitalRead(BUTTON_PINS[index]) == LOW;
    if (pressed != rawPressed[index]) {
      rawPressed[index] = pressed;
      changedAt[index] = now;
    }
    if (pressed != stablePressed[index] && now - changedAt[index] >= DEBOUNCE_MS) {
      stablePressed[index] = pressed;
      digitalWrite(
          FEEDBACK_STRIP_PIN,
          pcConnected && anyButtonPressed() ? HIGH : LOW);
      Serial.print(F("HCD_KEY|"));
      Serial.print(index + 1);
      Serial.print('|');
      Serial.println(pressed ? F("DOWN") : F("UP"));
    }
  }
}

}  // namespace

void setup() {
  const unsigned long now = millis();
  for (uint8_t index = 0; index < BUTTON_COUNT; ++index) {
    pinMode(BUTTON_PINS[index], INPUT_PULLUP);
    rawPressed[index] = digitalRead(BUTTON_PINS[index]) == LOW;
    stablePressed[index] = rawPressed[index];
    changedAt[index] = now;
  }
  pinMode(CONNECTION_LED_PIN, OUTPUT);
  pinMode(FEEDBACK_STRIP_PIN, OUTPUT);
  digitalWrite(CONNECTION_LED_PIN, LOW);
  digitalWrite(FEEDBACK_STRIP_PIN, LOW);
  Serial.begin(115200);
  Serial.print(F("HCD_READY|"));
  Serial.println(FIRMWARE_VERSION);
}

void loop() {
  readSerial();
  updateButtons();
  if (pcConnected && millis() - lastHeartbeatAt > HEARTBEAT_TIMEOUT_MS) {
    pcConnected = false;
    digitalWrite(CONNECTION_LED_PIN, LOW);
    digitalWrite(FEEDBACK_STRIP_PIN, LOW);
  }
}
