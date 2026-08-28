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

// Freshness-first transport with a longer bounded warm-up for each new TCP connection.
#ifndef AITL_STREAM_SELECT_SLICE_MS
#define AITL_STREAM_SELECT_SLICE_MS 20U
#endif

#ifndef AITL_WARMUP_SUCCESS_FRAMES
#define AITL_WARMUP_SUCCESS_FRAMES 3U
#endif

#ifndef AITL_WARMUP_STALL_TIMEOUT_MS
#define AITL_WARMUP_STALL_TIMEOUT_MS 1000U
#endif

#ifndef AITL_WARMUP_TOTAL_SEND_LIMIT_MS
#define AITL_WARMUP_TOTAL_SEND_LIMIT_MS 1500U
#endif

#ifndef AITL_FRAME_STALL_TIMEOUT_MS
#define AITL_FRAME_STALL_TIMEOUT_MS 500U
#endif

#ifndef AITL_FRAME_TOTAL_SEND_LIMIT_MS
#define AITL_FRAME_TOTAL_SEND_LIMIT_MS 900U
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
