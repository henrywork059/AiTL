// AiTL V0310 production camera pipeline.
//
// R10 physical tuning selected one framebuffer with CAMERA_GRAB_LATEST and
// showed materially better raw-TCP throughput with larger application writes.
// Keep the proven ATL1 wire format and existing control/session contract, but
// adapt the V037 implementation at compile time so V0310 can be tested without
// duplicating the mature camera/session code.

#include <Arduino.h>
#include <errno.h>
#include <sys/uio.h>
#include <esp_camera.h>
#include <lwip/sockets.h>

namespace {

// R10's best tested raw-TCP application write size. TCP/lwIP remains free to
// segment this into MSS-sized packets; this is an application write ceiling,
// not an MTU assumption.
constexpr size_t kV0310SendChunkBytes = 11680U;

// Capture the legacy DRAM fallback value before the macro below rewrites the
// V037 PSRAM path. V0310's physical acceptance target is the normal PSRAM
// ESP32-CAM path; non-PSRAM fallback remains WHEN_EMPTY.
constexpr camera_grab_mode_t kV0310FallbackGrabMode = CAMERA_GRAB_WHEN_EMPTY;

camera_grab_mode_t aitlV0310GrabMode() {
  return psramFound() ? CAMERA_GRAB_LATEST : kV0310FallbackGrabMode;
}

// The inherited sender calls sendmsg() with a 16-byte ATL1 header plus the JPEG
// iovec. R5/R10 evidence favored plain send() and larger application batches.
// This compatibility shim presents at most 11,680 bytes of progress per outer
// call using plain non-blocking send(), while preserving the inherited bounded
// timeout/progress/reconnect behavior.
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

      // If the header or an earlier iovec already made progress, report that
      // progress to the inherited sender and let its next iteration handle the
      // socket state. Otherwise preserve errno/-1 exactly.
      return accepted > 0 ? accepted : -1;
    }
  }

  return accepted;
}

}  // namespace

// esp_camera.h and the socket headers are already parsed above, so these token
// overrides affect only the inherited V037 implementation body.
#define sendmsg aitlV0310Sendmsg
#define CAMERA_GRAB_WHEN_EMPTY aitlV0310GrabMode()
#define setup aitlV0310InheritedSetup
#include "main.cpp"
#undef setup
#undef CAMERA_GRAB_WHEN_EMPTY
#undef sendmsg

void setup() {
  aitlV0310InheritedSetup();
  Serial.printf(
      "AiTL V0310 R10-tuned production pipeline active: fb=1 grab=latest send_chunk=%u ATL1-compatible\n",
      static_cast<unsigned int>(kV0310SendChunkBytes));
}
