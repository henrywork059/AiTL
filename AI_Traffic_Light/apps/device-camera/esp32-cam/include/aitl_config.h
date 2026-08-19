#pragma once

#include <esp_camera.h>

#if __has_include("secrets.h")
#include "secrets.h"
#endif

// Safe build defaults. Copy secrets.example.h to secrets.h and replace these.
#ifndef AITL_WIFI_SSID
#define AITL_WIFI_SSID "CHANGE_ME"
#endif

#ifndef AITL_WIFI_PASSWORD
#define AITL_WIFI_PASSWORD "CHANGE_ME"
#endif

#ifndef AITL_SERVER_HOST
#define AITL_SERVER_HOST "CHANGE_ME"
#endif

#ifndef AITL_SERVER_PORT
#define AITL_SERVER_PORT 8000
#endif

#ifndef AITL_SOURCE_ID
#define AITL_SOURCE_ID "esp32_cam_01"
#endif

#ifndef AITL_DEVICE_HOSTNAME
#define AITL_DEVICE_HOSTNAME "aitl-cam-01"
#endif

// 250 ms = up to 4 frame uploads/second. Increase this if Wi-Fi or the PC is overloaded.
#ifndef AITL_FRAME_INTERVAL_MS
#define AITL_FRAME_INTERVAL_MS 250UL
#endif

// VGA is a practical first setting for an ESP32-CAM traffic-model prototype.
#ifndef AITL_FRAME_SIZE
#define AITL_FRAME_SIZE FRAMESIZE_VGA
#endif

// ESP32 camera JPEG quality uses a lower number for higher quality.
#ifndef AITL_JPEG_QUALITY
#define AITL_JPEG_QUALITY 12
#endif

#ifndef AITL_HTTP_TIMEOUT_MS
#define AITL_HTTP_TIMEOUT_MS 3500U
#endif

#ifndef AITL_WIFI_CONNECT_TIMEOUT_MS
#define AITL_WIFI_CONNECT_TIMEOUT_MS 20000UL
#endif

#ifndef AITL_WIFI_RETRY_MS
#define AITL_WIFI_RETRY_MS 5000UL
#endif

#ifndef AITL_CAMERA_RETRY_MS
#define AITL_CAMERA_RETRY_MS 5000UL
#endif

#ifndef AITL_SERIAL_STATUS_INTERVAL_MS
#define AITL_SERIAL_STATUS_INTERVAL_MS 10000UL
#endif
