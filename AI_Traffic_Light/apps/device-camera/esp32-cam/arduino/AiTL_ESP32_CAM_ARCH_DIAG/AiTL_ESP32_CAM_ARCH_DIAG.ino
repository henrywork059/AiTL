// AiTL 0_3_8 R10 camera tuning benchmark firmware.
// DIAGNOSTIC ONLY. Extends the R9 architecture benchmark with controlled
// framebuffer/grab-mode/FPS, JPEG-quality, and TCP write-batching experiments.

#include <Arduino.h>
#include <WebServer.h>
#include <WiFi.h>
#include <esp_camera.h>
#include <esp_heap_caps.h>
#include <esp_http_server.h>
#include <esp_system.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <freertos/task.h>
#include <lwip/sockets.h>
#include <lwip/tcp.h>

#if __has_include("secrets.h")
#include "secrets.h"
#endif
#ifndef AITL_WIFI_SSID
#define AITL_WIFI_SSID "CHANGE_ME"
#endif
#ifndef AITL_WIFI_PASSWORD
#define AITL_WIFI_PASSWORD "CHANGE_ME"
#endif
#ifndef AITL_DEVICE_HOSTNAME
#define AITL_DEVICE_HOSTNAME "aitl-cam-r10-tuning"
#endif

namespace {

constexpr uint16_t CONTROL_PORT = 80;
constexpr uint16_t MANUAL_MJPEG_PORT = 84;
constexpr uint16_t HTTPD_PORT = 85;
constexpr uint16_t RAW_BULK_PORT = 87;
constexpr uint32_t WIFI_TIMEOUT_MS = 20000;
constexpr size_t MAX_BULK_BYTES = 1024U * 1024U;
constexpr size_t MIN_BULK_CHUNK_BYTES = 256;
constexpr size_t MAX_BULK_CHUNK_BYTES = 16384;
constexpr size_t DEFAULT_BULK_CHUNK_BYTES = 1460;
constexpr size_t MAX_CACHE_BYTES = 192U * 1024U;
constexpr char MJPEG_TYPE[] = "multipart/x-mixed-replace;boundary=aitlframe";
constexpr char MJPEG_BOUNDARY[] = "--aitlframe\r\n";

// AI Thinker ESP32-CAM.
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

WebServer controlServer(CONTROL_PORT);
WiFiServer manualServer(MANUAL_MJPEG_PORT, 1);
WiFiServer rawBulkServer(RAW_BULK_PORT, 1);
WiFiClient manualClient;
httpd_handle_t httpdServer = nullptr;

bool cameraReady = false;
bool httpdReady = false;
bool cameraUsesPsram = false;
volatile bool streamBusy = false;
volatile bool cacheCaptureBusy = false;

framesize_t configuredFrameSize = FRAMESIZE_QVGA;
int configuredJpegQuality = 24;
int activeFbCount = 2;
camera_grab_mode_t activeGrabMode = CAMERA_GRAB_LATEST;
camera_fb_location_t activeFbLocation = CAMERA_FB_IN_PSRAM;

uint16_t manualFramesRequested = 8;
uint8_t manualTargetFps = 10;
uint16_t manualFramesSent = 0;
uint32_t manualFailures = 0;
uint32_t manualLastSendMs = 0;
uint32_t manualLastCaptureMs = 0;
uint32_t manualLastBytes = 0;
uint32_t manualNextDueUs = 0;

volatile uint32_t httpdDirectFrames = 0;
volatile uint32_t httpdDirectFailures = 0;
volatile uint32_t httpdDirectLastSendMs = 0;
volatile uint32_t httpdDirectLastCaptureMs = 0;
volatile uint32_t httpdDirectLastBytes = 0;

SemaphoreHandle_t cacheMutex = nullptr;
TaskHandle_t cacheTaskHandle = nullptr;
volatile bool cacheActive = false;
volatile uint8_t cacheTargetFps = 20;
uint8_t* cacheBuffer = nullptr;
size_t cacheCapacity = 0;
size_t cacheLength = 0;
uint32_t cacheSequence = 0;
volatile uint32_t cacheCapturedFrames = 0;
volatile uint32_t cacheCaptureFailures = 0;
volatile uint32_t cacheLastCaptureMs = 0;
volatile uint32_t cacheLastCopyMs = 0;
volatile uint32_t cachedStreamFrames = 0;
volatile uint32_t cachedStreamFailures = 0;
volatile uint32_t cachedLastSendMs = 0;
volatile bool cachedLastCopyInternal = false;

size_t rawBulkBytes = 128U * 1024U;
size_t rawBulkChunkBytes = DEFAULT_BULK_CHUNK_BYTES;
bool rawBulkNoDelay = true;
volatile uint32_t rawBulkLastMs = 0;
volatile uint32_t rawBulkLastAccepted = 0;
volatile uint32_t rawBulkFailures = 0;
volatile uint32_t httpdBulkLastMs = 0;
volatile uint32_t httpdBulkLastAccepted = 0;
volatile uint32_t httpdBulkFailures = 0;

const char* resetReasonName() {
  switch (esp_reset_reason()) {
    case ESP_RST_POWERON: return "poweron";
    case ESP_RST_EXT: return "external";
    case ESP_RST_SW: return "software";
    case ESP_RST_PANIC: return "panic";
    case ESP_RST_INT_WDT: return "interrupt_watchdog";
    case ESP_RST_TASK_WDT: return "task_watchdog";
    case ESP_RST_WDT: return "watchdog";
    case ESP_RST_DEEPSLEEP: return "deep_sleep";
    case ESP_RST_BROWNOUT: return "brownout";
#ifdef ESP_RST_SDIO
    case ESP_RST_SDIO: return "sdio";
#endif
    default: return "unknown";
  }
}

const char* frameSizeName(framesize_t value) {
  switch (value) {
    case FRAMESIZE_QQVGA: return "QQVGA";
    case FRAMESIZE_HQVGA: return "HQVGA";
    case FRAMESIZE_QVGA: return "QVGA";
    case FRAMESIZE_CIF: return "CIF";
    case FRAMESIZE_VGA: return "VGA";
    case FRAMESIZE_SVGA: return "SVGA";
    case FRAMESIZE_XGA: return "XGA";
    case FRAMESIZE_SXGA: return "SXGA";
    case FRAMESIZE_UXGA: return "UXGA";
    default: return "QVGA";
  }
}

bool parseFrameSize(const String& text, framesize_t& out) {
  if (text == "QQVGA") out = FRAMESIZE_QQVGA;
  else if (text == "HQVGA") out = FRAMESIZE_HQVGA;
  else if (text == "QVGA") out = FRAMESIZE_QVGA;
  else if (text == "CIF") out = FRAMESIZE_CIF;
  else if (text == "VGA") out = FRAMESIZE_VGA;
  else if (text == "SVGA") out = FRAMESIZE_SVGA;
  else if (text == "XGA") out = FRAMESIZE_XGA;
  else if (text == "SXGA") out = FRAMESIZE_SXGA;
  else if (text == "UXGA") out = FRAMESIZE_UXGA;
  else return false;
  return true;
}

const char* grabModeName(camera_grab_mode_t mode) {
  return mode == CAMERA_GRAB_LATEST ? "latest" : "when_empty";
}

bool parseGrabMode(const String& value, camera_grab_mode_t& mode) {
  if (value == "latest") {
    mode = CAMERA_GRAB_LATEST;
    return true;
  }
  if (value == "when_empty") {
    mode = CAMERA_GRAB_WHEN_EMPTY;
    return true;
  }
  return false;
}

void configureSocketFd(int fd, bool noDelay) {
  if (fd < 0) return;
  int value = noDelay ? 1 : 0;
  setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &value, sizeof(value));
  int keepAlive = 1;
  setsockopt(fd, SOL_SOCKET, SO_KEEPALIVE, &keepAlive, sizeof(keepAlive));
}

void configureClient(WiFiClient& client, bool noDelay) {
  client.setNoDelay(noDelay);
  configureSocketFd(client.fd(), noDelay);
}

void closeManualClient() {
  if (manualClient) manualClient.stop();
  manualClient = WiFiClient();
}

void sendJson(int code, const String& body) {
  controlServer.sendHeader("Cache-Control", "no-store");
  controlServer.send(code, "application/json", body);
}

bool waitForCacheIdle(uint32_t timeoutMs = 2000) {
  cacheActive = false;
  const uint32_t started = millis();
  while (cacheCaptureBusy && millis() - started < timeoutMs) delay(2);
  return !cacheCaptureBusy;
}

bool applySensorRuntimeSettings() {
  sensor_t* sensor = esp_camera_sensor_get();
  if (!sensor) return false;
  if (sensor->set_framesize(sensor, configuredFrameSize) != 0) return false;
  if (sensor->set_quality(sensor, configuredJpegQuality) != 0) return false;
  return true;
}

bool initCameraMode(int fbCount, camera_grab_mode_t grabMode) {
  if (fbCount < 1 || fbCount > 2) return false;
  if (!waitForCacheIdle()) return false;
  closeManualClient();
  if (streamBusy) return false;

  if (cameraReady) {
    esp_camera_deinit();
    cameraReady = false;
    delay(80);
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

  cameraUsesPsram = psramFound();
  config.frame_size = cameraUsesPsram ? FRAMESIZE_UXGA : configuredFrameSize;
  config.jpeg_quality = cameraUsesPsram ? 10 : 16;
  config.fb_count = cameraUsesPsram ? fbCount : 1;
  config.grab_mode = cameraUsesPsram ? grabMode : CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = cameraUsesPsram ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;

  if (esp_camera_init(&config) != ESP_OK) return false;

  activeFbCount = config.fb_count;
  activeGrabMode = config.grab_mode;
  activeFbLocation = config.fb_location;
  cameraReady = applySensorRuntimeSettings();
  if (!cameraReady) {
    esp_camera_deinit();
    return false;
  }

  // Warm up after re-initialization so the first benchmark sample is not a
  // sensor/config transition artifact.
  for (int index = 0; index < 2; ++index) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (fb) esp_camera_fb_return(fb);
    delay(10);
  }
  return true;
}

String statusJson() {
  String json;
  json.reserve(2800);
  json = "{";
  json += "\"firmware\":\"aitl-0_3_8-r9-architecture-benchmark\"";
  json += ",\"tuning_revision\":\"R10\"";
  json += ",\"camera_ready\":" + String(cameraReady ? "true" : "false");
  json += ",\"httpd_ready\":" + String(httpdReady ? "true" : "false");
  json += ",\"frame_size\":\"" + String(frameSizeName(configuredFrameSize)) + "\"";
  json += ",\"jpeg_quality\":" + String(configuredJpegQuality);
  json += ",\"camera_fb_count\":" + String(activeFbCount);
  json += ",\"camera_grab_mode\":\"" + String(grabModeName(activeGrabMode)) + "\"";
  json += ",\"camera_fb_location\":\"" + String(activeFbLocation == CAMERA_FB_IN_PSRAM ? "psram" : "dram") + "\"";
  json += ",\"stream_busy\":" + String(streamBusy ? "true" : "false");
  json += ",\"cache_active\":" + String(cacheActive ? "true" : "false");
  json += ",\"cache_target_fps\":" + String(cacheTargetFps);
  json += ",\"cache_sequence\":" + String(cacheSequence);
  json += ",\"cache_bytes\":" + String(cacheLength);
  json += ",\"cache_captured_frames\":" + String(cacheCapturedFrames);
  json += ",\"cache_capture_failures\":" + String(cacheCaptureFailures);
  json += ",\"cache_last_capture_ms\":" + String(cacheLastCaptureMs);
  json += ",\"cache_last_copy_ms\":" + String(cacheLastCopyMs);
  json += ",\"cached_stream_frames\":" + String(cachedStreamFrames);
  json += ",\"cached_stream_failures\":" + String(cachedStreamFailures);
  json += ",\"cached_last_send_ms\":" + String(cachedLastSendMs);
  json += ",\"cached_last_copy_internal\":" + String(cachedLastCopyInternal ? "true" : "false");
  json += ",\"httpd_direct_frames\":" + String(httpdDirectFrames);
  json += ",\"httpd_direct_failures\":" + String(httpdDirectFailures);
  json += ",\"httpd_direct_last_send_ms\":" + String(httpdDirectLastSendMs);
  json += ",\"httpd_direct_last_capture_ms\":" + String(httpdDirectLastCaptureMs);
  json += ",\"httpd_direct_last_bytes\":" + String(httpdDirectLastBytes);
  json += ",\"raw_bulk_bytes\":" + String(rawBulkBytes);
  json += ",\"raw_bulk_chunk_bytes\":" + String(rawBulkChunkBytes);
  json += ",\"raw_bulk_nodelay\":" + String(rawBulkNoDelay ? "true" : "false");
  json += ",\"raw_bulk_last_ms\":" + String(rawBulkLastMs);
  json += ",\"raw_bulk_last_accepted\":" + String(rawBulkLastAccepted);
  json += ",\"raw_bulk_failures\":" + String(rawBulkFailures);
  json += ",\"httpd_bulk_last_ms\":" + String(httpdBulkLastMs);
  json += ",\"httpd_bulk_last_accepted\":" + String(httpdBulkLastAccepted);
  json += ",\"httpd_bulk_failures\":" + String(httpdBulkFailures);
  json += ",\"reset_reason\":\"" + String(resetReasonName()) + "\"";
  json += ",\"rssi\":" + String(WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : -127);
  json += ",\"bssid\":\"" + String(WiFi.status() == WL_CONNECTED ? WiFi.BSSIDstr() : "offline") + "\"";
  json += ",\"channel\":" + String(WiFi.status() == WL_CONNECTED ? WiFi.channel() : -1);
  json += ",\"free_heap\":" + String(ESP.getFreeHeap());
  json += ",\"internal_free\":" + String(heap_caps_get_free_size(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT));
  json += ",\"internal_largest\":" + String(heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT));
  json += ",\"psram_free\":" + String(ESP.getFreePsram());
  json += ",\"uptime_ms\":" + String(millis());
  json += "}";
  return json;
}

void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setAutoReconnect(true);
  WiFi.setHostname(AITL_DEVICE_HOSTNAME);
  WiFi.begin(AITL_WIFI_SSID, AITL_WIFI_PASSWORD);
  const uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < WIFI_TIMEOUT_MS) delay(100);
}

bool ensureCacheCapacity(size_t wanted) {
  if (wanted == 0 || wanted > MAX_CACHE_BYTES) return false;
  if (cacheBuffer && cacheCapacity >= wanted) return true;
  const uint32_t caps = cameraUsesPsram
      ? (MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT)
      : (MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
  uint8_t* next = static_cast<uint8_t*>(heap_caps_malloc(wanted, caps));
  if (!next) return false;
  if (cacheBuffer) heap_caps_free(cacheBuffer);
  cacheBuffer = next;
  cacheCapacity = wanted;
  return true;
}

void cacheCaptureTask(void*) {
  while (true) {
    if (!cacheActive || !cameraReady || !cacheMutex) {
      vTaskDelay(pdMS_TO_TICKS(10));
      continue;
    }
    cacheCaptureBusy = true;
    const uint32_t cycleStarted = millis();
    const uint32_t captureStarted = millis();
    camera_fb_t* fb = esp_camera_fb_get();
    cacheLastCaptureMs = millis() - captureStarted;
    if (!fb) {
      ++cacheCaptureFailures;
      cacheCaptureBusy = false;
      vTaskDelay(pdMS_TO_TICKS(5));
      continue;
    }

    const uint32_t copyStarted = millis();
    if (xSemaphoreTake(cacheMutex, pdMS_TO_TICKS(50)) == pdTRUE) {
      if (ensureCacheCapacity(fb->len)) {
        memcpy(cacheBuffer, fb->buf, fb->len);
        cacheLength = fb->len;
        ++cacheSequence;
        ++cacheCapturedFrames;
      } else {
        ++cacheCaptureFailures;
      }
      xSemaphoreGive(cacheMutex);
    } else {
      ++cacheCaptureFailures;
    }
    cacheLastCopyMs = millis() - copyStarted;
    esp_camera_fb_return(fb);
    cacheCaptureBusy = false;

    const uint32_t fps = cacheTargetFps > 0 ? static_cast<uint32_t>(cacheTargetFps) : 1U;
    const uint32_t periodMs = 1000U / fps;
    const uint32_t elapsed = millis() - cycleStarted;
    if (elapsed < periodMs) vTaskDelay(pdMS_TO_TICKS(periodMs - elapsed));
    else taskYIELD();
  }
}

bool readHttpdInt(httpd_req_t* req, const char* key, int fallback, int minimum, int maximum, int& out) {
  out = fallback;
  const size_t length = httpd_req_get_url_query_len(req);
  if (!length) return true;
  char* query = static_cast<char*>(malloc(length + 1));
  if (!query) return false;
  bool ok = true;
  if (httpd_req_get_url_query_str(req, query, length + 1) == ESP_OK) {
    char value[24]{};
    if (httpd_query_key_value(query, key, value, sizeof(value)) == ESP_OK) {
      const int parsed = atoi(value);
      if (parsed < minimum || parsed > maximum) ok = false;
      else out = parsed;
    }
  }
  free(query);
  return ok;
}

esp_err_t sendMjpegPart(httpd_req_t* req, const uint8_t* data, size_t length, uint32_t& sendMs) {
  char header[128];
  const int headerLength = snprintf(
      header,
      sizeof(header),
      "%sContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
      MJPEG_BOUNDARY,
      static_cast<unsigned int>(length));
  const uint32_t started = millis();
  esp_err_t result = httpd_resp_send_chunk(req, header, headerLength);
  if (result == ESP_OK) {
    result = httpd_resp_send_chunk(req, reinterpret_cast<const char*>(data), length);
  }
  if (result == ESP_OK) result = httpd_resp_send_chunk(req, "\r\n", 2);
  sendMs = millis() - started;
  return result;
}

esp_err_t httpdDirectHandler(httpd_req_t* req) {
  if (!cameraReady || cacheActive || streamBusy) {
    httpd_resp_set_status(req, "409 Conflict");
    return httpd_resp_sendstr(req, "camera busy or unavailable");
  }

  int frames = 5;
  int fps = 10;
  if (!readHttpdInt(req, "frames", 5, 1, 50, frames)
      || !readHttpdInt(req, "fps", 10, 1, 30, fps)) {
    httpd_resp_set_status(req, "422 Unprocessable Entity");
    return httpd_resp_sendstr(req, "invalid query");
  }

  streamBusy = true;
  httpdDirectFrames = 0;
  httpdDirectFailures = 0;
  httpd_resp_set_type(req, MJPEG_TYPE);
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");
  const uint32_t periodMs = 1000U / static_cast<uint32_t>(fps);
  uint32_t nextDue = millis();

  for (int index = 0; index < frames; ++index) {
    while (static_cast<int32_t>(millis() - nextDue) < 0) vTaskDelay(pdMS_TO_TICKS(1));
    nextDue += periodMs;
    const uint32_t captureStarted = millis();
    camera_fb_t* fb = esp_camera_fb_get();
    httpdDirectLastCaptureMs = millis() - captureStarted;
    if (!fb) {
      ++httpdDirectFailures;
      break;
    }
    httpdDirectLastBytes = fb->len;
    uint32_t sendMs = 0;
    const esp_err_t result = sendMjpegPart(req, fb->buf, fb->len, sendMs);
    httpdDirectLastSendMs = sendMs;
    esp_camera_fb_return(fb);
    if (result != ESP_OK) {
      ++httpdDirectFailures;
      break;
    }
    ++httpdDirectFrames;
  }

  httpd_resp_send_chunk(req, nullptr, 0);
  streamBusy = false;
  return ESP_OK;
}

esp_err_t httpdCachedHandler(httpd_req_t* req) {
  if (!cameraReady || !cacheActive || !cacheMutex || streamBusy) {
    httpd_resp_set_status(req, "409 Conflict");
    return httpd_resp_sendstr(req, "cache unavailable or busy");
  }

  int frames = 5;
  int fps = 10;
  if (!readHttpdInt(req, "frames", 5, 1, 50, frames)
      || !readHttpdInt(req, "fps", 10, 1, 30, fps)) {
    httpd_resp_set_status(req, "422 Unprocessable Entity");
    return httpd_resp_sendstr(req, "invalid query");
  }

  streamBusy = true;
  cachedStreamFrames = 0;
  cachedStreamFailures = 0;
  httpd_resp_set_type(req, MJPEG_TYPE);
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");
  const uint32_t periodMs = 1000U / static_cast<uint32_t>(fps);
  uint32_t nextDue = millis();
  uint32_t lastSequence = 0;

  for (int index = 0; index < frames; ++index) {
    while (static_cast<int32_t>(millis() - nextDue) < 0) vTaskDelay(pdMS_TO_TICKS(1));
    nextDue += periodMs;

    uint8_t* copy = nullptr;
    size_t length = 0;
    uint32_t sequence = 0;
    const uint32_t waitStarted = millis();

    while (millis() - waitStarted < 2500U) {
      if (xSemaphoreTake(cacheMutex, pdMS_TO_TICKS(50)) == pdTRUE) {
        sequence = cacheSequence;
        length = cacheLength;
        if (sequence != lastSequence && length > 0) {
          copy = static_cast<uint8_t*>(
              heap_caps_malloc(length, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT));
          cachedLastCopyInternal = copy != nullptr;
          if (!copy && cameraUsesPsram) {
            copy = static_cast<uint8_t*>(
                heap_caps_malloc(length, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
          }
          if (copy) memcpy(copy, cacheBuffer, length);
        }
        xSemaphoreGive(cacheMutex);
      }
      if (copy) break;
      vTaskDelay(pdMS_TO_TICKS(2));
    }

    if (!copy) {
      ++cachedStreamFailures;
      break;
    }

    lastSequence = sequence;
    uint32_t sendMs = 0;
    const esp_err_t result = sendMjpegPart(req, copy, length, sendMs);
    cachedLastSendMs = sendMs;
    heap_caps_free(copy);
    if (result != ESP_OK) {
      ++cachedStreamFailures;
      break;
    }
    ++cachedStreamFrames;
  }

  httpd_resp_send_chunk(req, nullptr, 0);
  streamBusy = false;
  return ESP_OK;
}

esp_err_t httpdBulkHandler(httpd_req_t* req) {
  int bytes = 128 * 1024;
  int chunk = static_cast<int>(DEFAULT_BULK_CHUNK_BYTES);
  if (!readHttpdInt(req, "bytes", bytes, 4096, static_cast<int>(MAX_BULK_BYTES), bytes)
      || !readHttpdInt(req, "chunk", chunk, static_cast<int>(MIN_BULK_CHUNK_BYTES),
                       static_cast<int>(MAX_BULK_CHUNK_BYTES), chunk)) {
    httpd_resp_set_status(req, "422 Unprocessable Entity");
    return httpd_resp_sendstr(req, "invalid bulk query");
  }

  uint8_t* buffer = static_cast<uint8_t*>(
      heap_caps_malloc(static_cast<size_t>(chunk), MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT));
  if (!buffer) {
    ++httpdBulkFailures;
    httpd_resp_set_status(req, "503 Service Unavailable");
    return httpd_resp_sendstr(req, "no internal bulk buffer");
  }
  memset(buffer, 0xA5, static_cast<size_t>(chunk));

  httpd_resp_set_type(req, "application/octet-stream");
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");
  httpdBulkLastAccepted = 0;
  const uint32_t started = millis();
  esp_err_t result = ESP_OK;
  while (httpdBulkLastAccepted < static_cast<uint32_t>(bytes)) {
    const size_t remain = static_cast<size_t>(bytes) - httpdBulkLastAccepted;
    const size_t count = remain < static_cast<size_t>(chunk) ? remain : static_cast<size_t>(chunk);
    result = httpd_resp_send_chunk(req, reinterpret_cast<const char*>(buffer), count);
    if (result != ESP_OK) break;
    httpdBulkLastAccepted += count;
  }
  httpdBulkLastMs = millis() - started;
  if (result != ESP_OK) ++httpdBulkFailures;
  heap_caps_free(buffer);
  if (result == ESP_OK) httpd_resp_send_chunk(req, nullptr, 0);
  return result;
}

esp_err_t httpdOpen(httpd_handle_t, int sockfd) {
  configureSocketFd(sockfd, true);
  return ESP_OK;
}

bool startHttpd() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = HTTPD_PORT;
  config.ctrl_port = 32770;
  config.max_uri_handlers = 8;
  config.send_wait_timeout = 8;
  config.recv_wait_timeout = 8;
  config.keep_alive_enable = true;
  config.open_fn = httpdOpen;
  if (httpd_start(&httpdServer, &config) != ESP_OK) return false;

  httpd_uri_t direct{};
  direct.uri = "/direct.mjpeg";
  direct.method = HTTP_GET;
  direct.handler = httpdDirectHandler;
  httpd_register_uri_handler(httpdServer, &direct);

  httpd_uri_t cached{};
  cached.uri = "/cached.mjpeg";
  cached.method = HTTP_GET;
  cached.handler = httpdCachedHandler;
  httpd_register_uri_handler(httpdServer, &cached);

  httpd_uri_t bulk{};
  bulk.uri = "/bulk.bin";
  bulk.method = HTTP_GET;
  bulk.handler = httpdBulkHandler;
  httpd_register_uri_handler(httpdServer, &bulk);
  return true;
}

void handleConfig() {
  if (cacheActive || streamBusy || (manualClient && manualClient.connected())) {
    sendJson(409, "{\"error\":\"busy\"}");
    return;
  }
  sensor_t* sensor = esp_camera_sensor_get();
  if (!sensor) {
    sendJson(503, "{\"error\":\"camera_not_ready\"}");
    return;
  }

  if (controlServer.hasArg("frame_size")) {
    framesize_t next;
    if (!parseFrameSize(controlServer.arg("frame_size"), next)
        || sensor->set_framesize(sensor, next) != 0) {
      sendJson(422, "{\"error\":\"invalid_frame_size\"}");
      return;
    }
    configuredFrameSize = next;
  }

  if (controlServer.hasArg("jpeg_quality")) {
    const int quality = controlServer.arg("jpeg_quality").toInt();
    if (quality < 4 || quality > 63 || sensor->set_quality(sensor, quality) != 0) {
      sendJson(422, "{\"error\":\"invalid_jpeg_quality\"}");
      return;
    }
    configuredJpegQuality = quality;
  }
  sendJson(200, statusJson());
}

void handleCameraReinit() {
  if (streamBusy) {
    sendJson(409, "{\"error\":\"stream_busy\"}");
    return;
  }
  const int fbCount = controlServer.hasArg("fb_count") ? controlServer.arg("fb_count").toInt() : activeFbCount;
  camera_grab_mode_t grabMode = activeGrabMode;
  if (controlServer.hasArg("grab") && !parseGrabMode(controlServer.arg("grab"), grabMode)) {
    sendJson(422, "{\"error\":\"invalid_grab_mode\"}");
    return;
  }
  if (fbCount < 1 || fbCount > 2) {
    sendJson(422, "{\"error\":\"invalid_fb_count\"}");
    return;
  }
  if (!initCameraMode(fbCount, grabMode)) {
    sendJson(503, "{\"error\":\"camera_reinit_failed\"}");
    return;
  }
  sendJson(200, statusJson());
}

void handleCapture() {
  if (!cameraReady || cacheActive || streamBusy || (manualClient && manualClient.connected())) {
    controlServer.send(409, "text/plain", "camera busy or not ready");
    return;
  }
  const uint32_t started = millis();
  camera_fb_t* fb = esp_camera_fb_get();
  manualLastCaptureMs = millis() - started;
  if (!fb) {
    controlServer.send(503, "text/plain", "capture failed");
    return;
  }
  controlServer.sendHeader("Cache-Control", "no-store");
  controlServer.setContentLength(fb->len);
  controlServer.send(200, "image/jpeg", "");
  WiFiClient client = controlServer.client();
  configureClient(client, true);
  client.write(fb->buf, fb->len);
  esp_camera_fb_return(fb);
}

void handleManualConfig() {
  if (manualClient && manualClient.connected()) {
    sendJson(409, "{\"error\":\"manual_active\"}");
    return;
  }
  const int frames = controlServer.hasArg("frames") ? controlServer.arg("frames").toInt() : 8;
  const int fps = controlServer.hasArg("fps") ? controlServer.arg("fps").toInt() : 10;
  if (frames < 1 || frames > 50 || fps < 1 || fps > 30) {
    sendJson(422, "{\"error\":\"invalid_manual_config\"}");
    return;
  }
  manualFramesRequested = static_cast<uint16_t>(frames);
  manualTargetFps = static_cast<uint8_t>(fps);
  manualFramesSent = 0;
  manualFailures = 0;
  manualLastSendMs = 0;
  sendJson(200, statusJson());
}

void handleCacheStart() {
  if (!cacheMutex || !cameraReady || streamBusy) {
    sendJson(503, "{\"error\":\"cache_unavailable\"}");
    return;
  }
  const int fps = controlServer.hasArg("fps") ? controlServer.arg("fps").toInt() : 20;
  if (fps < 1 || fps > 30) {
    sendJson(422, "{\"error\":\"invalid_cache_fps\"}");
    return;
  }
  closeManualClient();
  cacheTargetFps = static_cast<uint8_t>(fps);
  cacheCapturedFrames = 0;
  cacheCaptureFailures = 0;
  cachedStreamFrames = 0;
  cachedStreamFailures = 0;
  if (xSemaphoreTake(cacheMutex, pdMS_TO_TICKS(100)) == pdTRUE) {
    cacheLength = 0;
    cacheSequence = 0;
    xSemaphoreGive(cacheMutex);
  }
  cacheActive = true;
  sendJson(200, statusJson());
}

void handleCacheStop() {
  const bool idle = waitForCacheIdle();
  sendJson(idle ? 200 : 503, idle ? statusJson() : "{\"error\":\"cache_stop_timeout\"}");
}

void handleBulkConfig() {
  const int bytes = controlServer.hasArg("bytes")
      ? controlServer.arg("bytes").toInt()
      : static_cast<int>(128U * 1024U);
  const int chunk = controlServer.hasArg("chunk")
      ? controlServer.arg("chunk").toInt()
      : static_cast<int>(DEFAULT_BULK_CHUNK_BYTES);

  if (bytes < 4096 || bytes > static_cast<int>(MAX_BULK_BYTES)
      || chunk < static_cast<int>(MIN_BULK_CHUNK_BYTES)
      || chunk > static_cast<int>(MAX_BULK_CHUNK_BYTES)) {
    sendJson(422, "{\"error\":\"invalid_bulk_config\"}");
    return;
  }

  rawBulkBytes = static_cast<size_t>(bytes);
  rawBulkChunkBytes = static_cast<size_t>(chunk);
  rawBulkNoDelay = !controlServer.hasArg("nodelay") || controlServer.arg("nodelay") != "0";
  rawBulkLastMs = 0;
  rawBulkLastAccepted = 0;
  rawBulkFailures = 0;
  sendJson(200, statusJson());
}

void acceptManualClient() {
  if (cacheActive || streamBusy || (manualClient && manualClient.connected())) return;
  WiFiClient candidate = manualServer.accept();
  if (!candidate) return;
  configureClient(candidate, true);
  candidate.setTimeout(500);
  const uint32_t deadline = millis() + 800U;
  while (candidate.connected() && millis() < deadline) {
    if (!candidate.available()) {
      delay(1);
      continue;
    }
    const String line = candidate.readStringUntil('\n');
    if (line == "\r" || line.length() == 0) break;
  }
  candidate.print(
      "HTTP/1.1 200 OK\r\n"
      "Content-Type: multipart/x-mixed-replace; boundary=aitlframe\r\n"
      "Cache-Control: no-store\r\n"
      "Connection: close\r\n\r\n");
  manualClient = candidate;
  manualFramesSent = 0;
  manualFailures = 0;
  manualNextDueUs = micros();
}

void sendManualFrameIfDue() {
  if (!(manualClient && manualClient.connected()) || cacheActive || streamBusy) return;
  if (manualFramesSent >= manualFramesRequested) {
    manualClient.print("--aitlframe--\r\n");
    closeManualClient();
    return;
  }

  const uint32_t nowUs = micros();
  if (static_cast<int32_t>(nowUs - manualNextDueUs) < 0) return;
  const uint32_t fps = manualTargetFps > 0 ? static_cast<uint32_t>(manualTargetFps) : 1U;
  manualNextDueUs += 1000000UL / fps;

  const uint32_t captureStarted = millis();
  camera_fb_t* fb = esp_camera_fb_get();
  manualLastCaptureMs = millis() - captureStarted;
  if (!fb) {
    ++manualFailures;
    closeManualClient();
    return;
  }

  manualLastBytes = fb->len;
  const uint32_t sendStarted = millis();
  manualClient.printf(
      "--aitlframe\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
      static_cast<unsigned int>(fb->len));
  const size_t written = manualClient.write(fb->buf, fb->len);
  manualClient.print("\r\n");
  manualLastSendMs = millis() - sendStarted;
  esp_camera_fb_return(fb);

  if (written != manualLastBytes) {
    ++manualFailures;
    closeManualClient();
    return;
  }
  ++manualFramesSent;
}

void handleRawBulkClient() {
  WiFiClient client = rawBulkServer.accept();
  if (!client) return;
  configureClient(client, rawBulkNoDelay);

  uint8_t* buffer = static_cast<uint8_t*>(
      heap_caps_malloc(rawBulkChunkBytes, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT));
  if (!buffer) {
    ++rawBulkFailures;
    client.stop();
    return;
  }
  memset(buffer, 0x5A, rawBulkChunkBytes);

  rawBulkLastAccepted = 0;
  const uint32_t started = millis();
  bool ok = true;
  while (rawBulkLastAccepted < rawBulkBytes && client.connected()) {
    const size_t remain = rawBulkBytes - rawBulkLastAccepted;
    const size_t count = remain < rawBulkChunkBytes ? remain : rawBulkChunkBytes;
    const size_t written = client.write(buffer, count);
    if (written == 0) {
      ok = false;
      break;
    }
    rawBulkLastAccepted += written;
  }
  rawBulkLastMs = millis() - started;
  if (!ok || rawBulkLastAccepted != rawBulkBytes) ++rawBulkFailures;
  heap_caps_free(buffer);
  client.stop();
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(50);
  Serial.println();
  Serial.println("AiTL 0_3_8 R10 camera tuning benchmark");

  cameraUsesPsram = psramFound();
  activeFbCount = cameraUsesPsram ? 2 : 1;
  activeGrabMode = cameraUsesPsram ? CAMERA_GRAB_LATEST : CAMERA_GRAB_WHEN_EMPTY;
  activeFbLocation = cameraUsesPsram ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
  cameraReady = initCameraMode(activeFbCount, activeGrabMode);

  cacheMutex = xSemaphoreCreateMutex();
  if (cacheMutex) {
    xTaskCreatePinnedToCore(cacheCaptureTask, "aitl-cache", 4096, nullptr, 1, &cacheTaskHandle, 1);
  }

  connectWifi();

  controlServer.on("/status", HTTP_GET, [](){ sendJson(200, statusJson()); });
  controlServer.on("/config", HTTP_POST, handleConfig);
  controlServer.on("/camera/reinit", HTTP_POST, handleCameraReinit);
  controlServer.on("/capture", HTTP_GET, handleCapture);
  controlServer.on("/manual/config", HTTP_POST, handleManualConfig);
  controlServer.on("/cache/start", HTTP_POST, handleCacheStart);
  controlServer.on("/cache/stop", HTTP_POST, handleCacheStop);
  controlServer.on("/bulk/config", HTTP_POST, handleBulkConfig);
  controlServer.onNotFound([](){ sendJson(404, "{\"error\":\"not_found\"}"); });
  controlServer.begin();

  manualServer.begin();
  manualServer.setNoDelay(true);
  rawBulkServer.begin();
  httpdReady = startHttpd();

  Serial.printf(
      "Camera ready: %s | HTTPD ready: %s | PSRAM: %s | FB: %d | grab: %s\n",
      cameraReady ? "yes" : "no",
      httpdReady ? "yes" : "no",
      cameraUsesPsram ? "yes" : "no",
      activeFbCount,
      grabModeName(activeGrabMode));

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("ESP IP: %s\n", WiFi.localIP().toString().c_str());
    Serial.printf("Control: http://%s:%u/status\n", WiFi.localIP().toString().c_str(), CONTROL_PORT);
    Serial.printf("HTTPD direct: http://%s:%u/direct.mjpeg\n", WiFi.localIP().toString().c_str(), HTTPD_PORT);
    Serial.printf("HTTPD cached: http://%s:%u/cached.mjpeg\n", WiFi.localIP().toString().c_str(), HTTPD_PORT);
    Serial.printf("HTTPD bulk: http://%s:%u/bulk.bin\n", WiFi.localIP().toString().c_str(), HTTPD_PORT);
    Serial.printf("Raw bulk: tcp://%s:%u\n", WiFi.localIP().toString().c_str(), RAW_BULK_PORT);
  }
}

void loop() {
  controlServer.handleClient();
  if (WiFi.status() == WL_CONNECTED) {
    acceptManualClient();
    sendManualFrameIfDue();
    handleRawBulkClient();
  }
  delay(1);
}
