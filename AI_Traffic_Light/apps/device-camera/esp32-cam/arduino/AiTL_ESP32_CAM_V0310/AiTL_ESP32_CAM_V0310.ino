// AiTL V0310 standalone Arduino IDE production camera pipeline.
//
// This sketch intentionally reuses the mature V037 control/session/ATL1
// implementation and changes only the R10-supported hot-path choices:
//   - PSRAM: fb_count=1 + CAMERA_GRAB_LATEST
//   - plain non-blocking send() instead of real sendmsg()
//   - maximum 11,680 bytes per application write
// Saved resolution/JPEG quality/FPS remain PC-controlled.

#include <Arduino.h>
#include <errno.h>
#include <sys/uio.h>
#include <esp_camera.h>
#include <lwip/sockets.h>

#if __has_include("secrets.h")
#include "secrets.h"
#endif

namespace {

constexpr size_t kV0310SendChunkBytes = 11680U;
constexpr camera_grab_mode_t kV0310FallbackGrabMode = CAMERA_GRAB_WHEN_EMPTY;

camera_grab_mode_t aitlV0310GrabMode() {
  return psramFound() ? CAMERA_GRAB_LATEST : kV0310FallbackGrabMode;
}

ssize_t aitlV0310Sendmsg(int fd, const msghdr* message, int flags) {
  if (!message || !message->msg_iov || message->msg_iovlen == 0) {
    errno = EINVAL;
    return -1;
  }

  size_t budget = kV0310SendChunkBytes;
  ssize_t accepted = 0;

  for (size_t index = 0; index < message->msg_iovlen && budget > 0; ++index) {
    const auto* cursor = static_cast<const uint8_t*>(message->msg_iov[index].iov_base);
    size_t remaining = message->msg_iov[index].iov_len;

    while (remaining > 0 && budget > 0) {
      const size_t requested = remaining < budget ? remaining : budget;
      const ssize_t result = ::send(fd, cursor, requested, flags);

      if (result > 0) {
        const size_t progress = static_cast<size_t>(result);
        accepted += result;
        cursor += progress;
        remaining -= progress;
        budget -= progress;
        if (progress < requested) return accepted;
        continue;
      }

      if (result == 0) return accepted > 0 ? accepted : 0;
      return accepted > 0 ? accepted : -1;
    }
  }

  return accepted;
}

}  // namespace

// System headers are already parsed above. These token overrides therefore
// alter only the inherited V037 implementation body and keep its ATL1 wire
// format plus Connect / Start / Stop contract intact.
#define sendmsg aitlV0310Sendmsg
#define CAMERA_GRAB_WHEN_EMPTY aitlV0310GrabMode()
#define setup aitlV0310InheritedSetup
#include "../AiTL_ESP32_CAM_V037/AiTL_ESP32_CAM_V037.ino"
#undef setup
#undef CAMERA_GRAB_WHEN_EMPTY
#undef sendmsg

void setup() {
  aitlV0310InheritedSetup();
  Serial.printf(
      "AiTL V0310 R10-tuned production pipeline active: fb=1 grab=latest send_chunk=%u ATL1-compatible\n",
      static_cast<unsigned int>(kV0310SendChunkBytes));
}
