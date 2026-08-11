/*
 * Minimal LVGL 9 adapter for ESP32_Display_Panel.
 * Based on the Apache-2.0 Waveshare ESP32-S3-Touch-LCD-7 example.
 */

#pragma once

#include <Arduino.h>
#include <esp_display_panel.hpp>
#include <lvgl.h>

namespace HcdLvglAdapter {

bool begin(
    esp_panel::drivers::LCD* lcd,
    esp_panel::drivers::Touch* touch,
    uint16_t width,
    uint16_t height);
void shutdown();
bool lock(int32_t timeoutMs = -1);
void unlock();
String diagnostics();

}  // namespace HcdLvglAdapter
