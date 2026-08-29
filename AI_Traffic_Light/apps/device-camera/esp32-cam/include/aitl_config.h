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

// Adaptive JPEG pressure controller. OV2640 quality uses an inverse scale:
// higher number = stronger compression = smaller JPEG. The user's configured
// quality is the best-quality floor; V037 may temporarily raise the number
// under network pressure and slowly return toward the configured value.
#ifndef AITL_ADAPTIVE_MAX_JPEG_QUALITY
#define AITL_ADAPTIVE_MAX_JPEG_QUALITY 50
#endif
#ifndef AITL_ADAPTIVE_PRESSURE_STEP
#define AITL_ADAPTIVE_PRESSURE_STEP 2
#endif
#ifndef AITL_ADAPTIVE_FAILURE_STEP
#define AITL_ADAPTIVE_FAILURE_STEP 6
#endif
#ifndef AITL_ADAPTIVE_HIGH_SEND_PERCENT
#define AITL_ADAPTIVE_HIGH_SEND_PERCENT 85U
#endif
#ifndef AITL_ADAPTIVE_LOW_SEND_PERCENT
#define AITL_ADAPTIVE_LOW_SEND_PERCENT 35U
#endif
#ifndef AITL_ADAPTIVE_MIN_HIGH_SEND_MS
#define AITL_ADAPTIVE_MIN_HIGH_SEND_MS 20U
#endif
#ifndef AITL_ADAPTIVE_MIN_LOW_SEND_MS
#define AITL_ADAPTIVE_MIN_LOW_SEND_MS 8U
#endif
#ifndef AITL_ADAPTIVE_LARGE_FRAME_BYTES
#define AITL_ADAPTIVE_LARGE_FRAME_BYTES 6500U
#endif
#ifndef AITL_ADAPTIVE_RECOVERY_FRAME_BYTES
#define AITL_ADAPTIVE_RECOVERY_FRAME_BYTES 3600U
#endif
#ifndef AITL_ADAPTIVE_RECOVERY_SUCCESS_FRAMES
#define AITL_ADAPTIVE_RECOVERY_SUCCESS_FRAMES 30U
#endif


// R4 single-window + adaptive-resolution controller: the classic ESP32 Arduino/lwIP default TCP
// send buffer is about 5744 bytes. Keeping a JPEG below this target lets the
// whole ATL1+JPEG record be queued without waiting for a second ACK window.
#ifndef AITL_ADAPTIVE_TARGET_FRAME_BYTES
#define AITL_ADAPTIVE_TARGET_FRAME_BYTES 5000U
#endif
#ifndef AITL_ADAPTIVE_MIN_TARGET_FRAME_BYTES
#define AITL_ADAPTIVE_MIN_TARGET_FRAME_BYTES 3800U
#endif
#ifndef AITL_ADAPTIVE_WINDOW_MARGIN_BYTES
#define AITL_ADAPTIVE_WINDOW_MARGIN_BYTES 512U
#endif
#ifndef AITL_ADAPTIVE_OVERSIZE_STEP_MAX
#define AITL_ADAPTIVE_OVERSIZE_STEP_MAX 10
#endif
#ifndef AITL_ADAPTIVE_LOCAL_RETRY_MS
#define AITL_ADAPTIVE_LOCAL_RETRY_MS 5U
#endif
#ifndef AITL_ADAPTIVE_RECOVERY_HEADROOM_PERCENT
#define AITL_ADAPTIVE_RECOVERY_HEADROOM_PERCENT 72U
#endif
#ifndef AITL_ADAPTIVE_HARD_FRAME_BYTES
#define AITL_ADAPTIVE_HARD_FRAME_BYTES 6500U
#endif
#ifndef AITL_ADAPTIVE_RESOLUTION_RECOVERY_FRAMES
#define AITL_ADAPTIVE_RESOLUTION_RECOVERY_FRAMES 60U
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
