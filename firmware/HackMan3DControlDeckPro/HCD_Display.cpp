#include "HCD_Display.h"

#include <esp_display_panel.hpp>
#include <esp_heap_caps.h>
#include <lvgl.h>

#include "HCD_Config.h"
#include "HCD_LvglAdapter.h"

using namespace esp_panel::board;
using namespace esp_panel::drivers;

namespace {

Board* board = nullptr;
lv_obj_t* keyButtons[HcdConfig::KEY_COUNT] = {};
lv_obj_t* keyLabels[HcdConfig::KEY_COUNT] = {};
lv_obj_t* keyImages[HcdConfig::KEY_COUNT] = {};
lv_image_dsc_t keyImageDescriptors[HcdConfig::KEY_COUNT] = {};
uint8_t* keyImageData[HcdConfig::KEY_COUNT] = {};
lv_obj_t* connectionDot = nullptr;
lv_obj_t* networkLabel = nullptr;
lv_obj_t* keybed = nullptr;
lv_obj_t* levelSlider = nullptr;
lv_obj_t* sliderTouchArea = nullptr;
lv_obj_t* volumeHighIcon = nullptr;
lv_obj_t* volumeMuteIcon = nullptr;
lv_obj_t* microphoneSlider = nullptr;
lv_obj_t* microphoneTouchArea = nullptr;
lv_obj_t* microphoneHighIcon = nullptr;
lv_obj_t* microphoneMuteIcon = nullptr;
lv_obj_t* firmwareOverlay = nullptr;
HcdDisplay::KeyEventCallback keyEventCallback = nullptr;
HcdDisplay::SliderEventCallback sliderEventCallback = nullptr;
uint8_t currentIconSize = 1;
bool labelsVisible = false;
uint8_t currentTheme = 1;
uint16_t displayedSliderValue = 512;
uint16_t displayedMicrophoneValue = 512;
unsigned long lastSliderRefreshAt = 0;
unsigned long lastMicrophoneRefreshAt = 0;
unsigned long lastSliderSendAt = 0;
unsigned long lastMicrophoneSendAt = 0;
bool secondFaderVisible = false;
uint8_t currentSliderMode = 1;

// The largest 64 px icon remains inside a 96 px key with a visible margin.
constexpr uint16_t iconScales[] = {192, 256, 320, 344};
constexpr uint16_t labelledIconScales[] = {152, 184, 208, 224};

uint16_t currentImageScale() {
  return labelsVisible
      ? labelledIconScales[currentIconSize]
      : iconScales[currentIconSize];
}

void positionKeyContent(uint8_t index) {
  const bool hasIcon = !lv_obj_has_flag(keyImages[index], LV_OBJ_FLAG_HIDDEN);
  if (labelsVisible) {
    lv_obj_clear_flag(keyLabels[index], LV_OBJ_FLAG_HIDDEN);
    if (hasIcon) {
      lv_obj_align(keyImages[index], LV_ALIGN_TOP_MID, 0, 2);
      lv_obj_align(keyLabels[index], LV_ALIGN_BOTTOM_MID, 0, -2);
    } else {
      lv_obj_center(keyLabels[index]);
    }
  } else {
    lv_obj_add_flag(keyLabels[index], LV_OBJ_FLAG_HIDDEN);
    if (hasIcon) {
      lv_obj_center(keyImages[index]);
    }
  }
}

void applyTheme() {
  const uint32_t screenColor = currentTheme == 2 ? 0x000000 : 0x080808;
  const uint32_t bedColor = currentTheme == 0 ? 0x080808 : 0x111111;
  const uint32_t buttonColor = currentTheme == 2 ? 0x050505 :
      (currentTheme == 1 ? 0x202020 : 0x171717);
  const uint32_t borderColor = currentTheme == 2 ? 0x505050 :
      (currentTheme == 1 ? 0x404040 : 0x333333);
  lv_obj_t* screen = lv_screen_active();
  lv_obj_set_style_bg_color(screen, lv_color_hex(screenColor), 0);
  if (keybed != nullptr) {
    lv_obj_set_style_bg_color(keybed, lv_color_hex(bedColor), 0);
    lv_obj_set_style_border_color(
        keybed, lv_color_hex(currentTheme == 1 ? 0x303030 : bedColor), 0);
    lv_obj_set_style_shadow_width(keybed, currentTheme == 1 ? 14 : 0, 0);
  }
  for (uint8_t index = 0; index < HcdConfig::KEY_COUNT; ++index) {
    lv_obj_set_style_bg_color(keyButtons[index], lv_color_hex(buttonColor), 0);
    lv_obj_set_style_border_color(keyButtons[index], lv_color_hex(borderColor), 0);
    lv_obj_set_style_border_width(keyButtons[index], 1, 0);
    lv_obj_set_style_shadow_width(keyButtons[index], currentTheme == 1 ? 8 : 0, 0);
    lv_obj_set_style_shadow_color(keyButtons[index], lv_color_hex(0x000000), 0);
    lv_obj_set_style_shadow_offset_y(keyButtons[index], currentTheme == 1 ? 4 : 0, 0);
  }
}

void keyEvent(lv_event_t* event) {
  if (keyEventCallback == nullptr) {
    return;
  }
  const uintptr_t value = reinterpret_cast<uintptr_t>(lv_event_get_user_data(event));
  const uint8_t keyId = static_cast<uint8_t>(value);
  const lv_event_code_t code = lv_event_get_code(event);
  if (code == LV_EVENT_PRESSED) {
    keyEventCallback(keyId, true);
  } else if (code == LV_EVENT_RELEASED || code == LV_EVENT_PRESS_LOST) {
    keyEventCallback(keyId, false);
  }
}

void updateSliderFromTouch(uint8_t sliderId, bool force) {
  lv_indev_t* input = lv_indev_active();
  lv_obj_t* slider = sliderId == 2 ? microphoneSlider : levelSlider;
  uint16_t& displayedValue = sliderId == 2
      ? displayedMicrophoneValue
      : displayedSliderValue;
  unsigned long& lastRefreshAt = sliderId == 2
      ? lastMicrophoneRefreshAt
      : lastSliderRefreshAt;
  unsigned long& lastSendAt = sliderId == 2
      ? lastMicrophoneSendAt
      : lastSliderSendAt;
  if (input == nullptr || slider == nullptr) {
    return;
  }
  const unsigned long now = millis();
  if (!force && now - lastRefreshAt < HcdConfig::SLIDER_REFRESH_INTERVAL_MS) {
    return;
  }
  lv_point_t point = {};
  lv_indev_get_point(input, &point);
  const int32_t top = lv_obj_get_y(slider);
  int32_t height = lv_obj_get_height(slider) - 1;
  if (height < 1) {
    height = 1;
  }
  const int32_t distanceFromBottom = constrain(top + height - point.y, 0L, height);
  const uint16_t value = static_cast<uint16_t>(distanceFromBottom * 1023 / height);
  if (!force && abs(static_cast<int>(value) - static_cast<int>(displayedValue)) < 4) {
    return;
  }
  displayedValue = value;
  lastRefreshAt = now;
  lv_slider_set_value(slider, value, LV_ANIM_OFF);
  if (sliderEventCallback != nullptr &&
      (force || now - lastSendAt >= HcdConfig::SLIDER_SEND_INTERVAL_MS)) {
    lastSendAt = now;
    sliderEventCallback(sliderId, value);
  }
}

void sliderTouchEvent(lv_event_t* event) {
  const lv_event_code_t code = lv_event_get_code(event);
  const uint8_t sliderId = static_cast<uint8_t>(
      reinterpret_cast<uintptr_t>(lv_event_get_user_data(event)));
  if (code == LV_EVENT_PRESSED || code == LV_EVENT_RELEASED || code == LV_EVENT_PRESS_LOST) {
    updateSliderFromTouch(sliderId, true);
  } else if (code == LV_EVENT_PRESSING) {
    updateSliderFromTouch(sliderId, false);
  }
}

void styleFader(lv_obj_t* slider) {
  lv_obj_set_style_bg_color(slider, lv_color_hex(0x555555), LV_PART_MAIN);
  lv_obj_set_style_bg_opa(slider, LV_OPA_COVER, LV_PART_MAIN);
  lv_obj_set_style_border_width(slider, 0, LV_PART_MAIN);
  lv_obj_set_style_radius(slider, 2, LV_PART_MAIN);
  lv_obj_set_style_bg_opa(slider, LV_OPA_TRANSP, LV_PART_INDICATOR);
  lv_obj_set_style_pad_left(slider, 20, LV_PART_KNOB);
  lv_obj_set_style_pad_right(slider, 20, LV_PART_KNOB);
  lv_obj_set_style_pad_top(slider, 10, LV_PART_KNOB);
  lv_obj_set_style_pad_bottom(slider, 10, LV_PART_KNOB);
  lv_obj_set_style_radius(slider, 8, LV_PART_KNOB);
  lv_obj_set_style_bg_color(slider, lv_color_hex(0xE8E8E8), LV_PART_KNOB);
  lv_obj_set_style_border_color(slider, lv_color_hex(0xFFFFFF), LV_PART_KNOB);
  lv_obj_set_style_border_width(slider, 2, LV_PART_KNOB);
  lv_obj_clear_flag(slider, LV_OBJ_FLAG_CLICKABLE);
}

void buildInterface() {
  lv_obj_t* screen = lv_screen_active();
  lv_obj_set_style_bg_color(screen, lv_color_hex(0x080808), 0);
  lv_obj_set_style_bg_opa(screen, LV_OPA_COVER, 0);

  lv_obj_t* title = lv_label_create(screen);
  lv_label_set_text(title, "HackMan3D  CONTROL DECK PRO");
  lv_obj_set_style_text_color(title, lv_color_hex(0xFFFFFF), 0);
  lv_obj_align(title, LV_ALIGN_TOP_LEFT, 18, 14);

  connectionDot = lv_obj_create(screen);
  lv_obj_set_size(connectionDot, 18, 18);
  lv_obj_set_style_radius(connectionDot, LV_RADIUS_CIRCLE, 0);
  lv_obj_set_style_border_width(connectionDot, 0, 0);
  lv_obj_set_style_bg_color(connectionDot, lv_color_hex(0x3A3A3A), 0);
  lv_obj_align(connectionDot, LV_ALIGN_TOP_RIGHT, -18, 13);

  networkLabel = lv_label_create(screen);
  lv_label_set_text(networkLabel, "Wi-Fi starting…");
  lv_obj_set_style_text_color(networkLabel, lv_color_hex(0xA0A0A0), 0);
  lv_obj_align(networkLabel, LV_ALIGN_TOP_RIGHT, -48, 16);

  constexpr int columns = 7;
  constexpr int rows = 4;
  constexpr int marginX = 12;
  constexpr int top = 54;
  // Match the visible inset at the top of the keybed. The former 12 px value
  // placed the last row directly over the keybed's lower border.
  constexpr int bottom = 20;
  constexpr int gap = 6;
  constexpr int faderWidth = 58;
  constexpr int faderGap = 10;
  constexpr int sliderRailWidth = 4;
  constexpr int sliderIconSpace = 28;
  constexpr int gridRight = HcdConfig::DISPLAY_WIDTH - marginX - faderWidth - faderGap;
  constexpr int buttonWidth =
      (gridRight - marginX - gap * (columns - 1)) / columns;
  constexpr int buttonHeight =
      (HcdConfig::DISPLAY_HEIGHT - top - bottom - gap * (rows - 1)) / rows;

  keybed = lv_obj_create(screen);
  lv_obj_set_pos(keybed, 7, top - 8);
  lv_obj_set_size(keybed, HcdConfig::DISPLAY_WIDTH - 14, HcdConfig::DISPLAY_HEIGHT - top - 2);
  lv_obj_set_style_radius(keybed, 20, 0);
  lv_obj_set_style_border_width(keybed, 2, 0);
  lv_obj_clear_flag(keybed, LV_OBJ_FLAG_SCROLLABLE);

  for (uint8_t index = 0; index < HcdConfig::KEY_COUNT; ++index) {
    const int row = index / columns;
    const int column = index % columns;
    // A plain object has no button-theme press transform or transition. It is
    // still clickable, but rapid taps cannot trigger animated repaint storms.
    lv_obj_t* button = lv_obj_create(screen);
    keyButtons[index] = button;
    lv_obj_add_flag(button, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_clear_flag(button, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_pos(
        button,
        marginX + column * (buttonWidth + gap),
        top + row * (buttonHeight + gap));
    lv_obj_set_size(button, buttonWidth, buttonHeight);
    lv_obj_set_style_radius(button, 10, 0);
    lv_obj_set_style_clip_corner(button, true, 0);
    lv_obj_set_style_bg_color(button, lv_color_hex(0x171717), 0);
    lv_obj_set_style_border_color(button, lv_color_hex(0x404040), 0);
    lv_obj_set_style_border_width(button, 1, 0);
    lv_obj_set_style_shadow_width(button, 0, 0);
    lv_obj_add_event_cb(
        button,
        keyEvent,
        LV_EVENT_ALL,
        reinterpret_cast<void*>(static_cast<uintptr_t>(index + 1)));

    lv_obj_t* label = lv_label_create(button);
    keyLabels[index] = label;
    String defaultLabel = "Key " + String(index + 1);
    lv_label_set_text(label, defaultLabel.c_str());
    lv_label_set_long_mode(label, LV_LABEL_LONG_WRAP);
    lv_obj_set_width(label, buttonWidth - 8);
    lv_obj_set_height(label, 30);
    lv_obj_set_style_text_align(label, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_set_style_text_color(label, lv_color_hex(0xF5F5F5), 0);
    lv_obj_set_style_text_letter_space(label, -1, 0);
    lv_obj_center(label);

    lv_obj_t* image = lv_image_create(button);
    keyImages[index] = image;
    lv_obj_add_flag(image, LV_OBJ_FLAG_HIDDEN);
    lv_obj_align(image, LV_ALIGN_TOP_MID, 0, 10);
  }

  levelSlider = lv_slider_create(screen);
  lv_obj_set_pos(
      levelSlider,
      gridRight + faderGap + (faderWidth - sliderRailWidth) / 2,
      top + sliderIconSpace);
  lv_obj_set_size(
      levelSlider,
      sliderRailWidth,
      HcdConfig::DISPLAY_HEIGHT - top - bottom - sliderIconSpace * 2);
  lv_slider_set_range(levelSlider, 0, 1023);
  lv_slider_set_value(levelSlider, displayedSliderValue, LV_ANIM_OFF);
  styleFader(levelSlider);

  volumeHighIcon = lv_label_create(screen);
  lv_label_set_text(volumeHighIcon, LV_SYMBOL_VOLUME_MAX);
  lv_obj_set_style_text_color(volumeHighIcon, lv_color_hex(0xE8E8E8), 0);
  lv_obj_align_to(volumeHighIcon, levelSlider, LV_ALIGN_OUT_TOP_MID, 0, -8);

  volumeMuteIcon = lv_label_create(screen);
  lv_label_set_text(volumeMuteIcon, LV_SYMBOL_MUTE);
  lv_obj_set_style_text_color(volumeMuteIcon, lv_color_hex(0x8A8A8A), 0);
  lv_obj_align_to(volumeMuteIcon, levelSlider, LV_ALIGN_OUT_BOTTOM_MID, 0, 8);

  sliderTouchArea = lv_obj_create(screen);
  lv_obj_set_pos(sliderTouchArea, gridRight + faderGap, top - 5);
  lv_obj_set_size(sliderTouchArea, faderWidth, HcdConfig::DISPLAY_HEIGHT - top - bottom + 10);
  lv_obj_set_style_bg_opa(sliderTouchArea, LV_OPA_TRANSP, 0);
  lv_obj_set_style_border_width(sliderTouchArea, 0, 0);
  lv_obj_set_style_pad_all(sliderTouchArea, 0, 0);
  lv_obj_clear_flag(sliderTouchArea, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_add_flag(sliderTouchArea, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_add_event_cb(
      sliderTouchArea,
      sliderTouchEvent,
      LV_EVENT_ALL,
      reinterpret_cast<void*>(static_cast<uintptr_t>(1)));

  const int microphoneColumnX = marginX + 6 * (buttonWidth + gap);
  microphoneSlider = lv_slider_create(screen);
  lv_obj_set_pos(
      microphoneSlider,
      microphoneColumnX + (buttonWidth - sliderRailWidth) / 2,
      top + sliderIconSpace);
  lv_obj_set_size(
      microphoneSlider,
      sliderRailWidth,
      HcdConfig::DISPLAY_HEIGHT - top - bottom - sliderIconSpace * 2);
  lv_slider_set_range(microphoneSlider, 0, 1023);
  lv_slider_set_value(microphoneSlider, displayedMicrophoneValue, LV_ANIM_OFF);
  styleFader(microphoneSlider);

  microphoneHighIcon = lv_label_create(screen);
  lv_label_set_text(microphoneHighIcon, "MIC");
  lv_obj_set_style_text_color(microphoneHighIcon, lv_color_hex(0xE8E8E8), 0);
  lv_obj_align_to(microphoneHighIcon, microphoneSlider, LV_ALIGN_OUT_TOP_MID, 0, -8);

  microphoneMuteIcon = lv_label_create(screen);
  lv_label_set_text(microphoneMuteIcon, LV_SYMBOL_MUTE);
  lv_obj_set_style_text_color(microphoneMuteIcon, lv_color_hex(0x8A8A8A), 0);
  lv_obj_align_to(microphoneMuteIcon, microphoneSlider, LV_ALIGN_OUT_BOTTOM_MID, 0, 8);

  microphoneTouchArea = lv_obj_create(screen);
  lv_obj_set_pos(
      microphoneTouchArea,
      microphoneColumnX + (buttonWidth - faderWidth) / 2,
      top - 5);
  lv_obj_set_size(
      microphoneTouchArea,
      faderWidth,
      HcdConfig::DISPLAY_HEIGHT - top - bottom + 10);
  lv_obj_set_style_bg_opa(microphoneTouchArea, LV_OPA_TRANSP, 0);
  lv_obj_set_style_border_width(microphoneTouchArea, 0, 0);
  lv_obj_set_style_pad_all(microphoneTouchArea, 0, 0);
  lv_obj_clear_flag(microphoneTouchArea, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_add_flag(microphoneTouchArea, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_add_event_cb(
      microphoneTouchArea,
      sliderTouchEvent,
      LV_EVENT_ALL,
      reinterpret_cast<void*>(static_cast<uintptr_t>(2)));
  for (lv_obj_t* object : {
           microphoneSlider,
           microphoneHighIcon,
           microphoneMuteIcon,
           microphoneTouchArea,
       }) {
    lv_obj_add_flag(object, LV_OBJ_FLAG_HIDDEN);
  }
  applyTheme();

  firmwareOverlay = lv_obj_create(screen);
  lv_obj_set_pos(firmwareOverlay, 0, 0);
  lv_obj_set_size(firmwareOverlay, HcdConfig::DISPLAY_WIDTH, HcdConfig::DISPLAY_HEIGHT);
  lv_obj_set_style_bg_color(firmwareOverlay, lv_color_hex(0x080808), 0);
  lv_obj_set_style_bg_opa(firmwareOverlay, LV_OPA_COVER, 0);
  lv_obj_set_style_border_width(firmwareOverlay, 0, 0);
  lv_obj_set_style_radius(firmwareOverlay, 0, 0);
  lv_obj_clear_flag(firmwareOverlay, LV_OBJ_FLAG_SCROLLABLE);

  lv_obj_t* updateTitle = lv_label_create(firmwareOverlay);
  lv_label_set_text(updateTitle, "HACKMAN3D  CONTROL DECK PRO");
  lv_obj_set_style_text_color(updateTitle, lv_color_hex(0xA0A0A0), 0);
  lv_obj_align(updateTitle, LV_ALIGN_TOP_MID, 0, 76);

  lv_obj_t* updateMessage = lv_label_create(firmwareOverlay);
  lv_label_set_text(updateMessage, "FIRMWARE UPDATE");
  lv_obj_set_style_text_color(updateMessage, lv_color_hex(0xFFFFFF), 0);
  lv_obj_align(updateMessage, LV_ALIGN_CENTER, 0, -24);

  lv_obj_t* updateHelp = lv_label_create(firmwareOverlay);
  lv_label_set_text(
      updateHelp,
      "Installing the update...\nDo not unplug the Control Deck.\nThe screen will restart automatically.");
  lv_obj_set_style_text_align(updateHelp, LV_TEXT_ALIGN_CENTER, 0);
  lv_obj_set_style_text_color(updateHelp, lv_color_hex(0xB0B0B0), 0);
  lv_obj_align(updateHelp, LV_ALIGN_CENTER, 0, 48);
  lv_obj_add_flag(firmwareOverlay, LV_OBJ_FLAG_HIDDEN);
}

}  // namespace

namespace HcdDisplay {

bool begin(KeyEventCallback callback, SliderEventCallback sliderCallback) {
  keyEventCallback = callback;
  sliderEventCallback = sliderCallback;
  board = new Board();
  if (board == nullptr || !board->init()) {
    return false;
  }

  LCD* lcd = board->getLCD();
  if (lcd == nullptr) {
    return false;
  }
  lcd->configFrameBufferNumber(1);
  if (lcd->getBus()->getBasicAttributes().type == ESP_PANEL_BUS_TYPE_RGB) {
    BusRGB* rgb = static_cast<BusRGB*>(lcd->getBus());
    // Keep the timing validated for the Waveshare/Caturda 7-inch RGB panel.
    // A lower clock and an oversized bounce buffer can leave this controller
    // active but displaying only its white idle state.
    rgb->configRGB_FreqHz(16000000);
    // Twenty lines are the last configuration validated without persistent
    // drift on this panel while Wi-Fi traffic is active. The
    // height divides 480 into an even number of blocks, as
    // required by the ESP32-S3 RGB driver.
    rgb->configRGB_BounceBufferSize(HcdConfig::DISPLAY_WIDTH * 20);
  }
  if (!board->begin()) {
    return false;
  }
  if (!HcdLvglAdapter::begin(
          lcd,
          board->getTouch(),
          HcdConfig::DISPLAY_WIDTH,
          HcdConfig::DISPLAY_HEIGHT)) {
    return false;
  }
  if (!HcdLvglAdapter::lock()) {
    return false;
  }
  buildInterface();
  HcdLvglAdapter::unlock();
  return true;
}

void setAppConnected(bool connected) {
  if (connectionDot == nullptr || !HcdLvglAdapter::lock(50)) {
    return;
  }
  lv_obj_set_style_bg_color(
      connectionDot,
      lv_color_hex(connected ? 0xF02020 : 0x3A3A3A),
      0);
  HcdLvglAdapter::unlock();
}

void setWifiStatus(bool connected, bool configured, const IPAddress& address) {
  if (networkLabel == nullptr || !HcdLvglAdapter::lock(50)) {
    return;
  }
  const String message = connected
      ? "Wi-Fi  " + address.toString()
      : (configured ? "Wi-Fi connecting..." : "Wi-Fi setup required");
  lv_label_set_text(networkLabel, message.c_str());
  HcdLvglAdapter::unlock();
}

void setKeyLabel(uint8_t keyId, const String& label) {
  if (keyId == 0 || keyId > HcdConfig::KEY_COUNT || !HcdLvglAdapter::lock(50)) {
    return;
  }
  lv_label_set_text(keyLabels[keyId - 1], label.substring(0, 24).c_str());
  HcdLvglAdapter::unlock();
}

void setKeyIcon(uint8_t keyId, const uint8_t* data, size_t size) {
  if (keyId == 0 || keyId > HcdConfig::KEY_COUNT) {
    return;
  }
  const uint8_t index = keyId - 1;
  uint8_t* replacement = nullptr;
  if (data != nullptr && size == HcdConfig::ICON_DATA_SIZE) {
    replacement = static_cast<uint8_t*>(
        heap_caps_malloc(size, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    if (replacement == nullptr) {
      replacement = static_cast<uint8_t*>(malloc(size));
    }
    if (replacement == nullptr) {
      return;
    }
    memcpy(replacement, data, size);
  }
  if (!HcdLvglAdapter::lock(100)) {
    free(replacement);
    return;
  }

  uint8_t* previous = keyImageData[index];
  keyImageData[index] = replacement;
  if (replacement == nullptr) {
    lv_obj_add_flag(keyImages[index], LV_OBJ_FLAG_HIDDEN);
  } else {
    lv_image_dsc_t& descriptor = keyImageDescriptors[index];
    memset(&descriptor, 0, sizeof(descriptor));
    descriptor.header.magic = LV_IMAGE_HEADER_MAGIC;
    descriptor.header.cf = LV_COLOR_FORMAT_RGB565;
    descriptor.header.w = HcdConfig::ICON_WIDTH;
    descriptor.header.h = HcdConfig::ICON_HEIGHT;
    descriptor.header.stride = HcdConfig::ICON_WIDTH * 2;
    descriptor.data_size = size;
    descriptor.data = replacement;
    lv_image_set_src(keyImages[index], &descriptor);
    lv_image_set_scale(keyImages[index], currentImageScale());
    lv_obj_clear_flag(keyImages[index], LV_OBJ_FLAG_HIDDEN);
  }
  positionKeyContent(index);
  HcdLvglAdapter::unlock();
  free(previous);
}

void refresh() {
  if (!HcdLvglAdapter::lock(250)) {
    return;
  }
  lv_obj_t* screen = lv_screen_active();
  if (screen == nullptr) {
    HcdLvglAdapter::unlock();
    return;
  }
  lv_obj_invalidate(screen);
  lv_refr_now(nullptr);
  HcdLvglAdapter::unlock();
}

void setAppearance(
    uint8_t iconSize,
    bool showLabels,
    uint8_t theme,
    bool secondFader,
    uint8_t sliderMode) {
  const uint8_t nextIconSize = min(iconSize, static_cast<uint8_t>(3));
  const uint8_t nextTheme = min(theme, static_cast<uint8_t>(2));
  const uint8_t nextSliderMode = min(sliderMode, static_cast<uint8_t>(2));
  if (
      currentIconSize == nextIconSize && !labelsVisible &&
      currentTheme == nextTheme && secondFaderVisible == secondFader &&
      currentSliderMode == nextSliderMode) {
    return;
  }
  currentIconSize = nextIconSize;
  labelsVisible = false;
  currentTheme = nextTheme;
  secondFaderVisible = secondFader;
  currentSliderMode = nextSliderMode;
  if (!HcdLvglAdapter::lock(100)) {
    return;
  }
  applyTheme();
  if (currentSliderMode == 2) {
    lv_label_set_text(volumeHighIcon, LV_SYMBOL_EYE_OPEN);
    lv_label_set_text(volumeMuteIcon, LV_SYMBOL_EYE_CLOSE);
  } else {
    lv_label_set_text(volumeHighIcon, LV_SYMBOL_VOLUME_MAX);
    lv_label_set_text(volumeMuteIcon, LV_SYMBOL_MUTE);
  }
  for (lv_obj_t* object : {
           levelSlider,
           volumeHighIcon,
           volumeMuteIcon,
           sliderTouchArea,
       }) {
    if (currentSliderMode == 0) {
      lv_obj_add_flag(object, LV_OBJ_FLAG_HIDDEN);
    } else {
      lv_obj_remove_flag(object, LV_OBJ_FLAG_HIDDEN);
    }
  }
  for (uint8_t index = 0; index < HcdConfig::KEY_COUNT; ++index) {
    lv_image_set_scale(keyImages[index], currentImageScale());
    positionKeyContent(index);
    if (secondFaderVisible && index % 7 == 6) {
      lv_obj_add_flag(keyButtons[index], LV_OBJ_FLAG_HIDDEN);
    } else {
      lv_obj_remove_flag(keyButtons[index], LV_OBJ_FLAG_HIDDEN);
    }
  }
  for (lv_obj_t* object : {
           microphoneSlider,
           microphoneHighIcon,
           microphoneMuteIcon,
           microphoneTouchArea,
       }) {
    if (secondFaderVisible) {
      lv_obj_remove_flag(object, LV_OBJ_FLAG_HIDDEN);
    } else {
      lv_obj_add_flag(object, LV_OBJ_FLAG_HIDDEN);
    }
  }
  HcdLvglAdapter::unlock();
}

void setSliderValue(uint8_t sliderId, uint16_t value) {
  const uint16_t normalized = min(value, static_cast<uint16_t>(1023));
  lv_obj_t* slider = sliderId == 2 ? microphoneSlider : levelSlider;
  uint16_t& displayedValue = sliderId == 2
      ? displayedMicrophoneValue
      : displayedSliderValue;
  if (slider == nullptr || normalized == displayedValue || !HcdLvglAdapter::lock(50)) {
    return;
  }
  displayedValue = normalized;
  lv_slider_set_value(slider, normalized, LV_ANIM_OFF);
  HcdLvglAdapter::unlock();
}

void showFirmwareUpdate() {
  if (board == nullptr || firmwareOverlay == nullptr || !HcdLvglAdapter::lock(-1)) {
    return;
  }
  lv_obj_remove_flag(firmwareOverlay, LV_OBJ_FLAG_HIDDEN);
  lv_obj_move_foreground(firmwareOverlay);
  lv_obj_invalidate(firmwareOverlay);
  lv_refr_now(lv_display_get_default());
  HcdLvglAdapter::unlock();
  delay(900);
}

void beginFirmwareWrite() {
  if (board == nullptr) {
    return;
  }
  // Flash writes can momentarily starve the RGB DMA. Physically turn off the
  // expander-controlled backlight so no corrupted frames reach the user.
  Backlight* backlight = board->getBacklight();
  if (backlight != nullptr) {
    backlight->off();
  }
  IO_Expander* ioExpander = board->getIO_Expander();
  if (ioExpander != nullptr && ioExpander->getBase() != nullptr) {
    ioExpander->getBase()->digitalWrite(2, 0);
  }
  delay(30);
  HcdLvglAdapter::shutdown();
}

void prepareForRestart() {
  if (board == nullptr) {
    return;
  }
  HcdLvglAdapter::shutdown();
  Backlight* backlight = board->getBacklight();
  if (backlight != nullptr) {
    backlight->off();
  }
  LCD* lcd = board->getLCD();
  if (lcd != nullptr) {
    lcd->del();
  }
  IO_Expander* ioExpander = board->getIO_Expander();
  if (ioExpander != nullptr && ioExpander->getBase() != nullptr) {
    // The ST7262 and its backlight keep their state across ESP.restart().
    // Hold both expander outputs low so the following boot performs a real
    // panel reset, just like a USB power cycle.
    ioExpander->getBase()->digitalWrite(2, 0);
    ioExpander->getBase()->digitalWrite(3, 0);
    delay(80);
  }
  board->del();
  delay(120);
}

bool selectSdCard(bool selected) {
  if (board == nullptr || board->getIO_Expander() == nullptr ||
      board->getIO_Expander()->getBase() == nullptr) {
    return false;
  }
  // EXIO4 is the active-low TF-card chip select on this Waveshare board.
  return board->getIO_Expander()->getBase()->digitalWrite(4, selected ? LOW : HIGH);
}

}  // namespace HcdDisplay
