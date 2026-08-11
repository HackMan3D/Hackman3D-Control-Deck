#pragma once

#include <Arduino.h>

namespace HcdWifi {

using CommandHandler = void (*)(const String& line, Print& reply);

void begin();
void update(CommandHandler handler);
bool isConnected();
bool hasSavedCredentials();
IPAddress localAddress();
void sendLine(const String& line);

}  // namespace HcdWifi
