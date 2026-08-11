#include "HCD_LvglAdapter.h"

#include <Arduino.h>
#include <esp_heap_caps.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <freertos/task.h>

using esp_panel::drivers::LCD;
using esp_panel::drivers::Touch;
using esp_panel::drivers::TouchPoint;

namespace {

SemaphoreHandle_t lvglMutex = nullptr;
TaskHandle_t lvglTask = nullptr;
esp_timer_handle_t tickTimer = nullptr;
LCD* panelLcd = nullptr;
Touch* panelTouch = nullptr;
lv_display_t* display = nullptr;
void* frameBuffer1 = nullptr;
void* frameBuffer2 = nullptr;
void* renderBuffer = nullptr;
volatile bool refreshCallbackReady = false;
volatile uint32_t flushCount = 0;
volatile uint32_t vsyncCount = 0;
volatile uint32_t switchFailureCount = 0;
void* lastFlushedBuffer = nullptr;
bool touchPressed = false;
bool ignoredTouch = false;
unsigned long lastAcceptedPressAt = 0;

// Prevent an unrealistically fast burst from continuously invalidating LVGL
// objects and starving the RGB scan-out. Seventy milliseconds still permits
// more than fourteen deliberate actions per second.
constexpr unsigned long TOUCH_RETRIGGER_GUARD_MS = 70;

void tick(void*) {
  lv_tick_inc(2);
}

void worker(void*) {
  while (!refreshCallbackReady) {
    vTaskDelay(pdMS_TO_TICKS(1));
  }
  while (true) {
    uint32_t waitMs = 10;
    if (HcdLvglAdapter::lock()) {
      waitMs = lv_timer_handler();
      HcdLvglAdapter::unlock();
    }
    waitMs = constrain(waitMs, 2U, 100U);
    vTaskDelay(pdMS_TO_TICKS(waitMs));
  }
}

IRAM_ATTR bool refreshFinished(void* userData) {
  ++vsyncCount;
  BaseType_t shouldYield = pdFALSE;
  xTaskNotifyFromISR(
      static_cast<TaskHandle_t>(userData),
      ULONG_MAX,
      eNoAction,
      &shouldYield);
  return shouldYield == pdTRUE;
}

void flushDisplay(lv_display_t* lvDisplay, const lv_area_t* area, uint8_t* pixels) {
  LCD* lcd = static_cast<LCD*>(lv_display_get_user_data(lvDisplay));
  if (lcd == nullptr) {
    lv_display_flush_ready(lvDisplay);
    return;
  }
  if (area == nullptr) {
    lv_display_flush_ready(lvDisplay);
    return;
  }
  ++flushCount;
  lastFlushedBuffer = pixels;
  if (!lcd->drawBitmap(
          area->x1,
          area->y1,
          lv_area_get_width(area),
          lv_area_get_height(area),
          pixels)) {
    ++switchFailureCount;
  }
  lv_display_flush_ready(lvDisplay);
}

void readTouch(lv_indev_t* input, lv_indev_data_t* data) {
  Touch* touch = static_cast<Touch*>(lv_indev_get_user_data(input));
  TouchPoint point = {};
  const bool rawPressed = touch != nullptr && touch->readPoints(&point, 1, 0) > 0;
  if (rawPressed && !touchPressed && !ignoredTouch) {
    const unsigned long now = millis();
    if (lastAcceptedPressAt != 0 && now - lastAcceptedPressAt < TOUCH_RETRIGGER_GUARD_MS) {
      ignoredTouch = true;
    } else {
      touchPressed = true;
      lastAcceptedPressAt = now;
    }
  } else if (!rawPressed) {
    touchPressed = false;
    ignoredTouch = false;
  }
  if (rawPressed && touchPressed && !ignoredTouch) {
    data->point.x = point.x;
    data->point.y = point.y;
    data->state = LV_INDEV_STATE_PRESSED;
  } else {
    data->state = LV_INDEV_STATE_RELEASED;
  }
}

}  // namespace

namespace HcdLvglAdapter {

bool begin(LCD* lcd, Touch* touch, uint16_t width, uint16_t height) {
  if (lcd == nullptr || lvglMutex != nullptr) {
    return false;
  }
  panelLcd = lcd;
  panelTouch = touch;
  lvglMutex = xSemaphoreCreateRecursiveMutex();
  if (lvglMutex == nullptr) {
    return false;
  }

  lv_init();
  const esp_timer_create_args_t tickConfig = {
      .callback = tick,
      .arg = nullptr,
      .dispatch_method = ESP_TIMER_TASK,
      .name = "hcd_lv_tick",
      .skip_unhandled_events = true,
  };
  if (esp_timer_create(&tickConfig, &tickTimer) != ESP_OK ||
      esp_timer_start_periodic(tickTimer, 2000) != ESP_OK) {
    return false;
  }

  frameBuffer1 = panelLcd->getFrameBufferByIndex(0);
  frameBuffer2 = panelLcd->getFrameBufferByIndex(1);
  if (frameBuffer1 == nullptr) {
    return false;
  }

  const uint32_t renderBytes =
      width * 40 * LV_COLOR_FORMAT_GET_SIZE(LV_COLOR_FORMAT_RGB565);
  renderBuffer = heap_caps_malloc(renderBytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (renderBuffer == nullptr) {
    renderBuffer = heap_caps_malloc(renderBytes, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
  }
  if (renderBuffer == nullptr) {
    return false;
  }

  display = lv_display_create(width, height);
  if (display == nullptr) {
    return false;
  }
  lv_display_set_color_format(display, LV_COLOR_FORMAT_RGB565);
  lv_display_set_flush_cb(display, flushDisplay);
  lv_display_set_buffers(
      display,
      renderBuffer,
      nullptr,
      renderBytes,
      LV_DISPLAY_RENDER_MODE_PARTIAL);
  lv_display_set_user_data(display, panelLcd);
  lv_display_set_default(display);

  if (panelTouch != nullptr) {
    lv_indev_t* input = lv_indev_create();
    if (input == nullptr) {
      return false;
    }
    lv_indev_set_type(input, LV_INDEV_TYPE_POINTER);
    lv_indev_set_read_cb(input, readTouch);
    lv_indev_set_user_data(input, panelTouch);
    lv_indev_set_display(input, display);
  }

  if (xTaskCreatePinnedToCore(
          worker,
          "hcd_lvgl",
          12 * 1024,
          nullptr,
          2,
          &lvglTask,
          ARDUINO_RUNNING_CORE) != pdPASS) {
    return false;
  }
  panelLcd->attachRefreshFinishCallback(refreshFinished, lvglTask);
  refreshCallbackReady = true;
  return true;
}

void shutdown() {
  refreshCallbackReady = false;
  if (panelLcd != nullptr) {
    panelLcd->attachRefreshFinishCallback(nullptr, nullptr);
  }
  if (tickTimer != nullptr) {
    esp_timer_stop(tickTimer);
    esp_timer_delete(tickTimer);
    tickTimer = nullptr;
  }
  if (lvglTask != nullptr) {
    vTaskDelete(lvglTask);
    lvglTask = nullptr;
  }
}

bool lock(int32_t timeoutMs) {
  if (lvglMutex == nullptr) {
    return false;
  }
  const TickType_t ticks = timeoutMs < 0 ? portMAX_DELAY : pdMS_TO_TICKS(timeoutMs);
  return xSemaphoreTakeRecursive(lvglMutex, ticks) == pdTRUE;
}

void unlock() {
  if (lvglMutex != nullptr) {
    xSemaphoreGiveRecursive(lvglMutex);
  }
}

String diagnostics() {
  char message[192];
  const uint16_t first1 = frameBuffer1 == nullptr
      ? 0
      : *static_cast<const uint16_t*>(frameBuffer1);
  const uint16_t first2 = frameBuffer2 == nullptr
      ? 0
      : *static_cast<const uint16_t*>(frameBuffer2);
  snprintf(
      message,
      sizeof(message),
      "flush=%lu|vsync=%lu|fail=%lu|fb1=%p:%04X|fb2=%p:%04X|last=%p|ready=%u",
      static_cast<unsigned long>(flushCount),
      static_cast<unsigned long>(vsyncCount),
      static_cast<unsigned long>(switchFailureCount),
      frameBuffer1,
      first1,
      frameBuffer2,
      first2,
      lastFlushedBuffer,
      refreshCallbackReady ? 1 : 0);
  return String(message);
}

}  // namespace HcdLvglAdapter
