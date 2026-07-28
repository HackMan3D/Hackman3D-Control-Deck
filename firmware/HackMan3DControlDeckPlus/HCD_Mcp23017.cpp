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

bool writeRegister(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(HcdConfig::MCP23017_ADDRESS);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

}  // namespace

namespace HcdMcp23017 {

bool begin() {
  Wire.begin();
  Wire.setClock(400000);

  // GPA0–GPA7 and GPB0–GPB5 are active-low inputs with internal pull-ups.
  available = writeRegister(IODIRA, 0xFF) &&
              writeRegister(IODIRB, 0xFF) &&
              writeRegister(GPPUA, 0xFF) &&
              writeRegister(GPPUB, 0x3F);
  return available;
}

bool isAvailable() { return available; }

uint16_t readInputs() {
  if (!available) {
    return 0xFFFF;
  }

  Wire.beginTransmission(HcdConfig::MCP23017_ADDRESS);
  Wire.write(GPIOA);
  if (Wire.endTransmission(false) != 0) {
    available = false;
    return 0xFFFF;
  }

  const uint8_t received = Wire.requestFrom(
      static_cast<uint8_t>(HcdConfig::MCP23017_ADDRESS),
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
