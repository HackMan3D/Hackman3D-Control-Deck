/*
 * HackMan3D Control Deck Pro
 * ESP32-S3 7-inch USB touch controller
 *
 * Created, designed and developed by HackMan3D
 */

#include "HCD_Display.h"
#include "HCD_FlashCache.h"
#include "HCD_Protocol.h"

void setup() {
  Serial.begin(115200);
  Serial0.begin(115200);
  delay(200);
  Serial.println(F("HackMan3D Control Deck Pro starting"));
  Serial0.println(F("HackMan3D Control Deck Pro starting"));

  // Read persistent icons before the RGB panel begins refreshing.
  HcdFlashCache::beginAndPreload();

  if (!HcdDisplay::begin(HcdProtocol::sendKeyEvent, HcdProtocol::sendSliderEvent)) {
    Serial.println(F("HCD_ERROR|DISPLAY_INIT"));
    Serial0.println(F("HCD_ERROR|DISPLAY_INIT"));
    while (true) {
      delay(1000);
    }
  }
  HcdFlashCache::applyPreloadedIcons();
  HcdProtocol::begin();
  Serial.println(F("HCD_READY|1.3.6"));
  Serial0.println(F("HCD_READY|1.3.6"));
}

void loop() {
  HcdProtocol::update();
  delay(2);
}
