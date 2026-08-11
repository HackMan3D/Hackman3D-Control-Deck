#pragma once

#include <Arduino.h>

namespace HcdStorage {

bool begin();
bool isReady();
const char* status();
uint64_t capacityBytes();
uint64_t usedBytes();
uint32_t iconSignature(uint8_t keyId);
bool loadIcon(uint8_t keyId, uint8_t* output, size_t size);
bool saveIcon(uint8_t keyId, const uint8_t* data, size_t size, uint32_t signature);
bool removeIcon(uint8_t keyId);

}  // namespace HcdStorage
