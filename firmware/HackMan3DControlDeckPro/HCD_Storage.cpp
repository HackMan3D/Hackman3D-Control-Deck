#include "HCD_Storage.h"

#include <FS.h>
#include <SD.h>
#include <SPI.h>

#include "HCD_Config.h"
#include "HCD_Display.h"

namespace {

constexpr int SD_MOSI = 11;
constexpr int SD_CLOCK = 12;
constexpr int SD_MISO = 13;
constexpr int SD_SS = -1;
constexpr uint32_t SD_FREQUENCY = 4000000;
constexpr char CACHE_DIRECTORY[] = "/hcd";
constexpr char ICON_DIRECTORY[] = "/hcd/icons";
constexpr char SIGNATURE_FILE[] = "/hcd/icon_crc.bin";

bool ready = false;
const char* storageStatus = "NOT_STARTED";
uint32_t signatures[HcdConfig::KEY_COUNT] = {};

String iconPath(uint8_t keyId) {
  char path[28];
  snprintf(path, sizeof(path), "%s/%02u.rgb", ICON_DIRECTORY, keyId);
  return String(path);
}

void loadSignatures() {
  File file = SD.open(SIGNATURE_FILE, FILE_READ);
  if (!file || file.size() != sizeof(signatures)) {
    if (file) {
      file.close();
    }
    memset(signatures, 0, sizeof(signatures));
    return;
  }
  if (file.read(reinterpret_cast<uint8_t*>(signatures), sizeof(signatures)) !=
      sizeof(signatures)) {
    memset(signatures, 0, sizeof(signatures));
  }
  file.close();
}

bool saveSignatures() {
  const String temporary = String(SIGNATURE_FILE) + ".tmp";
  SD.remove(temporary);
  File file = SD.open(temporary, FILE_WRITE);
  if (!file) {
    return false;
  }
  const bool written =
      file.write(reinterpret_cast<const uint8_t*>(signatures), sizeof(signatures)) ==
      sizeof(signatures);
  file.flush();
  file.close();
  if (!written) {
    SD.remove(temporary);
    return false;
  }
  SD.remove(SIGNATURE_FILE);
  return SD.rename(temporary, SIGNATURE_FILE);
}

}  // namespace

namespace HcdStorage {

bool begin() {
  ready = false;
  SD.end();
  SPI.end();
  if (!HcdDisplay::selectSdCard(false)) {
    storageStatus = "CS_ERROR";
    return false;
  }
  delay(10);
  if (!HcdDisplay::selectSdCard(true)) {
    storageStatus = "CS_ERROR";
    return false;
  }
  SPI.setHwCs(false);
  if (!SPI.begin(SD_CLOCK, SD_MISO, SD_MOSI, SD_SS)) {
    storageStatus = "SPI_ERROR";
    return false;
  }
  // The final argument allows FAT32 creation only when a present card cannot
  // be mounted. An already usable card is never reformatted.
  if (!SD.begin(static_cast<uint8_t>(SD_SS), SPI, SD_FREQUENCY, "/hcdsd", 8, true)) {
    storageStatus = "MOUNT_ERROR";
    return false;
  }
  if (SD.cardType() == CARD_NONE) {
    storageStatus = "NO_CARD";
    return false;
  }
  if (!SD.exists(CACHE_DIRECTORY) && !SD.mkdir(CACHE_DIRECTORY)) {
    storageStatus = "DIRECTORY_ERROR";
    return false;
  }
  if (!SD.exists(ICON_DIRECTORY) && !SD.mkdir(ICON_DIRECTORY)) {
    storageStatus = "DIRECTORY_ERROR";
    return false;
  }
  loadSignatures();
  ready = true;
  storageStatus = "READY";
  return true;
}

bool isReady() {
  return ready;
}

const char* status() {
  return storageStatus;
}

uint64_t capacityBytes() {
  return ready ? SD.cardSize() : 0;
}

uint64_t usedBytes() {
  return ready ? SD.usedBytes() : 0;
}

uint32_t iconSignature(uint8_t keyId) {
  return ready && keyId > 0 && keyId <= HcdConfig::KEY_COUNT
      ? signatures[keyId - 1]
      : 0;
}

bool loadIcon(uint8_t keyId, uint8_t* output, size_t size) {
  if (!ready || output == nullptr || size != HcdConfig::ICON_DATA_SIZE ||
      iconSignature(keyId) == 0) {
    return false;
  }
  File file = SD.open(iconPath(keyId), FILE_READ);
  if (!file || file.size() != static_cast<int>(size)) {
    if (file) {
      file.close();
    }
    signatures[keyId - 1] = 0;
    return false;
  }
  const bool loaded = file.read(output, size) == size;
  file.close();
  return loaded;
}

bool saveIcon(uint8_t keyId, const uint8_t* data, size_t size, uint32_t signature) {
  if (!ready || keyId == 0 || keyId > HcdConfig::KEY_COUNT || data == nullptr ||
      size != HcdConfig::ICON_DATA_SIZE || signature == 0) {
    return false;
  }
  if (signatures[keyId - 1] == signature && SD.exists(iconPath(keyId))) {
    return true;
  }
  const String path = iconPath(keyId);
  const String temporary = path + ".tmp";
  SD.remove(temporary);
  File file = SD.open(temporary, FILE_WRITE);
  if (!file) {
    return false;
  }
  const bool written = file.write(data, size) == size;
  file.flush();
  file.close();
  if (!written) {
    SD.remove(temporary);
    return false;
  }
  SD.remove(path);
  if (!SD.rename(temporary, path)) {
    return false;
  }
  signatures[keyId - 1] = signature;
  return saveSignatures();
}

bool removeIcon(uint8_t keyId) {
  if (!ready || keyId == 0 || keyId > HcdConfig::KEY_COUNT) {
    return false;
  }
  SD.remove(iconPath(keyId));
  signatures[keyId - 1] = 0;
  return saveSignatures();
}

}  // namespace HcdStorage
