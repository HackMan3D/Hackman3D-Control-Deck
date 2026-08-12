#pragma once

#include <Arduino.h>

namespace HcdUsb {

using CommandHandler = void (*)(const String& line, Print& reply);

void begin();
void update(CommandHandler handler);
void sendLine(const String& line);

}  // namespace HcdUsb
