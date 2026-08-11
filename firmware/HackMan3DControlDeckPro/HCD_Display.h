#pragma once

#include <Arduino.h>

namespace HcdDisplay {

using KeyEventCallback = void (*)(uint8_t keyId, bool pressed);
using SliderEventCallback = void (*)(uint8_t sliderId, uint16_t value);

bool begin(KeyEventCallback callback, SliderEventCallback sliderCallback);
void setAppConnected(bool connected);
void setWifiStatus(bool connected, bool configured, const IPAddress& address);
void setKeyLabel(uint8_t keyId, const String& label);
void setKeyIcon(uint8_t keyId, const uint8_t* data, size_t size);
void refresh();
void setAppearance(
    uint8_t iconSize,
    bool showLabels,
    uint8_t theme,
    bool secondFader,
    uint8_t sliderMode);
void setSliderValue(uint8_t sliderId, uint16_t value);
void showFirmwareUpdate();
void beginFirmwareWrite();
void prepareForRestart();
bool selectSdCard(bool selected);

}  // namespace HcdDisplay
