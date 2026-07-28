#pragma once

#include <Arduino.h>

namespace HcdMcp23017 {

bool begin();
bool isAvailable();
uint16_t readInputs();

}  // namespace HcdMcp23017
