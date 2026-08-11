#include "HCD_Mcp23017.h"

#include <Wire.h>

#include "HCD_Config.h"

namespace {

constexpr uint8_t IODIRA = 0x00;
constexpr uint8_t IODIRB = 0x01;
constexpr uint8_t GPPUA = 0x0C;
constexpr uint8_t GPPUB = 0x0D;
constexpr uint8_t GPIOA = 0x12;

bool available = false;
uint8_t deviceAddress = 0;
unsigned long lastBeginAttemptAt = 0;

bool writeRegister(uint8_t reg, uint8_t value) {
  if (deviceAddress == 0) {
    return false;
  }
  Wire.beginTransmission(deviceAddress);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

}  // namespace

namespace HcdMcp23017 {

bool begin() {
  lastBeginAttemptAt = millis();
  Wire.begin();
  Wire.setClock(100000);

  available = false;
  deviceAddress = 0;
  for (uint8_t address = HcdConfig::MCP23017_ADDRESS;
       address <= HcdConfig::MCP23017_LAST_ADDRESS;
       ++address) {
    Wire.beginTransmission(address);
    if (Wire.endTransmission() == 0) {
      deviceAddress = address;
      break;
    }
  }
  if (deviceAddress == 0) {
    return false;
  }

  // GPB0–GPB7 drive keys 1–8. GPA0–GPA3 drive keys 9–12 and
  // GPA4–GPA5 remain reserved for the two encoder push switches.
  available = writeRegister(IODIRA, 0xFF) &&
              writeRegister(IODIRB, 0xFF) &&
              writeRegister(GPPUA, 0x3F) &&
              writeRegister(GPPUB, 0xFF);
  return available;
}

bool isAvailable() { return available; }

uint16_t readInputs() {
  if (!available) {
    if (millis() - lastBeginAttemptAt >= HcdConfig::MCP_RETRY_INTERVAL_MS) {
      begin();
    }
  }
  if (!available) {
    return 0xFFFF;
  }

  Wire.beginTransmission(deviceAddress);
  Wire.write(GPIOA);
  if (Wire.endTransmission(false) != 0) {
    available = false;
    return 0xFFFF;
  }

  const uint8_t received = Wire.requestFrom(
      deviceAddress,
      static_cast<uint8_t>(2));
  if (received != 2) {
    available = false;
    return 0xFFFF;
  }
  const uint8_t portA = Wire.read();
  const uint8_t portB = Wire.read();
  return static_cast<uint16_t>(portA) |
         (static_cast<uint16_t>(portB) << 8);
}

}  // namespace HcdMcp23017
