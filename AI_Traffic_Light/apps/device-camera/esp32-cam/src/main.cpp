#include <Arduino.h>

// ESP32-CAM firmware placeholder for AI Traffic Light project.
//
// Initial skeleton purpose:
// - reserve folder structure
// - document planned firmware direction
//
// Later implementation:
// - connect to Wi-Fi
// - initialize camera
// - host MJPEG stream at /stream
// - expose /status endpoint
// - allow resolution / JPEG quality settings

void setup() {
  Serial.begin(115200);
  Serial.println("AI Traffic Light ESP32-CAM placeholder firmware");
  Serial.println("Implement camera stream in a later version.");
}

void loop() {
  delay(1000);
}
