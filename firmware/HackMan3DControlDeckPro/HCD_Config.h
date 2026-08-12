#pragma once

#include <Arduino.h>

namespace HcdConfig {

constexpr char PRODUCT_NAME[] = "HackMan3D Control Deck Pro";
constexpr char MODEL_IDENTIFIER[] = "HCD-PRO";
constexpr char FIRMWARE_VERSION[] = "1.2.45";

constexpr uint16_t DISPLAY_WIDTH = 800;
constexpr uint16_t DISPLAY_HEIGHT = 480;
constexpr uint8_t KEY_COUNT = 28;
constexpr uint8_t POTENTIOMETER_COUNT = 0;
constexpr uint8_t ICON_WIDTH = 64;
constexpr uint8_t ICON_HEIGHT = 64;
constexpr size_t ICON_DATA_SIZE = ICON_WIDTH * ICON_HEIGHT * 2;
constexpr uint8_t CONNECTION_LED_PIN = 43;
constexpr uint8_t FEEDBACK_LED_PIN = 44;

constexpr uint16_t DISCOVERY_PORT = 42100;
constexpr uint16_t TCP_PORT = 42101;
constexpr uint16_t OTA_PORT = 42102;
constexpr unsigned long HEARTBEAT_TIMEOUT_MS = 3200;
constexpr unsigned long DISPLAY_SYNC_TIMEOUT_MS = 60000;
constexpr size_t LINE_LENGTH = 512;
constexpr unsigned long SLIDER_REFRESH_INTERVAL_MS = 32;
constexpr unsigned long SLIDER_SEND_INTERVAL_MS = 100;
constexpr unsigned long KEY_EVENT_SEND_INTERVAL_MS = 12;

}  // namespace HcdConfig
