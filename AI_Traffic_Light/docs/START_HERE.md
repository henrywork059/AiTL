# Start Here — V039

V039 / `0_3_9` is the current unaccepted candidate. V038 / `0_3_8` is the previous candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline.

## Normal Windows workflow

For routine update, validation and launch, use the same command from any PowerShell working directory:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

V039 makes this workflow idempotent. After the fast-forward update and full validation sequence, the helper may stop an existing listener on ports 8000/5173 only when Win32 process metadata identifies it as belonging to this AiTL PC Studio backend/frontend process tree. An unrelated process using either port is never terminated automatically and still blocks startup with a safety error. Runtime/user data is preserved.

## Camera transport

V039 keeps the V038/R10 camera-diagnostics work and the existing quality-preserving V037/R6 production ESP firmware and `aitl-tcp-jpeg-v1` transport:

```text
PC Connect -> ESP /status only
PC Start -> /config -> /start -> persistent TCP :81
ESP -> ATL1 header + configured JPEG
selected ESP -> CameraFrameService -> preview / Live AI / capture / zones / analytics
```

Configured JPEG quality and resolution remain fixed across production transport pressure. The production camera firmware still reports the V037-compatible identity/protocol; V039 does not change the production camera wire format.

## One-click Camera Diagnostics

Open **Operate → Camera Test** after saving/selecting an ESP in Camera Sources. Press **Diagnose camera** once. PC Studio automatically chooses the appropriate diagnostic path for production, R5/R8 transport, R9 architecture, or R10 tuning firmware.

R10's dedicated diagnostic sketch can sweep framebuffer count/grab mode, 3/5/10/15 FPS, newest-frame caching, JPEG quality, TCP write size, transfer size and repeatability, then restore the pre-test camera state. R10 remains diagnostic-only and does not replace production firmware.

The report provides measured evidence, likely bottleneck classification and a recommended prototype profile while preserving the local/student-scale simulation-only safety boundary.
