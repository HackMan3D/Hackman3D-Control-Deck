#pragma once

#include <Arduino.h>

namespace HcdConfig {

constexpr char PRODUCT_NAME[] = "HackMan3D Control Deck";
constexpr char MODEL_IDENTIFIER[] = "HCD-BASE";
constexpr char FIRMWARE_VERSION[] = "1.7.1";
constexpr unsigned long SERIAL_BAUD_RATE = 115200;

constexpr uint8_t KEY_COUNT = 9;

// The front panel is numbered left-to-right, while each physical row is
// wired right-to-left. Keep the logical events aligned with the 3x3 UI.
constexpr uint8_t KEY_PINS[KEY_COUNT] = {4, 3, 2, 7, 6, 5, 10, 9, 8};

// Logic-level N-MOSFET gates. HIGH turns the corresponding light on.
constexpr uint8_t CONNECTION_MOSFET_GATE_PIN = 21;  // A3
constexpr uint8_t FEEDBACK_MOSFET_GATE_PIN = 1;     // TX
constexpr bool MOSFET_GATE_ACTIVE_HIGH = true;
constexpr unsigned long LED_PWM_PERIOD_US = 2000;

constexpr unsigned long DEBOUNCE_MS = 20;
constexpr unsigned long HEARTBEAT_TIMEOUT_MS = 3000;
constexpr uint16_t DEFAULT_FEEDBACK_HOLD_MS = 120;
constexpr uint16_t MAX_FEEDBACK_HOLD_MS = 2000;
constexpr uint8_t SERIAL_LINE_LENGTH = 80;

}  // namespace HcdConfig
