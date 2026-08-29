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

// V037 new-camera defaults favor transport freshness. Existing saved PC profiles
// are preserved and still override these values during /config.
#ifndef AITL_DEFAULT_FRAME_SIZE
#define AITL_DEFAULT_FRAME_SIZE FRAMESIZE_QVGA
#endif
#ifndef AITL_DEFAULT_JPEG_QUALITY
#define AITL_DEFAULT_JPEG_QUALITY 24
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

#ifndef AITL_STREAM_SELECT_SLICE_MS
#define AITL_STREAM_SELECT_SLICE_MS 20U
#endif
#ifndef AITL_WARMUP_SUCCESS_FRAMES
#define AITL_WARMUP_SUCCESS_FRAMES 3U
#endif
#ifndef AITL_WARMUP_STALL_TIMEOUT_MS
#define AITL_WARMUP_STALL_TIMEOUT_MS 1200U
#endif
#ifndef AITL_WARMUP_TOTAL_SEND_LIMIT_MS
#define AITL_WARMUP_TOTAL_SEND_LIMIT_MS 2000U
#endif
#ifndef AITL_FRAME_STALL_TIMEOUT_MS
#define AITL_FRAME_STALL_TIMEOUT_MS 700U
#endif
#ifndef AITL_FRAME_TOTAL_SEND_LIMIT_MS
#define AITL_FRAME_TOTAL_SEND_LIMIT_MS 1500U
#endif


// R6 intentionally has no automatic JPEG-size target, quality escalation, or
// effective-resolution downshift. TCP segmentation is allowed to carry JPEGs
// larger than one lwIP send buffer; configured image quality is preserved.

#ifndef AITL_WIFI_CONNECT_TIMEOUT_MS
#define AITL_WIFI_CONNECT_TIMEOUT_MS 20000UL
#endif
#ifndef AITL_WIFI_RETRY_MS
#define AITL_WIFI_RETRY_MS 3000UL
#endif
#ifndef AITL_SERIAL_STATUS_INTERVAL_MS
#define AITL_SERIAL_STATUS_INTERVAL_MS 5000UL
#endif
