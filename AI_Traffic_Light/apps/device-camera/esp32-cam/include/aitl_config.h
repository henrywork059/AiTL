#pragma once

#include <esp_camera.h>

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
#define AITL_DEVICE_HOSTNAME "aitl-cam-01"
#endif

#ifndef AITL_DEFAULT_SOURCE_ID
#define AITL_DEFAULT_SOURCE_ID "esp32_cam_01"
#endif

#ifndef AITL_DEFAULT_FRAME_SIZE
#define AITL_DEFAULT_FRAME_SIZE FRAMESIZE_VGA
#endif

// ESP camera JPEG quality: lower number = higher image quality/larger frame.
#ifndef AITL_DEFAULT_JPEG_QUALITY
#define AITL_DEFAULT_JPEG_QUALITY 14
#endif

#ifndef AITL_DEFAULT_STREAM_FPS
#define AITL_DEFAULT_STREAM_FPS 15U
#endif

#ifndef AITL_CONTROL_PORT
#define AITL_CONTROL_PORT 80U
#endif

#ifndef AITL_STREAM_PORT
#define AITL_STREAM_PORT 81U
#endif

// Freshness-first transport: a blocked frame is abandoned instead of queued.
#ifndef AITL_STREAM_SEND_TIMEOUT_MS
#define AITL_STREAM_SEND_TIMEOUT_MS 120U
#endif

#ifndef AITL_FRAME_SEND_DEADLINE_MS
#define AITL_FRAME_SEND_DEADLINE_MS 120U
#endif

#ifndef AITL_WIFI_CONNECT_TIMEOUT_MS
#define AITL_WIFI_CONNECT_TIMEOUT_MS 20000UL
#endif

#ifndef AITL_WIFI_RETRY_MS
#define AITL_WIFI_RETRY_MS 3000UL
#endif

#ifndef AITL_SERIAL_STATUS_INTERVAL_MS
#define AITL_SERIAL_STATUS_INTERVAL_MS 5000UL
#endif
