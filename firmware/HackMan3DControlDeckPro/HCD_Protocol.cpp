#include "HCD_Protocol.h"

#include <ctype.h>
#include <Preferences.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <mbedtls/base64.h>
#include <memory>
#include <new>

#include "HCD_Config.h"
#include "HCD_Display.h"
#include "HCD_FlashCache.h"
#include "HCD_LvglAdapter.h"
#include "HCD_Storage.h"
#include "HCD_Wifi.h"

namespace {

Preferences labelPreferences;
unsigned long lastHeartbeatAt = 0;
bool appConnected = false;
uint8_t pressedKeyCount = 0;
bool physicalLedsEnabled = false;
bool lastWifiState = false;
std::unique_ptr<uint8_t[]> iconUpload;
uint8_t iconUploadKey = 0;
size_t iconUploadExpected = 0;
size_t iconUploadReceived = 0;
uint32_t iconUploadSignature = 0;
unsigned long lastKeyEventSentAt = 0;
bool displaySyncActive = false;
unsigned long displaySyncStartedAt = 0;

struct PendingKeyEvent {
  uint8_t keyId;
  bool pressed;
};

QueueHandle_t keyEventQueue = nullptr;

void dispatchKeyEvent(const PendingKeyEvent& event) {
  if (!appConnected || event.keyId == 0 || event.keyId > HcdConfig::KEY_COUNT) {
    return;
  }
  if (event.pressed) {
    pressedKeyCount = min(static_cast<uint8_t>(HcdConfig::KEY_COUNT),
                          static_cast<uint8_t>(pressedKeyCount + 1));
  } else if (pressedKeyCount > 0) {
    --pressedKeyCount;
  }
  if (physicalLedsEnabled) {
    digitalWrite(HcdConfig::FEEDBACK_LED_PIN, pressedKeyCount > 0 ? HIGH : LOW);
  }
  HcdWifi::sendLine(
      "HCD_KEY|" + String(event.keyId) + (event.pressed ? "|DOWN" : "|UP"));
}

void loadAppearance() {
  const uint8_t iconSize = labelPreferences.getUChar("iconSize", 1);
  const uint8_t theme = labelPreferences.getUChar("theme", 1);
  const bool secondFader = labelPreferences.getBool("secondFader", false);
  const uint8_t sliderMode = labelPreferences.getUChar("sliderMode", 1);
  HcdDisplay::setAppearance(iconSize, false, theme, secondFader, sliderMode);
}

void updateAppearance(const String& line) {
  constexpr char prefix[] = "HCD_PRO_DISPLAY|";
  const int sizeSeparator = line.indexOf('|', sizeof(prefix) - 1);
  const int labelSeparator = sizeSeparator < 0 ? -1 : line.indexOf('|', sizeSeparator + 1);
  if (sizeSeparator < 0 || labelSeparator < 0) {
    return;
  }
  const uint8_t iconSize = constrain(
      line.substring(sizeof(prefix) - 1, sizeSeparator).toInt(), 0, 3);
  const int faderSeparator = line.indexOf('|', labelSeparator + 1);
  const uint8_t theme = constrain(
      line.substring(
          labelSeparator + 1,
          faderSeparator < 0 ? line.length() : faderSeparator).toInt(),
      0,
      2);
  const int modeSeparator = faderSeparator < 0 ? -1 : line.indexOf('|', faderSeparator + 1);
  const bool secondFader = faderSeparator >= 0
      ? line.substring(
          faderSeparator + 1,
          modeSeparator < 0 ? line.length() : modeSeparator).toInt() != 0
      : labelPreferences.getBool("secondFader", false);
  const uint8_t sliderMode = modeSeparator >= 0
      ? constrain(line.substring(modeSeparator + 1).toInt(), 0, 2)
      : labelPreferences.getUChar("sliderMode", 1);
  // The desktop app is the source of truth and sends these settings after
  // every connection. Avoid writing flash here: cache suspension during NVS
  // writes can starve the ESP32-S3 RGB DMA and visibly shift the screen.
  HcdDisplay::setAppearance(iconSize, false, theme, secondFader, sliderMode);
}

void updateColors(const String& line) {
  constexpr char prefix[] = "HCD_PRO_COLORS|";
  uint32_t colors[5] = {};
  int start = sizeof(prefix) - 1;
  for (uint8_t index = 0; index < 5; ++index) {
    const int separator = index == 4 ? line.length() : line.indexOf('|', start);
    if (separator < 0) {
      return;
    }
    const String value = line.substring(start, separator);
    if (value.length() != 6) {
      return;
    }
    for (uint8_t character = 0; character < 6; ++character) {
      if (!isxdigit(static_cast<unsigned char>(value[character]))) {
        return;
      }
    }
    colors[index] = strtoul(value.c_str(), nullptr, 16);
    start = separator + 1;
  }
  HcdDisplay::setColors(colors[0], colors[1], colors[2], colors[3], colors[4]);
}

String decodeBase64(const String& value) {
  size_t outputLength = 0;
  const size_t capacity = value.length() * 3 / 4 + 4;
  std::unique_ptr<unsigned char[]> output(new unsigned char[capacity + 1]);
  const int result = mbedtls_base64_decode(
      output.get(),
      capacity,
      &outputLength,
      reinterpret_cast<const unsigned char*>(value.c_str()),
      value.length());
  if (result != 0) {
    return String();
  }
  output[outputLength] = '\0';
  return String(reinterpret_cast<char*>(output.get()));
}

size_t decodeBase64Bytes(const String& value, uint8_t* output, size_t capacity) {
  size_t outputLength = 0;
  const int result = mbedtls_base64_decode(
      output,
      capacity,
      &outputLength,
      reinterpret_cast<const unsigned char*>(value.c_str()),
      value.length());
  return result == 0 ? outputLength : 0;
}

void setAppConnected(bool connected) {
  if (connected == appConnected) {
    return;
  }
  appConnected = connected;
  if (physicalLedsEnabled) {
    digitalWrite(HcdConfig::CONNECTION_LED_PIN, connected ? HIGH : LOW);
  }
  if (!connected) {
    pressedKeyCount = 0;
    if (physicalLedsEnabled) {
      digitalWrite(HcdConfig::FEEDBACK_LED_PIN, LOW);
    }
    if (displaySyncActive) {
      displaySyncActive = false;
      HcdDisplay::finishDisplaySync();
    }
  }
  HcdDisplay::setAppConnected(connected);
}

void sendInfo(Print& reply) {
  reply.print(F("HCD_INFO|"));
  reply.print(HcdConfig::PRODUCT_NAME);
  reply.print('|');
  reply.print(HcdConfig::MODEL_IDENTIFIER);
  reply.print('|');
  reply.print(HcdConfig::FIRMWARE_VERSION);
  reply.print('|');
  reply.print(HcdConfig::KEY_COUNT);
  reply.print('|');
  reply.print(HcdConfig::POTENTIOMETER_COUNT);
  reply.print('|');
  for (uint8_t keyId = 1; keyId <= HcdConfig::KEY_COUNT; ++keyId) {
    if (keyId > 1) {
      reply.print(',');
    }
    char signature[9];
    snprintf(
        signature,
        sizeof(signature),
        "%08lx",
        static_cast<unsigned long>(HcdFlashCache::iconSignature(keyId)));
    reply.print(signature);
  }
  reply.println();
}

void updateLabel(const String& line) {
  constexpr char prefix[] = "HCD_PRO_LABEL|";
  const int separator = line.indexOf('|', sizeof(prefix) - 1);
  if (separator < 0) {
    return;
  }
  const uint8_t keyId = static_cast<uint8_t>(
      line.substring(sizeof(prefix) - 1, separator).toInt());
  if (keyId == 0 || keyId > HcdConfig::KEY_COUNT) {
    return;
  }
  const String label = decodeBase64(line.substring(separator + 1));
  if (label.isEmpty()) {
    return;
  }
  HcdDisplay::setKeyLabel(keyId, label);
}

void beginIconUpload(const String& line) {
  constexpr char prefix[] = "HCD_PRO_ICON_BEGIN|";
  const int keySeparator = line.indexOf('|', sizeof(prefix) - 1);
  const int sizeSeparator = keySeparator < 0 ? -1 : line.indexOf('|', keySeparator + 1);
  if (keySeparator < 0 || sizeSeparator < 0) {
    return;
  }
  const uint8_t keyId = static_cast<uint8_t>(
      line.substring(sizeof(prefix) - 1, keySeparator).toInt());
  const size_t expected = static_cast<size_t>(
      line.substring(keySeparator + 1, sizeSeparator).toInt());
  if (keyId == 0 || keyId > HcdConfig::KEY_COUNT || expected != HcdConfig::ICON_DATA_SIZE) {
    return;
  }

  iconUpload.reset(new (std::nothrow) uint8_t[expected]);
  iconUploadKey = keyId;
  iconUploadExpected = expected;
  iconUploadReceived = 0;
  iconUploadSignature = strtoul(line.substring(sizeSeparator + 1).c_str(), nullptr, 16);
  if (!iconUpload) {
    iconUploadKey = 0;
    iconUploadExpected = 0;
    iconUploadSignature = 0;
  }
}

void appendIconChunk(const String& line) {
  constexpr char prefix[] = "HCD_PRO_ICON_CHUNK|";
  if (iconUploadKey == 0 || !iconUpload) {
    return;
  }
  const size_t decodedSize = decodeBase64Bytes(
      line.substring(sizeof(prefix) - 1),
      iconUpload.get() + iconUploadReceived,
      iconUploadExpected - iconUploadReceived);
  if (decodedSize == 0 || iconUploadReceived + decodedSize > iconUploadExpected) {
    return;
  }
  iconUploadReceived += decodedSize;
}

void finishIconUpload(const String& line) {
  constexpr char prefix[] = "HCD_PRO_ICON_END|";
  const uint8_t keyId = static_cast<uint8_t>(line.substring(sizeof(prefix) - 1).toInt());
  if (keyId == 0 || keyId != iconUploadKey) {
    return;
  }
  if (iconUpload && iconUploadReceived == iconUploadExpected) {
    HcdDisplay::setKeyIcon(keyId, iconUpload.get(), iconUploadExpected);
  }
  iconUpload.reset();
  iconUploadKey = 0;
  iconUploadExpected = 0;
  iconUploadReceived = 0;
  iconUploadSignature = 0;
}

void clearIcon(const String& line) {
  constexpr char prefix[] = "HCD_PRO_ICON_CLEAR|";
  const uint8_t keyId = static_cast<uint8_t>(line.substring(sizeof(prefix) - 1).toInt());
  if (keyId == 0 || keyId > HcdConfig::KEY_COUNT) {
    return;
  }
  HcdDisplay::setKeyIcon(keyId, nullptr, 0);
}

void sendStorageInfo(Print& reply) {
  reply.print(F("HCD_STORAGE|"));
  reply.print(HcdStorage::status());
  reply.print('|');
  reply.print(static_cast<unsigned long long>(HcdStorage::capacityBytes()));
  reply.print('|');
  reply.println(static_cast<unsigned long long>(HcdStorage::usedBytes()));
}

void loadCachedIcons() {
  if (!HcdStorage::isReady()) {
    return;
  }
  std::unique_ptr<uint8_t[]> data(new (std::nothrow) uint8_t[HcdConfig::ICON_DATA_SIZE]);
  if (!data) {
    return;
  }
  for (uint8_t keyId = 1; keyId <= HcdConfig::KEY_COUNT; ++keyId) {
    if (HcdStorage::loadIcon(keyId, data.get(), HcdConfig::ICON_DATA_SIZE)) {
      HcdDisplay::setKeyIcon(keyId, data.get(), HcdConfig::ICON_DATA_SIZE);
    }
  }
}

void handleCommand(const String& line, Print& reply) {
  if (&reply == &Serial || &reply == &Serial0) {
    return;
  }
  if (line == "HCD_PING") {
    lastHeartbeatAt = millis();
    setAppConnected(true);
    reply.println(F("HCD_PONG"));
    return;
  }
  if (line == "HCD_GET_INFO") {
    sendInfo(reply);
    return;
  }
  if (line == "HCD_GET_DISPLAY_DIAG") {
    reply.print(F("HCD_DISPLAY_DIAG|"));
    reply.println(HcdLvglAdapter::diagnostics());
    return;
  }
  if (line == "HCD_GET_STORAGE") {
    sendStorageInfo(reply);
    return;
  }
  if (line == "HCD_PRO_SYNC_BEGIN") {
    displaySyncActive = true;
    displaySyncStartedAt = millis();
    HcdDisplay::showDisplaySync();
  } else if (line == "HCD_PRO_SYNC_END") {
    displaySyncActive = false;
    HcdDisplay::finishDisplaySync();
  } else if (line.startsWith("HCD_PRO_ICON_BEGIN|")) {
    beginIconUpload(line);
  } else if (line.startsWith("HCD_PRO_ICON_CHUNK|")) {
    appendIconChunk(line);
  } else if (line.startsWith("HCD_PRO_ICON_END|")) {
    finishIconUpload(line);
  } else if (line.startsWith("HCD_PRO_ICON_CLEAR|")) {
    clearIcon(line);
  } else if (line == "HCD_PRO_CACHE_COMMIT" && HcdFlashCache::hasPendingChanges()) {
    HcdDisplay::beginFirmwareWrite();
    HcdFlashCache::commit();
    HcdDisplay::prepareForRestart();
    ESP.restart();
  } else if (line == "HCD_PRO_REFRESH") {
    HcdDisplay::refresh();
  } else if (line.startsWith("HCD_PRO_DISPLAY|")) {
    updateAppearance(line);
  } else if (line.startsWith("HCD_PRO_COLORS|")) {
    updateColors(line);
  } else if (line.startsWith("HCD_PRO_SLIDER_STATE|")) {
    const int separator = line.indexOf('|', 21);
    const uint8_t sliderId = separator < 0
        ? 1
        : static_cast<uint8_t>(constrain(line.substring(21, separator).toInt(), 1, 2));
    const int valueStart = separator < 0 ? 21 : separator + 1;
    HcdDisplay::setSliderValue(
        sliderId,
        static_cast<uint16_t>(constrain(line.substring(valueStart).toInt(), 0, 1023)));
  }
}

void loadLabels() {
  for (uint8_t keyId = 1; keyId <= HcdConfig::KEY_COUNT; ++keyId) {
    char preferenceKey[8];
    snprintf(preferenceKey, sizeof(preferenceKey), "key%u", keyId);
    const String label = labelPreferences.getString(
        preferenceKey,
        "Key " + String(keyId));
    HcdDisplay::setKeyLabel(keyId, label);
  }
}

}  // namespace

namespace HcdProtocol {

void begin() {
  keyEventQueue = xQueueCreate(48, sizeof(PendingKeyEvent));
  labelPreferences.begin("hcd_labels", false);
  loadAppearance();
  HcdWifi::begin();
  physicalLedsEnabled = HcdWifi::hasSavedCredentials();
  if (physicalLedsEnabled) {
    Serial0.end();
    pinMode(HcdConfig::CONNECTION_LED_PIN, OUTPUT);
    pinMode(HcdConfig::FEEDBACK_LED_PIN, OUTPUT);
    digitalWrite(HcdConfig::CONNECTION_LED_PIN, LOW);
    digitalWrite(HcdConfig::FEEDBACK_LED_PIN, LOW);
  }
  lastWifiState = HcdWifi::isConnected();
  HcdDisplay::setWifiStatus(
      lastWifiState, HcdWifi::hasSavedCredentials(), HcdWifi::localAddress());
}

void update() {
  HcdWifi::update(handleCommand);
  // Network writes never run inside LVGL's drawing task. Drain a small number
  // at a time so a burst of taps cannot starve the RGB display DMA.
  if (keyEventQueue != nullptr &&
      millis() - lastKeyEventSentAt >= HcdConfig::KEY_EVENT_SEND_INTERVAL_MS) {
    PendingKeyEvent event = {};
    if (xQueueReceive(keyEventQueue, &event, 0) == pdTRUE) {
      lastKeyEventSentAt = millis();
      dispatchKeyEvent(event);
    }
  }
  const bool wifiState = HcdWifi::isConnected();
  if (wifiState != lastWifiState) {
    lastWifiState = wifiState;
    HcdDisplay::setWifiStatus(
        wifiState, HcdWifi::hasSavedCredentials(), HcdWifi::localAddress());
  }
  if (appConnected && millis() - lastHeartbeatAt > HcdConfig::HEARTBEAT_TIMEOUT_MS) {
    setAppConnected(false);
  }
  if (
      displaySyncActive &&
      millis() - displaySyncStartedAt > HcdConfig::DISPLAY_SYNC_TIMEOUT_MS) {
    displaySyncActive = false;
    HcdDisplay::finishDisplaySync();
  }
}

void sendKeyEvent(uint8_t keyId, bool pressed) {
  if (!appConnected || keyId == 0 || keyId > HcdConfig::KEY_COUNT) {
    return;
  }
  const PendingKeyEvent event = {keyId, pressed};
  if (keyEventQueue != nullptr && xQueueSend(keyEventQueue, &event, 0) != pdTRUE) {
    // Preserve release events even after an exceptional burst so the desktop
    // never keeps a long-press action stuck down.
    PendingKeyEvent discarded = {};
    xQueueReceive(keyEventQueue, &discarded, 0);
    xQueueSend(keyEventQueue, &event, 0);
  }
}

void sendSliderEvent(uint8_t sliderId, uint16_t value) {
  if (!appConnected) {
    return;
  }
  HcdWifi::sendLine(
      "HCD_SLIDER|" + String(sliderId) + "|" +
      String(min(value, static_cast<uint16_t>(1023))));
}

}  // namespace HcdProtocol
