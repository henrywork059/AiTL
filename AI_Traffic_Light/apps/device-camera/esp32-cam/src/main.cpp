#include <Arduino.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <WiFi.h>
#include <esp_camera.h>

#include "aitl_config.h"

namespace {

// AI Thinker ESP32-CAM camera pin map.
constexpr int PWDN_GPIO_NUM = 32;
constexpr int RESET_GPIO_NUM = -1;
constexpr int XCLK_GPIO_NUM = 0;
constexpr int SIOD_GPIO_NUM = 26;
constexpr int SIOC_GPIO_NUM = 27;
constexpr int Y9_GPIO_NUM = 35;
constexpr int Y8_GPIO_NUM = 34;
constexpr int Y7_GPIO_NUM = 39;
constexpr int Y6_GPIO_NUM = 36;
constexpr int Y5_GPIO_NUM = 21;
constexpr int Y4_GPIO_NUM = 19;
constexpr int Y3_GPIO_NUM = 18;
constexpr int Y2_GPIO_NUM = 5;
constexpr int VSYNC_GPIO_NUM = 25;
constexpr int HREF_GPIO_NUM = 23;
constexpr int PCLK_GPIO_NUM = 22;

WebServer statusServer(80);

bool cameraReady = false;
bool statusServerStarted = false;
unsigned long lastWifiAttemptMs = 0;
unsigned long lastCameraAttemptMs = 0;
unsigned long lastFrameAttemptMs = 0;
unsigned long lastStatusPrintMs = 0;
unsigned long uploadedFrames = 0;
unsigned long failedUploads = 0;
unsigned long lastUploadDurationMs = 0;
size_t lastUploadBytes = 0;
int lastHttpStatus = 0;

bool elapsed(unsigned long now, unsigned long previous, unsigned long interval) {
  return static_cast<unsigned long>(now - previous) >= interval;
}

bool sourceIdLooksValid() {
  const String sourceId(AITL_SOURCE_ID);
  if (sourceId.length() == 0 || sourceId.length() > 64) {
    return false;
  }

  for (size_t index = 0; index < sourceId.length(); ++index) {
    const char value = sourceId[index];
    const bool allowed = isAlphaNumeric(value) || value == '.' || value == '-' || value == '_';
    if (!allowed) {
      return false;
    }
  }
  return true;
}

bool deviceConfigReady() {
  return String(AITL_WIFI_SSID) != "CHANGE_ME" &&
         String(AITL_WIFI_PASSWORD) != "CHANGE_ME" &&
         String(AITL_SERVER_HOST) != "CHANGE_ME" &&
         sourceIdLooksValid();
}

String receiverUrl() {
  String url = "http://";
  url += AITL_SERVER_HOST;
  url += ":";
  url += String(AITL_SERVER_PORT);
  url += "/api/camera/frame?source_id=";
  url += AITL_SOURCE_ID;
  return url;
}

void printConfigurationHelp() {
  Serial.println();
  Serial.println("AiTL ESP32-CAM configuration is still using placeholders.");
  Serial.println("Copy include/secrets.example.h to include/secrets.h, then set:");
  Serial.println("  AITL_WIFI_SSID");
  Serial.println("  AITL_WIFI_PASSWORD");
  Serial.println("  AITL_SERVER_HOST (PC LAN IPv4 address)");
  Serial.println();
}

bool initializeCamera() {
  if (cameraReady) {
    return true;
  }

  camera_config_t config{};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  if (psramFound()) {
    config.frame_size = AITL_FRAME_SIZE;
    config.jpeg_quality = AITL_JPEG_QUALITY;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
    config.fb_location = CAMERA_FB_IN_PSRAM;
  } else {
    Serial.println("PSRAM not detected; falling back to QVGA and one framebuffer.");
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 15;
    config.fb_count = 1;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  const esp_err_t error = esp_camera_init(&config);
  if (error != ESP_OK) {
    Serial.printf("Camera init failed: 0x%04x\n", static_cast<unsigned int>(error));
    cameraReady = false;
    return false;
  }

  sensor_t* sensor = esp_camera_sensor_get();
  if (sensor != nullptr) {
    sensor->set_framesize(sensor, psramFound() ? AITL_FRAME_SIZE : FRAMESIZE_QVGA);
  }

  cameraReady = true;
  Serial.printf(
      "Camera ready: frame_size=%d jpeg_quality=%d psram=%s\n",
      static_cast<int>(psramFound() ? AITL_FRAME_SIZE : FRAMESIZE_QVGA),
      psramFound() ? AITL_JPEG_QUALITY : 15,
      psramFound() ? "yes" : "no");
  return true;
}

void startWifiConnection() {
  if (!deviceConfigReady()) {
    return;
  }

  Serial.printf("Connecting to Wi-Fi: %s\n", AITL_WIFI_SSID);
  WiFi.persistent(false);
  WiFi.mode(WIFI_MODE_NULL);
  WiFi.setHostname(AITL_DEVICE_HOSTNAME);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.setSleep(false);
  WiFi.begin(AITL_WIFI_SSID, AITL_WIFI_PASSWORD);
  lastWifiAttemptMs = millis();
}

void waitForInitialWifiConnection() {
  if (!deviceConfigReady()) {
    return;
  }

  const unsigned long startedAt = millis();
  while (WiFi.status() != WL_CONNECTED &&
         !elapsed(millis(), startedAt, AITL_WIFI_CONNECT_TIMEOUT_MS)) {
    delay(250);
    Serial.print('.');
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("Wi-Fi connected. ESP IP: %s\n", WiFi.localIP().toString().c_str());
    Serial.printf("Receiver: %s\n", receiverUrl().c_str());
    Serial.printf("ESP diagnostics: http://%s/status\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("Initial Wi-Fi connection timed out; background reconnect will continue.");
  }
}

String statusJson() {
  String body;
  body.reserve(420);
  body += "{";
  body += "\"device_id\":\"";
  body += AITL_SOURCE_ID;
  body += "\",\"hostname\":\"";
  body += AITL_DEVICE_HOSTNAME;
  body += "\",\"wifi_connected\":";
  body += WiFi.status() == WL_CONNECTED ? "true" : "false";
  body += ",\"ip\":\"";
  body += WiFi.localIP().toString();
  body += "\",\"rssi_dbm\":";
  body += String(WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0);
  body += ",\"camera_ready\":";
  body += cameraReady ? "true" : "false";
  body += ",\"receiver\":\"";
  body += receiverUrl();
  body += "\",\"uploaded_frames\":";
  body += String(uploadedFrames);
  body += ",\"failed_uploads\":";
  body += String(failedUploads);
  body += ",\"last_http_status\":";
  body += String(lastHttpStatus);
  body += ",\"last_upload_bytes\":";
  body += String(lastUploadBytes);
  body += ",\"last_upload_ms\":";
  body += String(lastUploadDurationMs);
  body += ",\"free_heap_bytes\":";
  body += String(ESP.getFreeHeap());
  body += ",\"uptime_ms\":";
  body += String(millis());
  body += "}";
  return body;
}

void startStatusServer() {
  if (statusServerStarted || WiFi.status() != WL_CONNECTED) {
    return;
  }

  statusServer.on("/", HTTP_GET, []() {
    String text;
    text += "AiTL ESP32-CAM\n";
    text += "Status: /status\n";
    text += "Receiver: ";
    text += receiverUrl();
    text += "\n";
    statusServer.send(200, "text/plain", text);
  });

  statusServer.on("/status", HTTP_GET, []() {
    statusServer.sendHeader("Cache-Control", "no-store");
    statusServer.send(200, "application/json", statusJson());
  });

  statusServer.onNotFound([]() {
    statusServer.send(404, "text/plain", "Not found\n");
  });

  statusServer.begin();
  statusServerStarted = true;
  Serial.printf("ESP status server started on http://%s/status\n", WiFi.localIP().toString().c_str());
}

void maintainWifi() {
  if (!deviceConfigReady()) {
    return;
  }

  if (WiFi.status() == WL_CONNECTED) {
    startStatusServer();
    return;
  }

  const unsigned long now = millis();
  if (!elapsed(now, lastWifiAttemptMs, AITL_WIFI_RETRY_MS)) {
    return;
  }

  Serial.println("Wi-Fi disconnected; reconnecting...");
  WiFi.disconnect();
  WiFi.begin(AITL_WIFI_SSID, AITL_WIFI_PASSWORD);
  lastWifiAttemptMs = now;
}

bool uploadLatestFrame() {
  if (!cameraReady || WiFi.status() != WL_CONNECTED) {
    return false;
  }

  camera_fb_t* frame = esp_camera_fb_get();
  if (frame == nullptr) {
    ++failedUploads;
    lastHttpStatus = 0;
    Serial.println("Camera capture failed: no framebuffer returned.");
    return false;
  }

  if (frame->format != PIXFORMAT_JPEG) {
    ++failedUploads;
    lastHttpStatus = 0;
    Serial.println("Camera capture was not JPEG; frame was discarded.");
    esp_camera_fb_return(frame);
    return false;
  }

  const unsigned long startedAt = millis();
  WiFiClient client;
  HTTPClient http;
  http.setConnectTimeout(AITL_HTTP_TIMEOUT_MS);
  http.setTimeout(AITL_HTTP_TIMEOUT_MS);

  const String url = receiverUrl();
  if (!http.begin(client, url)) {
    ++failedUploads;
    lastHttpStatus = -1;
    Serial.println("HTTP client failed to initialize.");
    esp_camera_fb_return(frame);
    return false;
  }

  http.addHeader("Content-Type", "image/jpeg");
  http.addHeader("X-AiTL-Device", AITL_SOURCE_ID);
  const int status = http.POST(frame->buf, frame->len);
  const size_t frameBytes = frame->len;

  lastUploadDurationMs = millis() - startedAt;
  lastUploadBytes = frameBytes;
  lastHttpStatus = status;

  const bool accepted = status >= 200 && status < 300;
  if (accepted) {
    ++uploadedFrames;
    if (uploadedFrames == 1 || uploadedFrames % 20 == 0) {
      Serial.printf(
          "Frame upload OK: count=%lu bytes=%u http=%d time=%lums\n",
          uploadedFrames,
          static_cast<unsigned int>(frameBytes),
          status,
          lastUploadDurationMs);
    }
  } else {
    ++failedUploads;
    String response;
    if (status > 0) {
      response = http.getString();
      if (response.length() > 240) {
        response = response.substring(0, 240) + "...";
      }
    } else {
      response = HTTPClient::errorToString(status);
    }
    Serial.printf(
        "Frame upload failed: http=%d bytes=%u time=%lums response=%s\n",
        status,
        static_cast<unsigned int>(frameBytes),
        lastUploadDurationMs,
        response.c_str());
  }

  http.end();
  esp_camera_fb_return(frame);
  return accepted;
}

void printPeriodicStatus() {
  const unsigned long now = millis();
  if (!elapsed(now, lastStatusPrintMs, AITL_SERIAL_STATUS_INTERVAL_MS)) {
    return;
  }
  lastStatusPrintMs = now;

  Serial.printf(
      "Status: wifi=%s rssi=%d camera=%s uploaded=%lu failed=%lu last_http=%d heap=%u\n",
      WiFi.status() == WL_CONNECTED ? "connected" : "disconnected",
      WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0,
      cameraReady ? "ready" : "not_ready",
      uploadedFrames,
      failedUploads,
      lastHttpStatus,
      static_cast<unsigned int>(ESP.getFreeHeap()));
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println();
  Serial.println("AiTL ESP32-CAM live frame sender");
  Serial.println("Prototype camera node only; AI inference remains on PC Studio.");

  if (!deviceConfigReady()) {
    printConfigurationHelp();
  }

  lastCameraAttemptMs = millis();
  initializeCamera();

  startWifiConnection();
  waitForInitialWifiConnection();
  startStatusServer();
}

void loop() {
  statusServer.handleClient();
  maintainWifi();

  const unsigned long now = millis();
  if (!cameraReady && elapsed(now, lastCameraAttemptMs, AITL_CAMERA_RETRY_MS)) {
    lastCameraAttemptMs = now;
    initializeCamera();
  }

  if (deviceConfigReady() && cameraReady && WiFi.status() == WL_CONNECTED &&
      elapsed(now, lastFrameAttemptMs, AITL_FRAME_INTERVAL_MS)) {
    uploadLatestFrame();
    lastFrameAttemptMs = millis();
  }

  printPeriodicStatus();
  delay(2);
}
