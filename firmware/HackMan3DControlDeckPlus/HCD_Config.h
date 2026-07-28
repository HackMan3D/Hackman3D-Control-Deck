#pragma once

#include <Arduino.h>

namespace HcdConfig {

constexpr char PRODUCT_NAME[] = "HackMan3D Control Deck Plus";
constexpr char MODEL_IDENTIFIER[] = "HCD-PLUS";
constexpr char FIRMWARE_VERSION[] = "1.0.0";
constexpr unsigned long SERIAL_BAUD_RATE = 115200;

constexpr uint8_t KEY_COUNT = 12;
constexpr uint8_t POTENTIOMETER_COUNT = 2;
constexpr uint8_t POT_BUTTON_COUNT = 2;

constexpr uint8_t MCP23017_ADDRESS = 0x20;
constexpr uint8_t MCP_KEY_BITS[KEY_COUNT] = {
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11,
};
constexpr uint8_t MCP_POT_BUTTON_BITS[POT_BUTTON_COUNT] = {12, 13};
constexpr uint8_t POTENTIOMETER_PINS[POTENTIOMETER_COUNT] = {A0, A1};

// Logic-level N-MOSFET gates. HIGH turns the corresponding light on.
constexpr uint8_t CONNECTION_MOSFET_GATE_PIN = 21;  // A3
constexpr uint8_t FEEDBACK_MOSFET_GATE_PIN = 1;     // TX
constexpr bool MOSFET_GATE_ACTIVE_HIGH = true;

constexpr unsigned long DEBOUNCE_MS = 20;
constexpr unsigned long POTENTIOMETER_REPORT_INTERVAL_MS = 20;
constexpr uint16_t POTENTIOMETER_CHANGE_THRESHOLD = 4;
constexpr unsigned long HEARTBEAT_TIMEOUT_MS = 3000;
constexpr uint16_t DEFAULT_FEEDBACK_HOLD_MS = 120;
constexpr uint16_t MAX_FEEDBACK_HOLD_MS = 2000;
constexpr uint8_t SERIAL_LINE_LENGTH = 96;

}  // namespace HcdConfig
