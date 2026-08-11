#include "HCD_FlashCache.h"

#include <FS.h>
#include <SPIFFS.h>
#include <esp_heap_caps.h>

#include "HCD_Config.h"
#include "HCD_Display.h"

namespace {

constexpr uint32_t CACHE_MAGIC = 0x48434449;
constexpr uint16_t CACHE_VERSION = 1;
constexpr char MANIFEST_PATH[] = "/icon_cache.bin";

struct CacheManifest {
  uint32_t magic;
  uint16_t version;
  uint16_t keyCount;
  uint32_t signatures[HcdConfig::KEY_COUNT];
};

CacheManifest manifest = {};
uint8_t* preloaded[HcdConfig::KEY_COUNT] = {};
uint8_t* pending[HcdConfig::KEY_COUNT] = {};
bool pendingRemoval[HcdConfig::KEY_COUNT] = {};
uint32_t pendingSignatures[HcdConfig::KEY_COUNT] = {};
bool ready = false;

String iconPath(uint8_t keyId) {
  char path[20];
  snprintf(path, sizeof(path), "/icon_%02u.rgb", keyId);
  return String(path);
}

uint8_t* allocateIcon() {
  uint8_t* data = static_cast<uint8_t*>(
      heap_caps_malloc(HcdConfig::ICON_DATA_SIZE, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  return data != nullptr
      ? data
      : static_cast<uint8_t*>(malloc(HcdConfig::ICON_DATA_SIZE));
}

void resetManifest() {
  memset(&manifest, 0, sizeof(manifest));
  manifest.magic = CACHE_MAGIC;
  manifest.version = CACHE_VERSION;
  manifest.keyCount = HcdConfig::KEY_COUNT;
}

bool readManifest() {
  File file = SPIFFS.open(MANIFEST_PATH, FILE_READ);
  if (!file || file.size() != sizeof(manifest)) {
    if (file) {
      file.close();
    }
    return false;
  }
  const bool read = file.read(reinterpret_cast<uint8_t*>(&manifest), sizeof(manifest)) ==
      sizeof(manifest);
  file.close();
  return read && manifest.magic == CACHE_MAGIC && manifest.version == CACHE_VERSION &&
      manifest.keyCount == HcdConfig::KEY_COUNT;
}

bool writeManifest() {
  constexpr char temporary[] = "/icon_cache.tmp";
  SPIFFS.remove(temporary);
  File file = SPIFFS.open(temporary, FILE_WRITE);
  if (!file) {
    return false;
  }
  const bool written =
      file.write(reinterpret_cast<const uint8_t*>(&manifest), sizeof(manifest)) ==
      sizeof(manifest);
  file.close();
  if (!written) {
    SPIFFS.remove(temporary);
    return false;
  }
  SPIFFS.remove(MANIFEST_PATH);
  return SPIFFS.rename(temporary, MANIFEST_PATH);
}

}  // namespace

namespace HcdFlashCache {

bool beginAndPreload() {
  ready = SPIFFS.begin(true);
  if (!ready) {
    resetManifest();
    return false;
  }
  if (!readManifest()) {
    resetManifest();
  }
  for (uint8_t keyId = 1; keyId <= HcdConfig::KEY_COUNT; ++keyId) {
    const uint8_t index = keyId - 1;
    if (manifest.signatures[index] == 0) {
      continue;
    }
    File file = SPIFFS.open(iconPath(keyId), FILE_READ);
    if (!file || file.size() != HcdConfig::ICON_DATA_SIZE) {
      if (file) {
        file.close();
      }
      manifest.signatures[index] = 0;
      continue;
    }
    preloaded[index] = allocateIcon();
    if (preloaded[index] == nullptr ||
        file.read(preloaded[index], HcdConfig::ICON_DATA_SIZE) != HcdConfig::ICON_DATA_SIZE) {
      free(preloaded[index]);
      preloaded[index] = nullptr;
      manifest.signatures[index] = 0;
    }
    file.close();
  }
  return true;
}

void applyPreloadedIcons() {
  for (uint8_t index = 0; index < HcdConfig::KEY_COUNT; ++index) {
    if (preloaded[index] != nullptr) {
      HcdDisplay::setKeyIcon(index + 1, preloaded[index], HcdConfig::ICON_DATA_SIZE);
      free(preloaded[index]);
      preloaded[index] = nullptr;
    }
  }
}

uint32_t iconSignature(uint8_t keyId) {
  return ready && keyId > 0 && keyId <= HcdConfig::KEY_COUNT
      ? manifest.signatures[keyId - 1]
      : 0;
}

bool stageIcon(uint8_t keyId, const uint8_t* data, size_t size, uint32_t signature) {
  if (!ready || keyId == 0 || keyId > HcdConfig::KEY_COUNT || data == nullptr ||
      size != HcdConfig::ICON_DATA_SIZE || signature == 0) {
    return false;
  }
  const uint8_t index = keyId - 1;
  if (manifest.signatures[index] == signature && SPIFFS.exists(iconPath(keyId))) {
    return true;
  }
  uint8_t* replacement = allocateIcon();
  if (replacement == nullptr) {
    return false;
  }
  memcpy(replacement, data, size);
  free(pending[index]);
  pending[index] = replacement;
  pendingRemoval[index] = false;
  pendingSignatures[index] = signature;
  return true;
}

bool stageIconRemoval(uint8_t keyId) {
  if (!ready || keyId == 0 || keyId > HcdConfig::KEY_COUNT) {
    return false;
  }
  const uint8_t index = keyId - 1;
  free(pending[index]);
  pending[index] = nullptr;
  pendingRemoval[index] = manifest.signatures[index] != 0;
  pendingSignatures[index] = 0;
  return true;
}

bool hasPendingChanges() {
  for (uint8_t index = 0; index < HcdConfig::KEY_COUNT; ++index) {
    if (pending[index] != nullptr || pendingRemoval[index]) {
      return true;
    }
  }
  return false;
}

bool commit() {
  if (!ready) {
    return false;
  }
  bool successful = true;
  for (uint8_t index = 0; index < HcdConfig::KEY_COUNT; ++index) {
    const uint8_t keyId = index + 1;
    const String path = iconPath(keyId);
    if (pendingRemoval[index]) {
      SPIFFS.remove(path);
      manifest.signatures[index] = 0;
    } else if (pending[index] != nullptr) {
      const String temporary = path + ".tmp";
      SPIFFS.remove(temporary);
      File file = SPIFFS.open(temporary, FILE_WRITE);
      const bool written = file &&
          file.write(pending[index], HcdConfig::ICON_DATA_SIZE) == HcdConfig::ICON_DATA_SIZE;
      if (file) {
        file.close();
      }
      if (written) {
        SPIFFS.remove(path);
        if (SPIFFS.rename(temporary, path)) {
          manifest.signatures[index] = pendingSignatures[index];
        } else {
          successful = false;
        }
      } else {
        SPIFFS.remove(temporary);
        successful = false;
      }
    }
    free(pending[index]);
    pending[index] = nullptr;
    pendingRemoval[index] = false;
    pendingSignatures[index] = 0;
  }
  return writeManifest() && successful;
}

}  // namespace HcdFlashCache
