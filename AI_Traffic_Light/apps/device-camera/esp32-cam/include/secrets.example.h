#pragma once

// Copy this file to "secrets.h" in the same folder before flashing.
// secrets.h is intentionally ignored by Git so Wi-Fi credentials stay local.

#define AITL_WIFI_SSID "YOUR_WIFI_NAME"
#define AITL_WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// Use the PC's LAN IPv4 address from ipconfig. Do not include http:// or a path.
#define AITL_SERVER_HOST "192.168.1.100"
#define AITL_SERVER_PORT 8000

// Each device should have a unique ID. Allowed: letters, numbers, dot, dash, underscore.
#define AITL_SOURCE_ID "esp32_cam_01"
#define AITL_DEVICE_HOSTNAME "aitl-cam-01"

// Optional tuning. Start with these values, then change only if needed.
#define AITL_FRAME_INTERVAL_MS 250UL
#define AITL_FRAME_SIZE FRAMESIZE_VGA
#define AITL_JPEG_QUALITY 12
