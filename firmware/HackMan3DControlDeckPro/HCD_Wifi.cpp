#include "HCD_Wifi.h"

#include <ESPmDNS.h>
#include <Preferences.h>
#include <Update.h>
#include <WebServer.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <mbedtls/base64.h>
#include <memory>

#include "HCD_Config.h"
#include "HCD_Display.h"

namespace {

Preferences wifiPreferences;
WiFiServer commandServer(HcdConfig::TCP_PORT);
WiFiClient commandClient;
WiFiUDP discovery;
WebServer setupServer(80);
WebServer otaServer(HcdConfig::OTA_PORT);
String serialBuffer;
String uartBuffer;
String clientBuffer;
bool networkServicesStarted = false;
bool setupPortalStarted = false;
bool restartPending = false;
unsigned long restartAt = 0;
unsigned long wifiStartedAt = 0;
unsigned long lastWifiRetryAt = 0;
String otaToken;
unsigned long otaArmedUntil = 0;
bool otaServerStarted = false;
bool otaUploadAuthorized = false;
bool otaUploadSucceeded = false;

String decodeBase64(const String& value) {
  size_t outputLength = 0;
  const size_t capacity = value.length() * 3 / 4 + 4;
  std::unique_ptr<unsigned char[]> output(new unsigned char[capacity + 1]);
  const int result = mbedtls_base64_decode(
      output.get(),
      capacity,
      &outputLength,
      reinterpret_cast<const unsigned char*>(value.c_str()),
      value.length());
  if (result != 0) {
    return String();
  }
  output[outputLength] = '\0';
  return String(reinterpret_cast<char*>(output.get()));
}

void saveCredentials(const String& ssid, const String& password) {
  wifiPreferences.putString("ssid", ssid);
  wifiPreferences.putString("password", password);
  restartPending = true;
  restartAt = millis() + 700;
}

void showSetupPage() {
  setupServer.send(
      200,
      "text/html; charset=utf-8",
      "<!doctype html><html><head><meta name='viewport' content='width=device-width'>"
      "<style>body{font-family:system-ui;background:#080808;color:#fff;max-width:520px;"
      "margin:50px auto;padding:24px}input,button{box-sizing:border-box;width:100%;padding:14px;"
      "margin:7px 0;border-radius:9px;border:1px solid #444;background:#171717;color:#fff}"
      "button{background:#fff;color:#000;font-weight:700}</style></head><body>"
      "<h1>HackMan3D Control Deck Pro</h1><p>Enter the Wi-Fi network used by this computer.</p>"
      "<form method='post' action='/save'><input name='ssid' placeholder='Wi-Fi network' required>"
      "<input name='password' type='password' placeholder='Password'><button>Save and restart</button>"
      "</form></body></html>");
}

void saveSetupPage() {
  const String ssid = setupServer.arg("ssid");
  if (ssid.isEmpty()) {
    setupServer.send(400, "text/plain", "Wi-Fi network is required.");
    return;
  }
  saveCredentials(ssid, setupServer.arg("password"));
  setupServer.send(
      200,
      "text/html; charset=utf-8",
      "<html><body style='font-family:system-ui;background:#080808;color:#fff;padding:40px'>"
      "<h1>Saved</h1><p>The HCD Pro is restarting and will join your Wi-Fi network.</p>"
      "</body></html>");
}

void startSetupPortal() {
  if (setupPortalStarted) {
    return;
  }
  const uint32_t suffix = static_cast<uint32_t>(ESP.getEfuseMac());
  char accessPointName[32];
  snprintf(accessPointName, sizeof(accessPointName), "HCD-PRO-SETUP-%04X", suffix & 0xFFFF);
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(accessPointName);
  setupServer.on("/", HTTP_GET, showSetupPage);
  setupServer.on("/save", HTTP_POST, saveSetupPage);
  setupServer.begin();
  setupPortalStarted = true;
  Serial.print(F("HCD_WIFI_SETUP|"));
  Serial.print(accessPointName);
  Serial.println(F("|http://192.168.4.1"));
  Serial0.print(F("HCD_WIFI_SETUP|"));
  Serial0.print(accessPointName);
  Serial0.println(F("|http://192.168.4.1"));
}

void startNetworkServices() {
  if (networkServicesStarted || WiFi.status() != WL_CONNECTED) {
    return;
  }
  discovery.begin(HcdConfig::DISCOVERY_PORT);
  commandServer.begin();
  commandServer.setNoDelay(true);
  MDNS.begin("hcd-pro");
  MDNS.addService("hcd", "tcp", HcdConfig::TCP_PORT);
  MDNS.addService("hcd-ota", "tcp", HcdConfig::OTA_PORT);
  otaServer.on(
      "/update",
      HTTP_POST,
      []() {
        if (!otaUploadAuthorized) {
          otaServer.send(403, "text/plain", "OTA update was not authorized.");
          return;
        }
        if (!otaUploadSucceeded) {
          otaServer.send(500, "text/plain", Update.errorString());
          otaToken = "";
          restartPending = true;
          restartAt = millis() + 750;
          return;
        }
        otaServer.send(200, "text/plain", "HCD_OTA_OK");
        otaToken = "";
        // Let the TCP response leave the device before restarting. Restarting
        // inside the HTTP callback can make the desktop report 100% while the
        // new boot partition has not yet been observed by the user.
        restartPending = true;
        restartAt = millis() + 1000;
      },
      []() {
        HTTPUpload& upload = otaServer.upload();
        if (upload.status == UPLOAD_FILE_START) {
          otaUploadAuthorized =
              !otaToken.isEmpty() && millis() < otaArmedUntil &&
              otaServer.arg("token") == otaToken;
          otaUploadSucceeded = false;
          if (otaUploadAuthorized) {
            HcdDisplay::beginFirmwareWrite();
          }
          if (otaUploadAuthorized && !Update.begin(UPDATE_SIZE_UNKNOWN)) {
            otaUploadAuthorized = false;
          }
        } else if (upload.status == UPLOAD_FILE_WRITE) {
          if (otaUploadAuthorized &&
              Update.write(upload.buf, upload.currentSize) != upload.currentSize) {
            otaUploadAuthorized = false;
          }
        } else if (upload.status == UPLOAD_FILE_END) {
          otaUploadSucceeded = otaUploadAuthorized && Update.end(true);
        } else if (upload.status == UPLOAD_FILE_ABORTED) {
          Update.abort();
          otaUploadAuthorized = false;
        }
      });
  otaServer.begin();
  otaServerStarted = true;
  networkServicesStarted = true;
}

bool processOtaArm(const String& line, Print& reply) {
  constexpr char prefix[] = "HCD_OTA_ARM|";
  if (!line.startsWith(prefix)) {
    return false;
  }
  const String token = line.substring(sizeof(prefix) - 1);
  if (token.length() < 16 || token.length() > 64) {
    reply.println(F("HCD_OTA_ERROR|INVALID_TOKEN"));
    return true;
  }
  for (size_t index = 0; index < token.length(); ++index) {
    if (!isAlphaNumeric(token[index])) {
      reply.println(F("HCD_OTA_ERROR|INVALID_TOKEN"));
      return true;
    }
  }
  otaToken = token;
  otaArmedUntil = millis() + 60000;
  HcdDisplay::showFirmwareUpdate();
  reply.print(F("HCD_OTA_READY|"));
  reply.println(HcdConfig::OTA_PORT);
  return true;
}

void processProvisioning(const String& line, Print& reply, bool& handled) {
  handled = false;
  constexpr char prefix[] = "HCD_WIFI_CONFIG|";
  if (!line.startsWith(prefix)) {
    return;
  }
  handled = true;
  const int separator = line.indexOf('|', sizeof(prefix) - 1);
  if (separator < 0) {
    reply.println(F("HCD_WIFI_ERROR|INVALID_FORMAT"));
    return;
  }
  const String ssid = decodeBase64(line.substring(sizeof(prefix) - 1, separator));
  const String password = decodeBase64(line.substring(separator + 1));
  if (ssid.isEmpty()) {
    reply.println(F("HCD_WIFI_ERROR|INVALID_SSID"));
    return;
  }
  saveCredentials(ssid, password);
  reply.println(F("HCD_WIFI_SAVED"));
}

void readCommands(Stream& stream, String& buffer, Print& reply, HcdWifi::CommandHandler handler) {
  while (stream.available() > 0) {
    const char character = static_cast<char>(stream.read());
    if (character == '\r') {
      continue;
    }
    if (character == '\n') {
      if (!buffer.isEmpty()) {
        bool handled = false;
        processProvisioning(buffer, reply, handled);
        if (!handled) {
          handled = processOtaArm(buffer, reply);
        }
        if (!handled && handler != nullptr) {
          handler(buffer, reply);
        }
      }
      buffer = "";
    } else if (buffer.length() < HcdConfig::LINE_LENGTH - 1) {
      buffer += character;
    } else {
      buffer = "";
    }
  }
}

void updateDiscovery() {
  const int packetSize = discovery.parsePacket();
  if (packetSize <= 0) {
    return;
  }
  char message[32] = {};
  const int length = discovery.read(message, sizeof(message) - 1);
  if (length <= 0 || String(message).substring(0, length).indexOf("HCD_DISCOVER") < 0) {
    return;
  }
  discovery.beginPacket(discovery.remoteIP(), discovery.remotePort());
  discovery.print(F("HCD_HERE|"));
  discovery.print(HcdConfig::PRODUCT_NAME);
  discovery.print('|');
  discovery.print(HcdConfig::MODEL_IDENTIFIER);
  discovery.print('|');
  discovery.print(HcdConfig::FIRMWARE_VERSION);
  discovery.print('|');
  discovery.print(HcdConfig::KEY_COUNT);
  discovery.print('|');
  discovery.print(HcdConfig::POTENTIOMETER_COUNT);
  discovery.print('|');
  discovery.print(HcdConfig::TCP_PORT);
  discovery.endPacket();
}

}  // namespace

namespace HcdWifi {

void begin() {
  wifiPreferences.begin("hcd_wifi", false);
  const String ssid = wifiPreferences.getString("ssid", "");
  const String password = wifiPreferences.getString("password", "");
  WiFi.setHostname("hcd-pro");
  if (ssid.isEmpty()) {
    startSetupPortal();
    return;
  }
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(ssid.c_str(), password.c_str());
  wifiStartedAt = millis();
  lastWifiRetryAt = wifiStartedAt;
}

void update(CommandHandler handler) {
  readCommands(Serial, serialBuffer, Serial, handler);
  readCommands(Serial0, uartBuffer, Serial0, handler);
  if (setupPortalStarted) {
    setupServer.handleClient();
  }
  if (
      !setupPortalStarted && wifiStartedAt != 0 && WiFi.status() != WL_CONNECTED &&
      millis() - wifiStartedAt > 120000) {
    startSetupPortal();
  }
  if (
      !setupPortalStarted && wifiStartedAt != 0 && WiFi.status() != WL_CONNECTED &&
      millis() - lastWifiRetryAt > 10000) {
    WiFi.reconnect();
    lastWifiRetryAt = millis();
  }
  if (WiFi.status() == WL_CONNECTED) {
    startNetworkServices();
    updateDiscovery();
    WiFiClient candidate = commandServer.available();
    if (candidate) {
      if (commandClient) {
        commandClient.stop();
      }
      commandClient = candidate;
      commandClient.setNoDelay(true);
      clientBuffer = "";
    }
    if (commandClient && commandClient.connected()) {
      readCommands(commandClient, clientBuffer, commandClient, handler);
    }
    if (otaServerStarted) {
      otaServer.handleClient();
    }
  }
  if (!otaToken.isEmpty() && millis() >= otaArmedUntil) {
    otaToken = "";
  }
  if (restartPending && static_cast<long>(millis() - restartAt) >= 0) {
    HcdDisplay::prepareForRestart();
    ESP.restart();
  }
}

bool isConnected() {
  return WiFi.status() == WL_CONNECTED;
}

bool hasSavedCredentials() {
  return !wifiPreferences.getString("ssid", "").isEmpty();
}

IPAddress localAddress() {
  return WiFi.localIP();
}

void sendLine(const String& line) {
  if (commandClient && commandClient.connected()) {
    commandClient.println(line);
  }
}

}  // namespace HcdWifi
