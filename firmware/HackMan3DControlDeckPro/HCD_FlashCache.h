#pragma once

#include <Arduino.h>

namespace HcdFlashCache {

bool beginAndPreload();
void applyPreloadedIcons();
uint32_t iconSignature(uint8_t keyId);
bool stageIcon(uint8_t keyId, const uint8_t* data, size_t size, uint32_t signature);
bool stageIconRemoval(uint8_t keyId);
bool hasPendingChanges();
bool commit();

}  // namespace HcdFlashCache
