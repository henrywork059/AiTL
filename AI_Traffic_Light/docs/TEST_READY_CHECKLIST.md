# V038 Acceptance Checklist

- [ ] `VERSION` is `0_3_8`; previous is `0_3_7`; passed baseline remains `0_2_4`.
- [ ] Existing V037/R6 ESP firmware remains accepted by V038; no wire-protocol change or mandatory reflash was introduced.
- [ ] Navigation contains **Camera Test / Camera Diagnostics** under Operate.
- [ ] A selected saved ESP is clearly shown before a diagnostic run.
- [ ] One **Diagnose camera** button runs the entire staged test without a separate Python/PowerShell diagnostic helper.
- [ ] The diagnostic route uses the standard API envelope and request ID.
- [ ] ESP control reachability, protocol compatibility, camera readiness and Wi-Fi telemetry are checked.
- [ ] Direct ATL1/JPEG streaming is measured while bypassing the normal PC Studio stream worker.
- [ ] A second direct stream phase adds `/status` polling so control/stream contention can be distinguished.
- [ ] The normal PC Studio managed stream path is then measured separately.
- [ ] ESP send-failure/deadline deltas, disconnect counts, FPS/frame counts, RSSI/BSSID and accepted-byte/errno telemetry are surfaced when available.
- [ ] Diagnosis distinguishes control unreachable, firmware mismatch, camera not ready, direct ESP camera/TCP stall, control-stream contention, PC Studio integration failure, weak Wi-Fi margin, and healthy-now cases.
- [ ] Diagnostic runs are mutually exclusive and cannot overlap against one selected ESP.
- [ ] The previous saved FPS/settings, connection/stream state and simulation state are restored after the run; restoration failure is displayed explicitly.
- [ ] Existing Camera Sources, Live AI, simulation, Dataset Capture, multi-ESP selection and V037/R6 transport regressions remain passing.
- [ ] Python compile, structure check, focused/inherited regressions, frontend typecheck/build and live smoke pass on the complete repository.
- [ ] Owner explicitly accepts V038 before `passed_baseline` changes.
