// AiTL 0_3_8 R3 transport-isolation firmware.
// DIAGNOSTIC-ONLY: flash temporarily to isolate camera/PSRAM/TCP/MJPEG behavior.
// It does not replace the normal AiTL V037 production firmware.

#include <Arduino.h>
#include <errno.h>
#include <sys/uio.h>
#include <WebServer.h>
#include <WiFi.h>
#include <esp_camera.h>
#include <esp_heap_caps.h>
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
#define AITL_DEVICE_HOSTNAME "aitl-cam-diag"
#endif

namespace {

constexpr uint16_t CONTROL_PORT = 80;
constexpr uint16_t ATL1_PORT = 81;
constexpr uint32_t WIFI_TIMEOUT_MS = 20000;
constexpr uint32_t SELECT_SLICE_MS = 20;
constexpr size_t ATL1_HEADER_BYTES = 16;
constexpr size_t MAX_SYNTHETIC_BYTES = 32768;
constexpr size_t MAX_TRACE_POINTS = 24;
constexpr uint8_t ATL1_MAGIC[4] = {'A','T','L','1'};

// AI Thinker ESP32-CAM pin map.
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

enum class TransportMode : uint8_t { Direct, Staged, DramCopy, Synthetic };

WebServer controlServer(CONTROL_PORT);
WiFiServer atl1Server(ATL1_PORT, 1);
WiFiClient atl1Client;
TransportMode mode = TransportMode::Direct;
bool cameraReady = false;
bool streaming = false;
uint8_t targetFps = 5;
uint32_t nextFrameDueUs = 0;
uint32_t sequenceNumber = 0;
uint32_t stallTimeoutMs = 1200;
uint32_t totalSendLimitMs = 2000;
size_t chunkBytes = 1460;
size_t syntheticBytes = 6000;
uint8_t* stageBuffer = nullptr;
size_t stageCapacity = 0;
uint8_t* syntheticBuffer = nullptr;
size_t syntheticCapacity = 0;

uint32_t frameCount = 0;
uint32_t sendFailures = 0;
uint32_t deadlineDrops = 0;
uint32_t lastFrameBytes = 0;
uint32_t lastCaptureMs = 0;
uint32_t lastSendMs = 0;
uint32_t lastAcceptedBytes = 0;
int lastErrno = 0;
uint32_t lastTraceBytes[MAX_TRACE_POINTS]{};
uint32_t lastTraceMs[MAX_TRACE_POINTS]{};
size_t lastTraceCount = 0;

const char* modeName() {
  switch (mode) {
    case TransportMode::Staged: return "staged";
    case TransportMode::DramCopy: return "dram_copy";
    case TransportMode::Synthetic: return "synthetic";
    default: return "direct";
  }
}

void putU32be(uint8_t* out, uint32_t value) {
  out[0] = static_cast<uint8_t>((value >> 24) & 0xFF);
  out[1] = static_cast<uint8_t>((value >> 16) & 0xFF);
  out[2] = static_cast<uint8_t>((value >> 8) & 0xFF);
  out[3] = static_cast<uint8_t>(value & 0xFF);
}

void resetTrace() { lastTraceCount = 0; }

void recordTrace(size_t accepted, uint32_t startedMs) {
  if (lastTraceCount >= MAX_TRACE_POINTS) return;
  if (lastTraceCount > 0 && lastTraceBytes[lastTraceCount - 1] == accepted) return;
  lastTraceBytes[lastTraceCount] = static_cast<uint32_t>(accepted);
  lastTraceMs[lastTraceCount] = millis() - startedMs;
  ++lastTraceCount;
}

bool ensureInternalBuffer(uint8_t*& buffer, size_t& capacity, size_t wanted) {
  if (wanted == 0) return false;
  if (buffer && capacity >= wanted) return true;
  if (buffer) heap_caps_free(buffer);
  buffer = static_cast<uint8_t*>(heap_caps_malloc(wanted, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT));
  if (!buffer) { capacity = 0; return false; }
  capacity = wanted;
  return true;
}

void closeAtl1Client() {
  if (atl1Client) atl1Client.stop();
  atl1Client = WiFiClient();
}

bool waitWritable(int fd, uint32_t startedMs, uint32_t progressMs) {
  while (true) {
    const uint32_t now = millis();
    if (now - startedMs >= totalSendLimitMs || now - progressMs >= stallTimeoutMs) return false;
    uint32_t waitMs = SELECT_SLICE_MS;
    const uint32_t totalRemain = totalSendLimitMs - (now - startedMs);
    const uint32_t stallRemain = stallTimeoutMs - (now - progressMs);
    if (totalRemain < waitMs) waitMs = totalRemain;
    if (stallRemain < waitMs) waitMs = stallRemain;
    if (waitMs == 0) return false;
    fd_set writes;
    FD_ZERO(&writes);
    FD_SET(fd, &writes);
    timeval timeout{};
    timeout.tv_sec = waitMs / 1000U;
    timeout.tv_usec = (waitMs % 1000U) * 1000U;
    const int ready = select(fd + 1, nullptr, &writes, nullptr, &timeout);
    if (ready > 0) return FD_ISSET(fd, &writes);
    if (ready == 0) { delay(1); continue; }
    if (errno == EINTR) continue;
    return false;
  }
}

bool sendBytesBounded(int fd, const uint8_t* data, size_t length, uint32_t startedMs,
                      size_t& accepted, int& terminalErrno) {
  size_t offset = 0;
  uint32_t lastProgress = millis();
  while (offset < length) {
    const uint32_t now = millis();
    if (now - startedMs >= totalSendLimitMs || now - lastProgress >= stallTimeoutMs) {
      terminalErrno = ETIMEDOUT;
      return false;
    }
    const int result = ::send(fd, data + offset, length - offset, MSG_DONTWAIT);
    if (result > 0) {
      offset += static_cast<size_t>(result);
      accepted += static_cast<size_t>(result);
      lastProgress = millis();
      recordTrace(accepted, startedMs);
      delay(1);
      continue;
    }
    if (result == 0) { terminalErrno = ECONNRESET; return false; }
    if (errno == EINTR) continue;
    if (errno == EAGAIN || errno == EWOULDBLOCK) {
      if (!waitWritable(fd, startedMs, lastProgress)) { terminalErrno = ETIMEDOUT; return false; }
      continue;
    }
    terminalErrno = errno;
    return false;
  }
  return true;
}

bool sendVectoredBounded(int fd, const uint8_t* header, size_t headerLength,
                         const uint8_t* payload, size_t payloadLength, uint32_t startedMs,
                         size_t& accepted, int& terminalErrno) {
  const size_t total = headerLength + payloadLength;
  size_t sent = 0;
  uint32_t lastProgress = millis();
  while (sent < total) {
    const uint32_t now = millis();
    if (now - startedMs >= totalSendLimitMs || now - lastProgress >= stallTimeoutMs) {
      terminalErrno = ETIMEDOUT;
      return false;
    }
    iovec vectors[2]{};
    int count = 0;
    if (sent < headerLength) {
      vectors[count].iov_base = const_cast<uint8_t*>(header + sent);
      vectors[count].iov_len = headerLength - sent;
      ++count;
      vectors[count].iov_base = const_cast<uint8_t*>(payload);
      vectors[count].iov_len = payloadLength;
      ++count;
    } else {
      const size_t payloadOffset = sent - headerLength;
      vectors[0].iov_base = const_cast<uint8_t*>(payload + payloadOffset);
      vectors[0].iov_len = payloadLength - payloadOffset;
      count = 1;
    }
    msghdr message{};
    message.msg_iov = vectors;
    message.msg_iovlen = count;
    const int result = ::sendmsg(fd, &message, MSG_DONTWAIT);
    if (result > 0) {
      sent += static_cast<size_t>(result);
      accepted = sent;
      lastProgress = millis();
      recordTrace(accepted, startedMs);
      delay(1);
      continue;
    }
    if (result == 0) { terminalErrno = ECONNRESET; return false; }
    if (errno == EINTR) continue;
    if (errno == EAGAIN || errno == EWOULDBLOCK) {
      if (!waitWritable(fd, startedMs, lastProgress)) { terminalErrno = ETIMEDOUT; return false; }
      continue;
    }
    terminalErrno = errno;
    return false;
  }
  return true;
}

bool sendAtl1Frame(const uint8_t* payload, size_t payloadLength, bool staged) {
  const int fd = atl1Client.fd();
  if (fd < 0) { lastErrno = EBADF; return false; }
  uint8_t header[ATL1_HEADER_BYTES];
  memcpy(header, ATL1_MAGIC, 4);
  putU32be(header + 4, static_cast<uint32_t>(payloadLength));
  putU32be(header + 8, ++sequenceNumber);
  putU32be(header + 12, millis());
  const uint32_t started = millis();
  size_t accepted = 0;
  int terminalErrno = 0;
  resetTrace();
  bool ok = false;
  if (!staged) {
    ok = sendVectoredBounded(fd, header, sizeof(header), payload, payloadLength, started, accepted, terminalErrno);
  } else {
    if (!ensureInternalBuffer(stageBuffer, stageCapacity, chunkBytes)) {
      lastErrno = ENOMEM;
      return false;
    }
    ok = sendBytesBounded(fd, header, sizeof(header), started, accepted, terminalErrno);
    if (ok) {
      for (size_t offset = 0; offset < payloadLength && ok; offset += chunkBytes) {
        const size_t n = min(chunkBytes, payloadLength - offset);
        memcpy(stageBuffer, payload + offset, n);
        ok = sendBytesBounded(fd, stageBuffer, n, started, accepted, terminalErrno);
      }
    }
  }
  lastSendMs = millis() - started;
  lastAcceptedBytes = static_cast<uint32_t>(accepted);
  lastErrno = terminalErrno;
  if (!ok) {
    ++sendFailures;
    if (terminalErrno == ETIMEDOUT) ++deadlineDrops;
  } else {
    ++frameCount;
  }
  return ok;
}

String statusJson() {
  String json = "{";
  json += "\"firmware\":\"aitl-0_3_8-r3-transport-diag\"";
  json += ",\"camera_ready\":" + String(cameraReady ? "true" : "false");
  json += ",\"streaming\":" + String(streaming ? "true" : "false");
  json += ",\"mode\":\"" + String(modeName()) + "\"";
  json += ",\"target_fps\":" + String(targetFps);
  json += ",\"stall_timeout_ms\":" + String(stallTimeoutMs);
  json += ",\"total_send_limit_ms\":" + String(totalSendLimitMs);
  json += ",\"chunk_bytes\":" + String(chunkBytes);
  json += ",\"synthetic_bytes\":" + String(syntheticBytes);
  json += ",\"frame_count\":" + String(frameCount);
  json += ",\"send_failures\":" + String(sendFailures);
  json += ",\"deadline_drops\":" + String(deadlineDrops);
  json += ",\"last_frame_bytes\":" + String(lastFrameBytes);
  json += ",\"last_capture_ms\":" + String(lastCaptureMs);
  json += ",\"last_send_ms\":" + String(lastSendMs);
  json += ",\"last_accepted_bytes\":" + String(lastAcceptedBytes);
  json += ",\"last_errno\":" + String(lastErrno);
  json += ",\"free_heap\":" + String(ESP.getFreeHeap());
  json += ",\"internal_free\":" + String(heap_caps_get_free_size(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT));
  json += ",\"internal_largest\":" + String(heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT));
  json += ",\"psram_free\":" + String(ESP.getFreePsram());
  json += ",\"rssi\":" + String(WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : -127);
  json += ",\"bssid\":\"" + String(WiFi.status() == WL_CONNECTED ? WiFi.BSSIDstr() : "offline") + "\"";
  json += ",\"channel\":" + String(WiFi.status() == WL_CONNECTED ? WiFi.channel() : -1);
  json += ",\"progress_trace\":[";
  for (size_t i = 0; i < lastTraceCount; ++i) {
    if (i) json += ",";
    json += "{\"bytes\":" + String(lastTraceBytes[i]) + ",\"ms\":" + String(lastTraceMs[i]) + "}";
  }
  json += "]}";
  return json;
}

void sendJson(int code, const String& body) {
  controlServer.sendHeader("Cache-Control", "no-store");
  controlServer.send(code, "application/json", body);
}

bool setFrameSize(const String& value) {
  sensor_t* sensor = esp_camera_sensor_get();
  if (!sensor) return false;
  framesize_t size;
  if (value == "QQVGA") size = FRAMESIZE_QQVGA;
  else if (value == "HQVGA") size = FRAMESIZE_HQVGA;
  else if (value == "QVGA") size = FRAMESIZE_QVGA;
  else if (value == "CIF") size = FRAMESIZE_CIF;
  else if (value == "VGA") size = FRAMESIZE_VGA;
  else return false;
  return sensor->set_framesize(sensor, size) == 0;
}

void handleConfigure() {
  if (!cameraReady || streaming) { sendJson(409, "{\"error\":\"busy_or_not_ready\"}"); return; }
  if (controlServer.hasArg("frame_size") && !setFrameSize(controlServer.arg("frame_size"))) {
    sendJson(422, "{\"error\":\"invalid_frame_size\"}"); return;
  }
  if (controlServer.hasArg("jpeg_quality")) {
    const int q = controlServer.arg("jpeg_quality").toInt();
    sensor_t* sensor = esp_camera_sensor_get();
    if (!sensor || q < 4 || q > 63 || sensor->set_quality(sensor, q) != 0) {
      sendJson(422, "{\"error\":\"invalid_jpeg_quality\"}"); return;
    }
  }
  sendJson(200, statusJson());
}

void handleMode() {
  if (streaming) { sendJson(409, "{\"error\":\"streaming\"}"); return; }
  if (!controlServer.hasArg("mode")) { sendJson(422, "{\"error\":\"missing_mode\"}"); return; }
  const String requested = controlServer.arg("mode");
  if (requested == "direct") mode = TransportMode::Direct;
  else if (requested == "staged") mode = TransportMode::Staged;
  else if (requested == "dram_copy") mode = TransportMode::DramCopy;
  else if (requested == "synthetic") mode = TransportMode::Synthetic;
  else { sendJson(422, "{\"error\":\"invalid_mode\"}"); return; }
  if (controlServer.hasArg("fps")) {
    const int fps = controlServer.arg("fps").toInt();
    if (fps < 1 || fps > 20) { sendJson(422, "{\"error\":\"invalid_fps\"}"); return; }
    targetFps = static_cast<uint8_t>(fps);
  }
  if (controlServer.hasArg("stall_ms")) {
    const int value = controlServer.arg("stall_ms").toInt();
    if (value < 100 || value > 10000) { sendJson(422, "{\"error\":\"invalid_stall_ms\"}"); return; }
    stallTimeoutMs = static_cast<uint32_t>(value);
  }
  if (controlServer.hasArg("total_ms")) {
    const int value = controlServer.arg("total_ms").toInt();
    if (value < 200 || value > 15000 || static_cast<uint32_t>(value) < stallTimeoutMs) {
      sendJson(422, "{\"error\":\"invalid_total_ms\"}"); return;
    }
    totalSendLimitMs = static_cast<uint32_t>(value);
  }
  if (controlServer.hasArg("chunk_bytes")) {
    const int value = controlServer.arg("chunk_bytes").toInt();
    if (value < 128 || value > 4096) { sendJson(422, "{\"error\":\"invalid_chunk_bytes\"}"); return; }
    chunkBytes = static_cast<size_t>(value);
  }
  if (controlServer.hasArg("payload_bytes")) {
    const int value = controlServer.arg("payload_bytes").toInt();
    if (value < 128 || value > static_cast<int>(MAX_SYNTHETIC_BYTES)) {
      sendJson(422, "{\"error\":\"invalid_payload_bytes\"}"); return;
    }
    syntheticBytes = static_cast<size_t>(value);
  }
  sendJson(200, statusJson());
}

void handleCapture() {
  if (!cameraReady || streaming) { controlServer.send(409, "text/plain", "camera busy or not ready"); return; }
  const uint32_t started = millis();
  camera_fb_t* fb = esp_camera_fb_get();
  lastCaptureMs = millis() - started;
  if (!fb) { controlServer.send(503, "text/plain", "capture failed"); return; }
  lastFrameBytes = static_cast<uint32_t>(fb->len);
  controlServer.sendHeader("Cache-Control", "no-store");
  controlServer.setContentLength(fb->len);
  controlServer.send(200, "image/jpeg", "");
  WiFiClient client = controlServer.client();
  client.setNoDelay(true);
  client.write(fb->buf, fb->len);
  esp_camera_fb_return(fb);
}

void handleMjpeg() {
  if (!cameraReady || streaming) { controlServer.send(409, "text/plain", "camera busy or not ready"); return; }
  int frames = controlServer.hasArg("frames") ? controlServer.arg("frames").toInt() : 10;
  int fps = controlServer.hasArg("fps") ? controlServer.arg("fps").toInt() : 5;
  if (frames < 1) frames = 1;
  if (frames > 40) frames = 40;
  if (fps < 1) fps = 1;
  if (fps > 15) fps = 15;
  WiFiClient client = controlServer.client();
  client.setNoDelay(true);
  client.print("HTTP/1.1 200 OK\r\n");
  client.print("Content-Type: multipart/x-mixed-replace; boundary=aitlframe\r\n");
  client.print("Cache-Control: no-store\r\nConnection: close\r\n\r\n");
  const uint32_t periodMs = 1000U / static_cast<uint32_t>(fps);
  for (int i = 0; i < frames && client.connected(); ++i) {
    const uint32_t frameStarted = millis();
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) break;
    lastFrameBytes = static_cast<uint32_t>(fb->len);
    client.printf("--aitlframe\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", static_cast<unsigned int>(fb->len));
    client.write(fb->buf, fb->len);
    client.print("\r\n");
    esp_camera_fb_return(fb);
    const uint32_t elapsed = millis() - frameStarted;
    if (elapsed < periodMs) delay(periodMs - elapsed);
  }
  client.print("--aitlframe--\r\n");
  client.flush();
  client.stop();
}

void handleStart() {
  if (!cameraReady) { sendJson(503, "{\"error\":\"camera_not_ready\"}"); return; }
  closeAtl1Client();
  streaming = true;
  nextFrameDueUs = micros();
  sendJson(200, statusJson());
}

void handleStop() {
  streaming = false;
  closeAtl1Client();
  sendJson(200, statusJson());
}

bool initCamera() {
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
    config.frame_size = FRAMESIZE_UXGA;
    config.jpeg_quality = 10;
    config.fb_count = 1;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    config.fb_location = CAMERA_FB_IN_PSRAM;
  } else {
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 16;
    config.fb_count = 1;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }
  if (esp_camera_init(&config) != ESP_OK) return false;
  sensor_t* sensor = esp_camera_sensor_get();
  if (!sensor) return false;
  if (sensor->set_framesize(sensor, FRAMESIZE_QVGA) != 0) return false;
  if (sensor->set_quality(sensor, 24) != 0) return false;
  return true;
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

void configureClient(WiFiClient& client) {
  client.setNoDelay(true);
  const int fd = client.fd();
  if (fd < 0) return;
  int enabled = 1;
  setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &enabled, sizeof(enabled));
  setsockopt(fd, SOL_SOCKET, SO_KEEPALIVE, &enabled, sizeof(enabled));
}

void acceptAtl1Client() {
  if (!streaming || (atl1Client && atl1Client.connected())) return;
  closeAtl1Client();
  WiFiClient candidate = atl1Server.accept();
  if (!candidate) return;
  configureClient(candidate);
  atl1Client = candidate;
  nextFrameDueUs = micros();
}

void sendNextIfDue() {
  if (!streaming || !(atl1Client && atl1Client.connected())) return;
  const uint32_t nowUs = micros();
  if (static_cast<int32_t>(nowUs - nextFrameDueUs) < 0) return;
  const uint32_t periodUs = 1000000UL / (targetFps > 0 ? targetFps : 1U);
  nextFrameDueUs = nowUs + periodUs;

  camera_fb_t* fb = nullptr;
  const uint8_t* payload = nullptr;
  size_t payloadLength = 0;
  uint8_t* dramCopy = nullptr;

  if (mode == TransportMode::Synthetic) {
    if (!ensureInternalBuffer(syntheticBuffer, syntheticCapacity, syntheticBytes)) {
      lastErrno = ENOMEM; ++sendFailures; closeAtl1Client(); return;
    }
    memset(syntheticBuffer, 0x5A, syntheticBytes);
    syntheticBuffer[0] = 0xFF; syntheticBuffer[1] = 0xD8;
    syntheticBuffer[syntheticBytes - 2] = 0xFF; syntheticBuffer[syntheticBytes - 1] = 0xD9;
    payload = syntheticBuffer;
    payloadLength = syntheticBytes;
    lastCaptureMs = 0;
  } else {
    const uint32_t captureStarted = millis();
    fb = esp_camera_fb_get();
    lastCaptureMs = millis() - captureStarted;
    if (!fb) { lastErrno = EIO; ++sendFailures; closeAtl1Client(); return; }
    payload = fb->buf;
    payloadLength = fb->len;
    if (mode == TransportMode::DramCopy) {
      dramCopy = static_cast<uint8_t*>(heap_caps_malloc(payloadLength, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT));
      if (!dramCopy) {
        lastErrno = ENOMEM; ++sendFailures; esp_camera_fb_return(fb); closeAtl1Client(); return;
      }
      memcpy(dramCopy, payload, payloadLength);
      esp_camera_fb_return(fb);
      fb = nullptr;
      payload = dramCopy;
    }
  }

  lastFrameBytes = static_cast<uint32_t>(payloadLength);
  const bool staged = mode == TransportMode::Staged;
  const bool ok = sendAtl1Frame(payload, payloadLength, staged);
  if (fb) esp_camera_fb_return(fb);
  if (dramCopy) heap_caps_free(dramCopy);
  if (!ok) closeAtl1Client();
}

} // namespace

void setup() {
  Serial.begin(115200);
  delay(50);
  Serial.println();
  Serial.println("AiTL 0_3_8 R3 transport-isolation diagnostic firmware");
  cameraReady = initCamera();
  connectWifi();
  controlServer.on("/status", HTTP_GET, [](){ sendJson(200, statusJson()); });
  controlServer.on("/config", HTTP_POST, handleConfigure);
  controlServer.on("/mode", HTTP_POST, handleMode);
  controlServer.on("/start", HTTP_POST, handleStart);
  controlServer.on("/stop", HTTP_POST, handleStop);
  controlServer.on("/capture", HTTP_GET, handleCapture);
  controlServer.on("/mjpeg", HTTP_GET, handleMjpeg);
  controlServer.onNotFound([](){ sendJson(404, "{\"error\":\"not_found\"}"); });
  controlServer.begin();
  atl1Server.begin();
  atl1Server.setNoDelay(true);
  Serial.printf("Camera ready: %s\n", cameraReady ? "yes" : "no");
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("ESP IP: %s\n", WiFi.localIP().toString().c_str());
    Serial.printf("Control: http://%s/status\n", WiFi.localIP().toString().c_str());
    Serial.printf("MJPEG test: http://%s/mjpeg\n", WiFi.localIP().toString().c_str());
    Serial.printf("ATL1 test: tcp://%s:%u\n", WiFi.localIP().toString().c_str(), ATL1_PORT);
  }
}

void loop() {
  controlServer.handleClient();
  if (WiFi.status() == WL_CONNECTED) {
    acceptAtl1Client();
    sendNextIfDue();
  }
  delay(1);
}
