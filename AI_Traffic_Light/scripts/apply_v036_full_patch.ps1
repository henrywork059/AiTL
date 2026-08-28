$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ChangelogPath = Join-Path $ProjectRoot "CHANGELOG.md"
$ProjectVersionPath = Join-Path $ProjectRoot "apps\pc-studio\frontend\src\constants\projectVersion.ts"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

if (-not (Test-Path $ChangelogPath)) {
    throw "CHANGELOG.md not found at $ChangelogPath"
}

$projectVersion = @'
export const PROJECT_VERSION = "0_3_6";
export const PROJECT_VERSION_LABEL = "0_3_6 low-latency multi-ESP TCP streaming candidate";
'@
[System.IO.File]::WriteAllText($ProjectVersionPath, ($projectVersion.TrimEnd() + "`n"), $Utf8NoBom)

$baseSection = @'
## 0_3_6 — Low-latency binary TCP and multi-ESP streaming

- Created V036 / `0_3_6` after V035 to improve physical ESP32-CAM streaming speed and reduce end-to-end latency; V024 / `0_2_4` remains the owner-confirmed passed baseline.
- Replaced the ESP-to-PC multipart MJPEG hot path with a persistent length-prefixed binary TCP JPEG stream on port 81 while keeping HTTP port 80 for `/status`, `/config`, `/start`, `/stop`, and idle diagnostics.
- Added the `aitl-tcp-jpeg-v1` frame protocol with `ATL1` magic, JPEG length, source sequence, ESP uptime timestamp, and JPEG payload so the PC can read exact frames without multipart parsing or JPEG marker scanning.
- Preserved Connect as zero-image status/control only; Start still applies the complete PC-owned OV2640 configuration before opening image transport; Stop closes image transport before `/stop`.
- Added freshness-first bounded send deadlines on the ESP, absolute target-FPS scheduling, TCP_NODELAY/keepalive, PSRAM double buffering with `CAMERA_GRAB_LATEST`, and reconnect behavior that drops stalled partial streams instead of accumulating stale visual backlog.
- Added PC-side fixed-length ingestion, V036 firmware compatibility checks, faster stream-stall recovery, source-sequence/gap telemetry, and the existing event-driven backend MJPEG relay for browser preview.
- Updated the tracked PlatformIO firmware and added a matching standalone Arduino IDE sketch so both firmware paths use the same PC-pull V036 transport and require only Wi-Fi credentials, not the PC IP address.
- Same-candidate V036 multi-camera extension: PC Studio persists up to 12 ESP profiles with per-camera IP/FPS/OV2640 settings, runs one independent TCP worker/newest-frame cache per connected ESP, and lets the user select which ESP feeds the shared AI/capture pipeline without stopping other running streams.
- Same-candidate V036 source-switch hardening: changing the selected camera clears the former physical frame, promotes a cached target frame only when it is recent, invalidates cached bytes when a saved IP changes, retires replaced session generations so late old-device frames are rejected, and prevents stale/wrong-source frames from being presented as fresh Live AI or Dataset Capture input.
- Same-candidate V036 lifecycle hardening: backend shutdown disconnects all ESP sessions, saved camera configuration is ignored runtime data in `config/remote_cameras.json`, and focused regression covers independent streams, persistence, switching, stale-cache rejection, IP changes, isolated Stop, and multi-session shutdown.
- Same-candidate V036 ESP transport repair: use progress-bounded non-blocking TCP writes in 1360-byte chunks; temporary backpressure waits in short `select()` slices, successful partial writes reset a 250 ms no-progress timeout, and a 500 ms hard frame cap prevents indefinite stalls without truncating healthy JPEGs merely because they exceed one lwIP send-buffer window.
- Simulation still suspends physical image transfer and resumes it afterward. Multiple cameras do not create simultaneous independent live traffic controllers, ESP-side inference, or physical/public-road signal authority.
'@

$requiredBullets = @(
    ($baseSection -split "`r?`n") | Where-Object { $_ -like "- *" }
)


$existing = [System.IO.File]::ReadAllText($ChangelogPath)
if ($existing -notmatch '(?m)^## 0_3_6\b') {
    if ($existing -notmatch '^# Changelog\s*') {
        throw "CHANGELOG.md does not start with '# Changelog'"
    }
    $body = [regex]::Replace($existing, '^# Changelog\s*', '', 1)
    $updated = "# Changelog`n`n$($baseSection.TrimEnd())`n`n$($body.TrimStart())"
    [System.IO.File]::WriteAllText($ChangelogPath, ($updated.TrimEnd() + "`n"), $Utf8NoBom)
    Write-Host "[PASS] Added complete CHANGELOG.md section for 0_3_6"
}
else {
    $updated = $existing
    foreach ($bullet in $requiredBullets) {
        if ($updated -notmatch [regex]::Escape($bullet)) {
            $updated = [regex]::Replace(
                $updated,
                '(?m)^(## 0_3_6[^\r\n]*\r?\n)',
                ('$1' + "`n" + $bullet + "`n"),
                1
            )
        }
    }
    [System.IO.File]::WriteAllText($ChangelogPath, ($updated.TrimEnd() + "`n"), $Utf8NoBom)
    Write-Host "[PASS] CHANGELOG.md contains V036 multi-camera/review hardening notes"
}

Write-Host "[PASS] Frontend projectVersion.ts is 0_3_6"
Write-Host "[PASS] V036 full-patch metadata finalized"
