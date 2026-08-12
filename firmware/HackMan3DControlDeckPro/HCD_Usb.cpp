#include "HCD_Usb.h"

#include "HCD_Config.h"

namespace {

String nativeInputBuffer;
String bridgeInputBuffer;

void readCommands(
    Stream& input,
    Print& reply,
    String& inputBuffer,
    HcdUsb::CommandHandler handler) {
  while (input.available() > 0) {
    const char character = static_cast<char>(input.read());
    if (character == '\r') {
      continue;
    }
    if (character == '\n') {
      if (!inputBuffer.isEmpty() && handler != nullptr) {
        handler(inputBuffer, reply);
      }
      inputBuffer = "";
    } else if (inputBuffer.length() < HcdConfig::LINE_LENGTH - 1) {
      inputBuffer += character;
    } else {
      inputBuffer = "";
    }
  }
}

}  // namespace

namespace HcdUsb {

void begin() {
  nativeInputBuffer.reserve(HcdConfig::LINE_LENGTH);
  bridgeInputBuffer.reserve(HcdConfig::LINE_LENGTH);
}

void update(CommandHandler handler) {
  readCommands(Serial, Serial, nativeInputBuffer, handler);
  readCommands(Serial0, Serial0, bridgeInputBuffer, handler);
}

void sendLine(const String& line) {
  Serial.println(line);
  Serial0.println(line);
}

}  // namespace HcdUsb
