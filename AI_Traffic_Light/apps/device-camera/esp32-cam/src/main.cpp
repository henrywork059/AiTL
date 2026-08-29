// AiTL V037 PlatformIO firmware (quality-preserving persistent TCP JPEG).
#include <Arduino.h>
#include <errno.h>
#include <sys/uio.h>
#include <WebServer.h>
#include <WiFi.h>
#include <esp_camera.h>
#include <esp_timer.h>
#include <lwip/sockets.h>
#include <lwip/tcp.h>

#include "aitl_config.h"

namespace {

constexpr char kCameraProtocol[] = "aitl-camera-v037";
constexpr char kStreamProtocol[] = "aitl-tcp-jpeg-v1";
constexpr char kFirmwareRevision[] = "v037-r6-quality-preserving-tcp";
constexpr uint8_t kFrameMagic[4] = {'A', 'T', 'L', '1'};
constexpr size_t kFrameHeaderBytes = 16;

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

struct CameraSettings {
  framesize_t frameSize = AITL_DEFAULT_FRAME_SIZE;
  int jpegQuality = AITL_DEFAULT_JPEG_QUALITY;
  int brightness = 0;
  int contrast = 0;
  int saturation = 0;
  int specialEffect = 0;
  bool awb = true;
  bool awbGain = true;
  int wbMode = 0;
  bool aec = true;
  bool aec2 = false;
  int aeLevel = 0;
  int aecValue = 300;
  bool agc = true;
  int agcGain = 0;
  int gainCeiling = 0;
  bool bpc = false;
  bool wpc = true;
  bool rawGma = true;
  bool lenc = true;
  bool hmirror = false;
  bool vflip = false;
  bool dcw = true;
  bool colorbar = false;
};

WebServer controlServer(AITL_CONTROL_PORT);
WiFiServer streamServer(AITL_STREAM_PORT, 1);
WiFiClient streamClient;
CameraSettings settings;

bool cameraReady = false;
bool sessionActive = false;
uint8_t targetFps = AITL_DEFAULT_STREAM_FPS;
uint32_t nextFrameDueUs = 0;
uint32_t sequenceNumber = 0;
uint32_t streamFrameCount = 0;
uint32_t streamSendFailures = 0;
uint32_t streamDeadlineDrops = 0;
uint32_t lastFrameBytes = 0;
uint32_t lastCaptureMs = 0;
uint32_t lastSendMs = 0;
uint32_t lastFrameAtMs = 0;
uint32_t lastWifiRetryAtMs = 0;
uint32_t lastStatusAtMs = 0;
uint32_t fpsWindowStartedAtMs = 0;
uint32_t fpsWindowFrames = 0;
float actualFps = 0.0f;
uint32_t streamClientSuccessfulFrames = 0;
uint32_t lastSendAcceptedBytes = 0;
int lastSendErrno = 0;
bool lastSendWarmup = false;
int effectiveJpegQuality = AITL_DEFAULT_JPEG_QUALITY;  // R6 mirrors the saved setting.
float sendEwmaMs = 0.0f;
uint32_t transportSlowFrames = 0;
// Legacy R2/R4 telemetry remains at zero for same-candidate API/UI compatibility.
uint32_t adaptiveQualityAdjustments = 0;
uint32_t adaptivePayloadTargetBytes = 0;
uint32_t adaptiveLocalFrameDrops = 0;
uint32_t adaptiveWindowLearns = 0;
framesize_t effectiveFrameSize = AITL_DEFAULT_FRAME_SIZE;  // Mirrors settings.frameSize.
uint32_t adaptiveResolutionDownshifts = 0;
uint32_t adaptiveResolutionRecoveries = 0;
uint16_t lastFrameWidth = 0;
uint16_t lastFrameHeight = 0;
uint32_t wifiDisconnects = 0;
uint32_t wifiReconnects = 0;
bool wifiEverConnected = false;
bool wifiPreviouslyConnected = false;

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
    default: return "VGA";
  }
}


bool parseFrameSize(const String& value, framesize_t& out) {
  if (value == "QQVGA") out = FRAMESIZE_QQVGA;
  else if (value == "HQVGA") out = FRAMESIZE_HQVGA;
  else if (value == "QVGA") out = FRAMESIZE_QVGA;
  else if (value == "CIF") out = FRAMESIZE_CIF;
  else if (value == "VGA") out = FRAMESIZE_VGA;
  else if (value == "SVGA") out = FRAMESIZE_SVGA;
  else if (value == "XGA") out = FRAMESIZE_XGA;
  else if (value == "SXGA") out = FRAMESIZE_SXGA;
  else if (value == "UXGA") out = FRAMESIZE_UXGA;
  else return false;
  return true;
}

bool parseBoolArg(const String& value) {
  return value == "1" || value == "true" || value == "on";
}

void closeStreamClient() {
  if (streamClient) {
    streamClient.stop();
  }
  streamClient = WiFiClient();
}

void putU32be(uint8_t* out, uint32_t value) {
  out[0] = static_cast<uint8_t>((value >> 24) & 0xFF);
  out[1] = static_cast<uint8_t>((value >> 16) & 0xFF);
  out[2] = static_cast<uint8_t>((value >> 8) & 0xFF);
  out[3] = static_cast<uint8_t>(value & 0xFF);
}

bool waitSocketWritableForProgress(
    int fd,
    uint32_t totalStartedMs,
    uint32_t lastProgressMs,
    uint32_t stallTimeoutMs,
    uint32_t totalLimitMs) {
  while (true) {
    const uint32_t now = millis();
    if (now - totalStartedMs >= totalLimitMs) return false;
    if (now - lastProgressMs >= stallTimeoutMs) return false;

    const uint32_t totalRemaining = totalLimitMs - (now - totalStartedMs);
    const uint32_t stallRemaining = stallTimeoutMs - (now - lastProgressMs);
    uint32_t waitMs = AITL_STREAM_SELECT_SLICE_MS;
    if (totalRemaining < waitMs) waitMs = totalRemaining;
    if (stallRemaining < waitMs) waitMs = stallRemaining;
    if (waitMs == 0) return false;

    fd_set writeSet;
    FD_ZERO(&writeSet);
    FD_SET(fd, &writeSet);
    timeval timeout{};
    timeout.tv_sec = waitMs / 1000U;
    timeout.tv_usec = (waitMs % 1000U) * 1000U;

    const int ready = select(fd + 1, nullptr, &writeSet, nullptr, &timeout);
    if (ready > 0) return FD_ISSET(fd, &writeSet);
    if (ready == 0) {
      delay(1);
      continue;
    }
    if (errno == EINTR) continue;
    return false;
  }
}

bool sendFrameVectoredProgressBounded(
    int fd,
    const uint8_t* header,
    size_t headerLength,
    const uint8_t* payload,
    size_t payloadLength,
    uint32_t totalStartedMs,
    uint32_t stallTimeoutMs,
    uint32_t totalLimitMs,
    size_t& acceptedBytes,
    int& terminalErrno) {
  const size_t totalLength = headerLength + payloadLength;
  size_t sent = 0;
  uint32_t lastProgressMs = millis();
  acceptedBytes = 0;
  terminalErrno = 0;

  while (sent < totalLength) {
    const uint32_t now = millis();
    if (now - totalStartedMs >= totalLimitMs || now - lastProgressMs >= stallTimeoutMs) {
      terminalErrno = ETIMEDOUT;
      acceptedBytes = sent;
      return false;
    }

    iovec vectors[2]{};
    int vectorCount = 0;
    if (sent < headerLength) {
      vectors[vectorCount].iov_base = const_cast<uint8_t*>(header + sent);
      vectors[vectorCount].iov_len = headerLength - sent;
      ++vectorCount;
      if (payloadLength > 0) {
        vectors[vectorCount].iov_base = const_cast<uint8_t*>(payload);
        vectors[vectorCount].iov_len = payloadLength;
        ++vectorCount;
      }
    } else {
      const size_t payloadOffset = sent - headerLength;
      vectors[0].iov_base = const_cast<uint8_t*>(payload + payloadOffset);
      vectors[0].iov_len = payloadLength - payloadOffset;
      vectorCount = 1;
    }

    msghdr message{};
    message.msg_iov = vectors;
    message.msg_iovlen = vectorCount;

    // Present header + JPEG as one logical write so lwIP can fill MSS-sized
    // segments efficiently instead of emitting a standalone 16-byte packet.
    const int result = ::sendmsg(fd, &message, MSG_DONTWAIT);
    if (result > 0) {
      sent += static_cast<size_t>(result);
      acceptedBytes = sent;
      lastProgressMs = millis();
      delay(1);
      continue;
    }
    if (result == 0) {
      terminalErrno = ECONNRESET;
      acceptedBytes = sent;
      return false;
    }
    if (errno == EINTR) continue;
    if (errno == EAGAIN || errno == EWOULDBLOCK) {
      if (!waitSocketWritableForProgress(fd, totalStartedMs, lastProgressMs, stallTimeoutMs, totalLimitMs)) {
        terminalErrno = ETIMEDOUT;
        acceptedBytes = sent;
        return false;
      }
      continue;
    }
    terminalErrno = errno;
    acceptedBytes = sent;
    return false;
  }
  return true;
}

void configureStreamSocket(WiFiClient& client) {
  client.setNoDelay(true);
  const int fd = client.fd();
  if (fd < 0) return;

  int enabled = 1;
  setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &enabled, sizeof(enabled));
  setsockopt(fd, SOL_SOCKET, SO_KEEPALIVE, &enabled, sizeof(enabled));

#ifdef TCP_KEEPIDLE
  int keepIdle = 3;
  setsockopt(fd, IPPROTO_TCP, TCP_KEEPIDLE, &keepIdle, sizeof(keepIdle));
#endif
#ifdef TCP_KEEPINTVL
  int keepInterval = 1;
  setsockopt(fd, IPPROTO_TCP, TCP_KEEPINTVL, &keepInterval, sizeof(keepInterval));
#endif
#ifdef TCP_KEEPCNT
  int keepCount = 3;
  setsockopt(fd, IPPROTO_TCP, TCP_KEEPCNT, &keepCount, sizeof(keepCount));
#endif
}

String settingsJson() {
  String json = "{";
  json += "\"frame_size\":\"" + String(frameSizeName(settings.frameSize)) + "\"";
  json += ",\"jpeg_quality\":" + String(settings.jpegQuality);
  json += ",\"brightness\":" + String(settings.brightness);
  json += ",\"contrast\":" + String(settings.contrast);
  json += ",\"saturation\":" + String(settings.saturation);
  json += ",\"special_effect\":" + String(settings.specialEffect);
  json += ",\"awb\":" + String(settings.awb ? "true" : "false");
  json += ",\"awb_gain\":" + String(settings.awbGain ? "true" : "false");
  json += ",\"wb_mode\":" + String(settings.wbMode);
  json += ",\"aec\":" + String(settings.aec ? "true" : "false");
  json += ",\"aec2\":" + String(settings.aec2 ? "true" : "false");
  json += ",\"ae_level\":" + String(settings.aeLevel);
  json += ",\"aec_value\":" + String(settings.aecValue);
  json += ",\"agc\":" + String(settings.agc ? "true" : "false");
  json += ",\"agc_gain\":" + String(settings.agcGain);
  json += ",\"gainceiling\":" + String(settings.gainCeiling);
  json += ",\"bpc\":" + String(settings.bpc ? "true" : "false");
  json += ",\"wpc\":" + String(settings.wpc ? "true" : "false");
  json += ",\"raw_gma\":" + String(settings.rawGma ? "true" : "false");
  json += ",\"lenc\":" + String(settings.lenc ? "true" : "false");
  json += ",\"hmirror\":" + String(settings.hmirror ? "true" : "false");
  json += ",\"vflip\":" + String(settings.vflip ? "true" : "false");
  json += ",\"dcw\":" + String(settings.dcw ? "true" : "false");
  json += ",\"colorbar\":" + String(settings.colorbar ? "true" : "false");
  json += "}";
  return json;
}

String statusJson() {
  String json = "{";
  json += "\"protocol\":\"" + String(kCameraProtocol) + "\"";
  json += ",\"stream_protocol\":\"" + String(kStreamProtocol) + "\"";
  json += ",\"firmware_revision\":\"" + String(kFirmwareRevision) + "\"";
  json += ",\"camera_ready\":" + String(cameraReady ? "true" : "false");
  json += ",\"session_active\":" + String(sessionActive ? "true" : "false");
  json += ",\"stream_client_active\":" + String((streamClient && streamClient.connected()) ? "true" : "false");
  json += ",\"stream_port\":" + String(AITL_STREAM_PORT);
  json += ",\"stream_fps\":" + String(targetFps);
  json += ",\"stream_frame_count\":" + String(streamFrameCount);
  json += ",\"stream_send_failures\":" + String(streamSendFailures);
  json += ",\"stream_deadline_drops\":" + String(streamDeadlineDrops);
  json += ",\"send_stall_timeout_ms\":" + String(AITL_FRAME_STALL_TIMEOUT_MS);
  json += ",\"frame_send_limit_ms\":" + String(AITL_FRAME_TOTAL_SEND_LIMIT_MS);
  json += ",\"warmup_stall_timeout_ms\":" + String(AITL_WARMUP_STALL_TIMEOUT_MS);
  json += ",\"warmup_send_limit_ms\":" + String(AITL_WARMUP_TOTAL_SEND_LIMIT_MS);
  json += ",\"stream_client_successful_frames\":" + String(streamClientSuccessfulFrames);
  json += ",\"last_send_accepted_bytes\":" + String(lastSendAcceptedBytes);
  json += ",\"last_send_errno\":" + String(lastSendErrno);
  json += ",\"last_send_warmup\":" + String(lastSendWarmup ? "true" : "false");
  json += ",\"quality_preserving_transport\":true";
  json += ",\"adaptive_quality_enabled\":false";
  json += ",\"configured_jpeg_quality\":" + String(settings.jpegQuality);
  json += ",\"effective_jpeg_quality\":" + String(effectiveJpegQuality);
  json += ",\"adaptive_quality_adjustments\":" + String(adaptiveQualityAdjustments);
  json += ",\"send_ewma_ms\":" + String(sendEwmaMs, 1);
  json += ",\"adaptive_payload_target_bytes\":" + String(adaptivePayloadTargetBytes);
  json += ",\"adaptive_local_frame_drops\":" + String(adaptiveLocalFrameDrops);
  json += ",\"adaptive_window_learns\":" + String(adaptiveWindowLearns);
  json += ",\"configured_frame_size\":\"" + String(frameSizeName(settings.frameSize)) + "\"";
  json += ",\"effective_frame_size\":\"" + String(frameSizeName(effectiveFrameSize)) + "\"";
  json += ",\"adaptive_resolution_downshifts\":" + String(adaptiveResolutionDownshifts);
  json += ",\"adaptive_resolution_recoveries\":" + String(adaptiveResolutionRecoveries);
  json += ",\"last_frame_width\":" + String(lastFrameWidth);
  json += ",\"last_frame_height\":" + String(lastFrameHeight);
  json += ",\"last_frame_bytes\":" + String(lastFrameBytes);
  json += ",\"last_capture_ms\":" + String(lastCaptureMs);
  json += ",\"last_send_ms\":" + String(lastSendMs);
  json += ",\"last_frame_at_ms\":" + String(lastFrameAtMs);
  json += ",\"actual_fps\":" + String(actualFps, 2);
  json += ",\"psram\":" + String(psramFound() ? "true" : "false");
  json += ",\"rssi\":" + String(WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : -127);
  json += ",\"wifi_bssid\":\"" + String(WiFi.status() == WL_CONNECTED ? WiFi.BSSIDstr() : "offline") + "\"";
  json += ",\"wifi_channel\":" + String(WiFi.status() == WL_CONNECTED ? WiFi.channel() : -1);
  json += ",\"wifi_disconnects\":" + String(wifiDisconnects);
  json += ",\"wifi_reconnects\":" + String(wifiReconnects);
  json += ",\"transport_slow_frames\":" + String(transportSlowFrames);
  json += ",\"free_heap\":" + String(ESP.getFreeHeap());
  json += ",\"uptime_ms\":" + String(millis());
  json += ",\"settings\":" + settingsJson();
  json += "}";
  return json;
}

void sendJson(int code, const String& body) {
  controlServer.sendHeader("Cache-Control", "no-store");
  controlServer.send(code, "application/json", body);
}

bool applySettings() {
  sensor_t* sensor = esp_camera_sensor_get();
  if (!sensor) return false;

  int failures = 0;
  failures += sensor->set_framesize(sensor, settings.frameSize) != 0;
  failures += sensor->set_quality(sensor, settings.jpegQuality) != 0;
  failures += sensor->set_brightness(sensor, settings.brightness) != 0;
  failures += sensor->set_contrast(sensor, settings.contrast) != 0;
  failures += sensor->set_saturation(sensor, settings.saturation) != 0;
  failures += sensor->set_special_effect(sensor, settings.specialEffect) != 0;
  failures += sensor->set_whitebal(sensor, settings.awb ? 1 : 0) != 0;
  failures += sensor->set_awb_gain(sensor, settings.awbGain ? 1 : 0) != 0;
  failures += sensor->set_wb_mode(sensor, settings.wbMode) != 0;
  failures += sensor->set_exposure_ctrl(sensor, settings.aec ? 1 : 0) != 0;
  failures += sensor->set_aec2(sensor, settings.aec2 ? 1 : 0) != 0;
  failures += sensor->set_ae_level(sensor, settings.aeLevel) != 0;
  failures += sensor->set_aec_value(sensor, settings.aecValue) != 0;
  failures += sensor->set_gain_ctrl(sensor, settings.agc ? 1 : 0) != 0;
  failures += sensor->set_agc_gain(sensor, settings.agcGain) != 0;
  failures += sensor->set_gainceiling(sensor, static_cast<gainceiling_t>(settings.gainCeiling)) != 0;
  failures += sensor->set_bpc(sensor, settings.bpc ? 1 : 0) != 0;
  failures += sensor->set_wpc(sensor, settings.wpc ? 1 : 0) != 0;
  failures += sensor->set_raw_gma(sensor, settings.rawGma ? 1 : 0) != 0;
  failures += sensor->set_lenc(sensor, settings.lenc ? 1 : 0) != 0;
  failures += sensor->set_hmirror(sensor, settings.hmirror ? 1 : 0) != 0;
  failures += sensor->set_vflip(sensor, settings.vflip ? 1 : 0) != 0;
  failures += sensor->set_dcw(sensor, settings.dcw ? 1 : 0) != 0;
  failures += sensor->set_colorbar(sensor, settings.colorbar ? 1 : 0) != 0;
  if (failures == 0) {
    // R6 never changes quality or resolution behind the user's saved profile.
    effectiveJpegQuality = settings.jpegQuality;
    effectiveFrameSize = settings.frameSize;
    sendEwmaMs = 0.0f;
    adaptiveQualityAdjustments = 0;
    adaptivePayloadTargetBytes = 0;
    adaptiveLocalFrameDrops = 0;
    adaptiveWindowLearns = 0;
    adaptiveResolutionDownshifts = 0;
    adaptiveResolutionRecoveries = 0;
  }
  return failures == 0;
}

void updateSendTelemetry(uint32_t sendMs) {
  if (sendMs > 0) {
    sendEwmaMs = sendEwmaMs <= 0.0f
        ? static_cast<float>(sendMs)
        : (sendEwmaMs * 0.80f + static_cast<float>(sendMs) * 0.20f);
  }
  const uint32_t safeFps = targetFps > 0 ? targetFps : 1U;
  const uint32_t frameBudgetMs = 1000U / safeFps;
  if (sendMs > frameBudgetMs) ++transportSlowFrames;
}

bool readRequiredArg(const char* name, String& out) {
  if (!controlServer.hasArg(name)) return false;
  out = controlServer.arg(name);
  return true;
}

void handleConfig() {
  if (!cameraReady) {
    sendJson(503, "{\"error\":\"camera_not_ready\"}");
    return;
  }
  if (streamClient && streamClient.connected()) {
    sendJson(409, "{\"error\":\"stream_client_active\"}");
    return;
  }

  CameraSettings next = settings;
  String value;
  framesize_t parsedFrameSize;
  if (!readRequiredArg("frame_size", value) || !parseFrameSize(value, parsedFrameSize)) {
    sendJson(422, "{\"error\":\"invalid_frame_size\"}");
    return;
  }
  next.frameSize = parsedFrameSize;

#define READ_INT_ARG(NAME, FIELD) \
  do { if (!readRequiredArg(NAME, value)) { sendJson(422, "{\"error\":\"missing_setting\"}"); return; } next.FIELD = value.toInt(); } while (0)
#define READ_BOOL_ARG(NAME, FIELD) \
  do { if (!readRequiredArg(NAME, value)) { sendJson(422, "{\"error\":\"missing_setting\"}"); return; } next.FIELD = parseBoolArg(value); } while (0)

  READ_INT_ARG("jpeg_quality", jpegQuality);
  READ_INT_ARG("brightness", brightness);
  READ_INT_ARG("contrast", contrast);
  READ_INT_ARG("saturation", saturation);
  READ_INT_ARG("special_effect", specialEffect);
  READ_BOOL_ARG("awb", awb);
  READ_BOOL_ARG("awb_gain", awbGain);
  READ_INT_ARG("wb_mode", wbMode);
  READ_BOOL_ARG("aec", aec);
  READ_BOOL_ARG("aec2", aec2);
  READ_INT_ARG("ae_level", aeLevel);
  READ_INT_ARG("aec_value", aecValue);
  READ_BOOL_ARG("agc", agc);
  READ_INT_ARG("agc_gain", agcGain);
  READ_INT_ARG("gainceiling", gainCeiling);
  READ_BOOL_ARG("bpc", bpc);
  READ_BOOL_ARG("wpc", wpc);
  READ_BOOL_ARG("raw_gma", rawGma);
  READ_BOOL_ARG("lenc", lenc);
  READ_BOOL_ARG("hmirror", hmirror);
  READ_BOOL_ARG("vflip", vflip);
  READ_BOOL_ARG("dcw", dcw);
  READ_BOOL_ARG("colorbar", colorbar);

#undef READ_INT_ARG
#undef READ_BOOL_ARG

  if (!readRequiredArg("stream_fps", value)) {
    sendJson(422, "{\"error\":\"missing_stream_fps\"}");
    return;
  }
  const int fps = value.toInt();
  if (fps < 1 || fps > 30 || next.jpegQuality < 4 || next.jpegQuality > 63) {
    sendJson(422, "{\"error\":\"setting_out_of_range\"}");
    return;
  }

  settings = next;
  targetFps = static_cast<uint8_t>(fps);
  if (!applySettings()) {
    sendJson(500, "{\"error\":\"sensor_setting_failed\"}");
    return;
  }
  sendJson(200, statusJson());
}

void handleStart() {
  if (!cameraReady) {
    sendJson(503, "{\"error\":\"camera_not_ready\"}");
    return;
  }
  closeStreamClient();
  sessionActive = true;
  nextFrameDueUs = micros();
  sendJson(200, statusJson());
}

void handleStop() {
  sessionActive = false;
  closeStreamClient();
  sendJson(200, statusJson());
}

void handleCapture() {
  if (!cameraReady || sessionActive) {
    controlServer.send(409, "text/plain", "Capture is available only while the streaming session is idle.");
    return;
  }
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    controlServer.send(503, "text/plain", "Camera capture failed.");
    return;
  }
  controlServer.sendHeader("Cache-Control", "no-store");
  controlServer.setContentLength(fb->len);
  controlServer.send(200, "image/jpeg", "");
  WiFiClient client = controlServer.client();
  client.write(fb->buf, fb->len);
  esp_camera_fb_return(fb);
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
    // Allocate for the maximum supported JPEG size first, then lower the runtime
    // sensor resolution. This follows the current Espressif CameraWebServer strategy
    // and avoids framebuffer overflow after later set_framesize() calls.
    config.frame_size = FRAMESIZE_UXGA;
    config.jpeg_quality = 10;
    // R6 physical isolation: one WHEN_EMPTY buffer avoids continuous
    // two-buffer DMA/FB pressure while retaining runtime resolution changes.
    config.fb_count = 1;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    config.fb_location = CAMERA_FB_IN_PSRAM;
  } else {
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 16;
    config.fb_count = 1;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    config.fb_location = CAMERA_FB_IN_DRAM;
    settings.frameSize = FRAMESIZE_QVGA;
    settings.jpegQuality = 16;
  }

  const esp_err_t result = esp_camera_init(&config);
  if (result != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", result);
    return false;
  }
  return applySettings();
}

void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setAutoReconnect(true);
  WiFi.setHostname(AITL_DEVICE_HOSTNAME);
  WiFi.begin(AITL_WIFI_SSID, AITL_WIFI_PASSWORD);

  const uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < AITL_WIFI_CONNECT_TIMEOUT_MS) {
    delay(100);
  }
  wifiPreviouslyConnected = WiFi.status() == WL_CONNECTED;
  wifiEverConnected = wifiPreviouslyConnected;
}

void maintainWifi() {
  const bool connected = WiFi.status() == WL_CONNECTED;
  if (connected) {
    if (!wifiPreviouslyConnected) {
      if (wifiEverConnected) ++wifiReconnects;
      wifiEverConnected = true;
      Serial.printf("Wi-Fi connected ip=%s rssi=%d bssid=%s channel=%d reconnects=%lu\n",
                    WiFi.localIP().toString().c_str(), WiFi.RSSI(), WiFi.BSSIDstr().c_str(),
                    WiFi.channel(), static_cast<unsigned long>(wifiReconnects));
    }
    wifiPreviouslyConnected = true;
    return;
  }

  if (wifiPreviouslyConnected) {
    ++wifiDisconnects;
    Serial.printf("Wi-Fi lost disconnects=%lu; preserving configured image quality/resolution\n",
                  static_cast<unsigned long>(wifiDisconnects));
  }
  wifiPreviouslyConnected = false;
  closeStreamClient();
  if (millis() - lastWifiRetryAtMs < AITL_WIFI_RETRY_MS) return;
  lastWifiRetryAtMs = millis();
  WiFi.reconnect();
}

void discardBufferedFrame() {
  if (!cameraReady) return;
  camera_fb_t* fb = esp_camera_fb_get();
  if (fb) esp_camera_fb_return(fb);
}

void acceptStreamClient() {
  if (!sessionActive || WiFi.status() != WL_CONNECTED) return;
  if (streamClient && streamClient.connected()) return;

  closeStreamClient();
  WiFiClient candidate = streamServer.accept();
  if (!candidate) return;
  configureStreamSocket(candidate);
  streamClient = candidate;
  streamClientSuccessfulFrames = 0;
  // Flush the frame that may have been held while idle; first transmitted frame is fresh.
  discardBufferedFrame();
  nextFrameDueUs = micros();
  Serial.printf("TCP stream client connected from %s rssi=%d bssid=%s channel=%d\n",
                streamClient.remoteIP().toString().c_str(), WiFi.RSSI(),
                WiFi.BSSIDstr().c_str(), WiFi.channel());
}

void updateFpsWindow() {
  ++fpsWindowFrames;
  const uint32_t now = millis();
  const uint32_t elapsed = now - fpsWindowStartedAtMs;
  if (elapsed >= 1000U) {
    actualFps = (1000.0f * static_cast<float>(fpsWindowFrames)) / static_cast<float>(elapsed);
    fpsWindowFrames = 0;
    fpsWindowStartedAtMs = now;
  }
}

void sendNextFrameIfDue() {
  if (!sessionActive || !(streamClient && streamClient.connected())) return;

  const uint32_t nowUs = micros();
  if (static_cast<int32_t>(nowUs - nextFrameDueUs) < 0) return;

  const uint32_t periodUs = 1000000UL / (targetFps > 0 ? targetFps : 1);
  nextFrameDueUs += periodUs;
  if (static_cast<int32_t>(nowUs - nextFrameDueUs) > static_cast<int32_t>(periodUs)) {
    // Never "catch up" by sending old work. Schedule from now when behind.
    nextFrameDueUs = nowUs + periodUs;
  }

  const uint32_t captureStarted = millis();
  camera_fb_t* fb = esp_camera_fb_get();
  lastCaptureMs = millis() - captureStarted;
  if (!fb) {
    ++streamSendFailures;
    closeStreamClient();
    return;
  }

  lastFrameBytes = static_cast<uint32_t>(fb->len);
  lastFrameWidth = static_cast<uint16_t>(fb->width);
  lastFrameHeight = static_cast<uint16_t>(fb->height);
  // R6 deliberately sends the configured JPEG as-is. TCP may segment any
  // payload size; a lwIP send buffer is not a maximum JPEG size.

  ++sequenceNumber;
  uint8_t header[kFrameHeaderBytes];
  memcpy(header, kFrameMagic, sizeof(kFrameMagic));
  putU32be(header + 4, static_cast<uint32_t>(fb->len));
  putU32be(header + 8, sequenceNumber);
  putU32be(header + 12, millis());

  const int fd = streamClient.fd();
  const bool warmup = streamClientSuccessfulFrames < AITL_WARMUP_SUCCESS_FRAMES;
  const uint32_t stallTimeoutMs = warmup ? AITL_WARMUP_STALL_TIMEOUT_MS : AITL_FRAME_STALL_TIMEOUT_MS;
  const uint32_t totalLimitMs = warmup ? AITL_WARMUP_TOTAL_SEND_LIMIT_MS : AITL_FRAME_TOTAL_SEND_LIMIT_MS;
  const uint32_t sendStarted = millis();
  size_t acceptedBytes = 0;
  int terminalErrno = 0;
  const bool payloadOk = fd >= 0 && sendFrameVectoredProgressBounded(
      fd,
      header,
      sizeof(header),
      fb->buf,
      fb->len,
      sendStarted,
      stallTimeoutMs,
      totalLimitMs,
      acceptedBytes,
      terminalErrno);
  lastSendMs = millis() - sendStarted;
  lastSendAcceptedBytes = static_cast<uint32_t>(acceptedBytes);
  lastSendErrno = terminalErrno;
  lastSendWarmup = warmup;
  updateSendTelemetry(lastSendMs);
  esp_camera_fb_return(fb);

  if (!payloadOk) {
    ++streamSendFailures;
    if (terminalErrno == ETIMEDOUT) ++streamDeadlineDrops;
    Serial.printf(
        "TCP send failed frame=%luB send=%lums accepted=%lu errno=%d rssi=%d bssid=%s channel=%d; quality/resolution preserved\n",
        static_cast<unsigned long>(lastFrameBytes),
        static_cast<unsigned long>(lastSendMs),
        static_cast<unsigned long>(lastSendAcceptedBytes),
        lastSendErrno,
        WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : -127,
        WiFi.status() == WL_CONNECTED ? WiFi.BSSIDstr().c_str() : "offline",
        WiFi.status() == WL_CONNECTED ? WiFi.channel() : -1);
    // A partial length-prefixed frame invalidates this socket. Close it and wait
    // for the PC reconnect worker; never degrade future JPEG quality/resolution.
    closeStreamClient();
    return;
  }

  ++streamClientSuccessfulFrames;
  ++streamFrameCount;
  lastFrameAtMs = millis();
  updateFpsWindow();
}

void printPeriodicStatus() {
  if (millis() - lastStatusAtMs < AITL_SERIAL_STATUS_INTERVAL_MS) return;
  lastStatusAtMs = millis();
  Serial.printf(
      "ip=%s session=%s client=%s fps=%.1f target=%u res=%ux%u/%s frame=%luB capture=%lums send=%lums accepted=%lu errno=%d warmup=%s q=%d/%d fixed=yes ewma=%.0fms slow=%lu failures=%lu deadlines=%lu rssi=%d bssid=%s ch=%d wifiDisc=%lu wifiRec=%lu\n",
      WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString().c_str() : "offline",
      sessionActive ? "on" : "off",
      (streamClient && streamClient.connected()) ? "on" : "off",
      actualFps,
      targetFps,
      static_cast<unsigned int>(lastFrameWidth),
      static_cast<unsigned int>(lastFrameHeight),
      frameSizeName(settings.frameSize),
      static_cast<unsigned long>(lastFrameBytes),
      static_cast<unsigned long>(lastCaptureMs),
      static_cast<unsigned long>(lastSendMs),
      static_cast<unsigned long>(lastSendAcceptedBytes),
      lastSendErrno,
      lastSendWarmup ? "yes" : "no",
      effectiveJpegQuality,
      settings.jpegQuality,
      sendEwmaMs,
      static_cast<unsigned long>(transportSlowFrames),
      static_cast<unsigned long>(streamSendFailures),
      static_cast<unsigned long>(streamDeadlineDrops),
      WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : -127,
      WiFi.status() == WL_CONNECTED ? WiFi.BSSIDstr().c_str() : "offline",
      WiFi.status() == WL_CONNECTED ? WiFi.channel() : -1,
      static_cast<unsigned long>(wifiDisconnects),
      static_cast<unsigned long>(wifiReconnects));
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(50);
  Serial.println();
  Serial.println("AiTL V037 R6 quality-preserving TCP ESP32-CAM node");

  cameraReady = initCamera();
  connectWifi();

  controlServer.on("/status", HTTP_GET, []() { sendJson(200, statusJson()); });
  controlServer.on("/config", HTTP_POST, handleConfig);
  controlServer.on("/start", HTTP_POST, handleStart);
  controlServer.on("/stop", HTTP_POST, handleStop);
  controlServer.on("/capture", HTTP_GET, handleCapture);
  controlServer.onNotFound([]() { sendJson(404, "{\"error\":\"not_found\"}"); });
  controlServer.begin();

  streamServer.setNoDelay(true);
  streamServer.begin();
  streamServer.setNoDelay(true);
  fpsWindowStartedAtMs = millis();

  Serial.printf("Camera ready: %s\n", cameraReady ? "yes" : "no");
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("ESP IP: %s\n", WiFi.localIP().toString().c_str());
    Serial.printf("Wi-Fi: rssi=%d bssid=%s channel=%d\n", WiFi.RSSI(), WiFi.BSSIDstr().c_str(), WiFi.channel());
    Serial.printf("Control: http://%s/status\n", WiFi.localIP().toString().c_str());
    Serial.printf("Stream: tcp://%s:%u (%s)\n", WiFi.localIP().toString().c_str(), AITL_STREAM_PORT, kStreamProtocol);
  } else {
    Serial.println("Wi-Fi not connected yet; automatic retry remains enabled.");
  }
}

void loop() {
  maintainWifi();
  controlServer.handleClient();
  acceptStreamClient();
  sendNextFrameIfDue();
  printPeriodicStatus();
  delay(0);
}
