import { useEffect, useMemo, useState } from "react";
import {
  fetchCameraDiagnosticProgress,
  runCameraDiagnostics,
  type CameraDiagnosticCheckStatus,
  type CameraDiagnosticFindingSeverity,
  type CameraDiagnosticProgress,
  type CameraDiagnosticReport,
  type CameraLoadPhase,
} from "../lib/cameraDiagnosticsApi";
import { fetchRemoteCameraStatus, type RemoteCameraStatus } from "../lib/remoteCameraApi";

function checkPillClass(status: CameraDiagnosticCheckStatus): string {
  if (status === "pass") return "status-pill status-implemented";
  if (status === "fail") return "status-pill status-planned";
  if (status === "warn") return "status-pill status-info";
  return "status-pill muted";
}

function benchmarkPillClass(status: string): string {
  if (status === "PASS") return "status-pill status-implemented";
  if (status === "FAIL") return "status-pill status-planned";
  return "status-pill muted";
}

function overallPillClass(report: CameraDiagnosticReport): string {
  if (report.overall === "healthy") return "status-pill status-implemented";
  if (report.overall === "failed") return "status-pill status-planned";
  return "status-pill status-info";
}

function findingPillClass(severity: CameraDiagnosticFindingSeverity): string {
  if (severity === "critical") return "status-pill status-planned";
  if (severity === "warning") return "status-pill status-info";
  return "status-pill muted";
}

function displayNumber(value: number | null | undefined, suffix = "", decimals?: number): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  const text = decimals === undefined ? String(value) : value.toFixed(decimals);
  return `${text}${suffix}`;
}

function phaseResult(phase: CameraLoadPhase): string {
  const ratio = phase.fps_ratio === undefined ? "" : ` / ${Math.round(phase.fps_ratio * 100)}% target`;
  return `${phase.measured_fps.toFixed(2)} FPS${ratio}`;
}

function engineLabel(progress: CameraDiagnosticProgress | null): string {
  if (!progress?.engine) return "Detecting";
  if (progress.engine === "transport_benchmark") return "R5 transport + timing benchmark";
  if (progress.engine === "standard") return "Production camera diagnostics";
  return progress.engine;
}

export function CameraDiagnosticsPage() {
  const [remote, setRemote] = useState<RemoteCameraStatus | null>(null);
  const [report, setReport] = useState<CameraDiagnosticReport | null>(null);
  const [progress, setProgress] = useState<CameraDiagnosticProgress | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchRemoteCameraStatus()
      .then(setRemote)
      .catch((nextError) => setError(nextError instanceof Error ? nextError.message : "Camera status could not be loaded."));
  }, []);

  useEffect(() => {
    if (!running) return;
    let cancelled = false;

    async function poll() {
      try {
        const next = await fetchCameraDiagnosticProgress();
        if (!cancelled) setProgress(next);
      } catch {
        // The main /run request remains authoritative. A transient progress-poll
        // failure must not abort an otherwise healthy diagnostic run.
      }
    }

    void poll();
    const timer = window.setInterval(() => void poll(), 500);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [running]);

  const activeProfile = useMemo(
    () => remote?.cameras.find((camera) => camera.source_id === remote.active_source_id) ?? null,
    [remote],
  );

  async function diagnose() {
    setRunning(true);
    setError(null);
    setReport(null);
    setProgress({
      status: "running",
      engine: "probing",
      stage: "Preflight",
      current_test: "Detecting selected ESP diagnostic capability",
      test_index: null,
      frame_current: null,
      frame_total: null,
      detail: null,
      last_line: null,
      started_at_ms: Date.now(),
      elapsed_ms: 0,
      error: null,
      log_tail: [],
    });
    try {
      const next = await runCameraDiagnostics();
      setReport(next);
      setRemote(await fetchRemoteCameraStatus());
      try {
        setProgress(await fetchCameraDiagnosticProgress());
      } catch {
        // The completed report is enough if the final progress fetch races a backend reload.
      }
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Camera diagnosis failed to run.");
      try {
        setProgress(await fetchCameraDiagnosticProgress());
      } catch {
        // Preserve the primary diagnostic error.
      }
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="page-stack">
      <div className="two-column-grid">
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Deep one-click camera test</h2>
              <p className="placeholder-copy">
                One button automatically selects the correct diagnostic engine. Normal AiTL firmware runs the production
                control/stability/managed-worker checks; R5 benchmark firmware runs the full transport matrix and then a
                targeted real-frame timing follow-up to separate camera acquisition, socket send time and still-unexplained frame time.
              </p>
            </div>
            <span className="status-pill status-info">V038 R7 timing</span>
          </div>

          <div className="settings-list">
            <div><span>Selected camera</span><code>{activeProfile?.source_id ?? "none"}</code></div>
            <div><span>ESP address</span><code>{activeProfile?.host ?? "not configured"}</code></div>
            <div><span>Saved target FPS</span><code>{activeProfile?.target_fps ?? "—"}</code></div>
            <div><span>Current state</span><code>{activeProfile?.streaming ? "streaming" : activeProfile?.connected ? "connected" : "idle"}</code></div>
          </div>

          <p className="small-note">
            The selected ESP is probed first. R5 transport firmware is benchmarked directly from this page, then four independent
            /capture requests are compared with the ESP-reported camera acquisition time. No ESP reflash is required for this timing follow-up.
          </p>

          <div className="button-row">
            <button className="primary" type="button" onClick={() => void diagnose()} disabled={running || !activeProfile}>
              {running ? "Testing camera..." : "Diagnose camera"}
            </button>
          </div>

          {!activeProfile && <p className="error-message">Save and select an ESP camera in Camera Sources first.</p>}
          {error && <p className="error-message">{error}</p>}

          {running && progress && (
            <div className="settings-list">
              <div><span>Diagnostic engine</span><code>{engineLabel(progress)}</code></div>
              <div><span>Current stage</span><code>{progress.stage}</code></div>
              <div><span>Current test</span><code>{progress.test_index ? `#${progress.test_index} ` : ""}{progress.current_test ?? "preparing"}</code></div>
              <div><span>Frame progress</span><code>{progress.frame_total ? `${progress.frame_current ?? 0} / ${progress.frame_total}` : "—"}</code></div>
              <div><span>Elapsed</span><code>{(progress.elapsed_ms / 1000).toFixed(1)} s</code></div>
              <div><span>Live detail</span><code>{progress.detail ?? progress.last_line ?? "starting"}</code></div>
            </div>
          )}
          {running && <p className="small-note">Keep the ESP powered and leave the Camera Diagnostics page open while the active phase changes above.</p>}
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Diagnosis</h2>
              <p className="placeholder-copy">The final result combines functional failures, stability margin and ranked bottleneck evidence.</p>
            </div>
            {report ? <span className={overallPillClass(report)}>{report.overall}</span> : <span className="status-pill muted">not run</span>}
          </div>
          {report ? (
            <>
              <h3>{report.title}</h3>
              <p>{report.summary}</p>
              <div className="settings-list">
                <div><span>Diagnosis code</span><code>{report.diagnosis_code}</code></div>
                <div><span>Confidence</span><code>{report.confidence}</code></div>
                <div><span>Functionality</span><code>{report.functionality.score}% ({report.functionality.passed}/{report.functionality.total})</code></div>
                <div><span>Stability</span><code>{report.stability.grade} / {report.stability.score}%</code></div>
                <div><span>Primary bottleneck</span><code>{report.bottleneck_analysis.primary_bottleneck}</code></div>
                <div><span>Duration</span><code>{(report.duration_ms / 1000).toFixed(1)} s</code></div>
                <div><span>State restored</span><code>{report.state_restored ? "yes" : "needs attention"}</code></div>
              </div>
            </>
          ) : (
            <p className="placeholder-copy">Press Diagnose camera to generate the detailed report.</p>
          )}
        </section>
      </div>

      {report && (
        <>
          {report.transport_benchmark && (
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>Full transport benchmark matrix</h2>
                  <p className="placeholder-copy">
                    Same-device comparison of fallback and isolation paths. Synthetic payloads are diagnostic controls and are not production recommendations.
                  </p>
                </div>
                <span className="status-pill status-info">{report.transport_benchmark.benchmark_revision}</span>
              </div>
              <div className="settings-list">
                {report.transport_benchmark.results.map((item) => (
                  <div key={item.key}>
                    <span>
                      <strong>{item.name}</strong><br />
                      <small>{item.transport} · {item.frames}/{item.requested_frames} frames · {item.detail}</small>
                    </span>
                    <span>
                      <code>{item.measured_fps === null ? "—" : `${item.measured_fps.toFixed(2)} FPS`}</code>{" "}
                      <span className={benchmarkPillClass(item.status)}>{item.status}</span>
                    </span>
                  </div>
                ))}
              </div>
              <div className="settings-list">
                <div><span>Recommended transport</span><code>{report.transport_benchmark.diagnosis.recommended_key ?? "none"}</code></div>
                <div><span>Benchmark diagnosis</span><code>{report.transport_benchmark.diagnosis.diagnosis_code}</code></div>
                <div><span>Likely bottleneck</span><code>{report.transport_benchmark.diagnosis.likely_bottleneck}</code></div>
              </div>
              <p className="small-note"><strong>Recommended action:</strong> {report.transport_benchmark.diagnosis.recommendation}</p>
            </section>
          )}

          {report.pipeline_timing && (
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>Real-frame timing diagnosis</h2>
                  <p className="placeholder-copy">
                    The reliable transport candidate is decomposed into ESP camera acquisition, ESP socket-send time and the remaining unaccounted frame interval.
                  </p>
                </div>
                <span className="status-pill status-info">{report.pipeline_timing.dominant_remaining_stage.replace(/_/g, " ")}</span>
              </div>
              <div className="settings-list">
                <div><span>Timing confidence</span><code>{report.pipeline_timing.confidence}</code></div>
                <div><span>Candidate</span><code>{report.pipeline_timing.candidate_key}</code></div>
                <div><span>Target / achieved</span><code>{report.pipeline_timing.target_fps} / {report.pipeline_timing.candidate.measured_fps.toFixed(2)} FPS</code></div>
                <div><span>Target frame period</span><code>{displayNumber(report.pipeline_timing.target_period_ms, " ms", 1)}</code></div>
                <div><span>Observed frame interval</span><code>{displayNumber(report.pipeline_timing.candidate.observed_interval_ms, " ms", 1)}</code></div>
                <div><span>ESP capture avg / p95</span><code>{displayNumber(report.pipeline_timing.candidate.capture_ms.avg ?? report.pipeline_timing.capture_probe.esp_capture_ms.avg, "", 1)} / {displayNumber(report.pipeline_timing.candidate.capture_ms.p95 ?? report.pipeline_timing.capture_probe.esp_capture_ms.p95, " ms", 1)}</code></div>
                <div><span>ESP send avg / p95</span><code>{displayNumber(report.pipeline_timing.candidate.send_ms.avg, "", 1)} / {displayNumber(report.pipeline_timing.candidate.send_ms.p95, " ms", 1)}</code></div>
                <div><span>Capture + send accounted</span><code>{displayNumber(report.pipeline_timing.accounted_ms, " ms", 1)}</code></div>
                <div><span>Still unexplained</span><code>{displayNumber(report.pipeline_timing.unexplained_ms, " ms", 1)}{report.pipeline_timing.unexplained_ratio === null ? "" : ` (${Math.round(report.pipeline_timing.unexplained_ratio * 100)}%)`}</code></div>
                <div><span>HTTP /capture request avg</span><code>{displayNumber(report.pipeline_timing.capture_probe.request_ms.avg, " ms", 1)}</code></div>
                <div><span>Request time outside camera acquisition</span><code>{displayNumber(report.pipeline_timing.capture_probe.request_minus_capture_ms.avg, " ms", 1)}</code></div>
                <div><span>Synthetic send control</span><code>{report.pipeline_timing.synthetic_send ? `${report.pipeline_timing.synthetic_send.measured_fps.toFixed(2)} FPS / ${displayNumber(report.pipeline_timing.synthetic_send.send_ms.avg, " ms", 1)}` : "—"}</code></div>
              </div>
              {report.pipeline_timing.conclusions.length > 0 && <><h3>Timing conclusions</h3><ul>{report.pipeline_timing.conclusions.map((item) => <li key={item}>{item}</li>)}</ul></>}
              <p className="small-note"><strong>Next targeted action:</strong> {report.pipeline_timing.next_action}</p>
            </section>
          )}

          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>Functionality & layer checks</h2>
                <p className="placeholder-copy">Protocol, camera readiness, transport paths, session behavior, image integrity and restore/cleanup are checked separately.</p>
              </div>
              <span className="status-pill muted">{report.checks.length} checks</span>
            </div>
            <div className="settings-list">
              {report.checks.map((check) => (
                <div key={check.id}>
                  <span><strong>{check.label}</strong><br /><small>{check.detail}</small></span>
                  <span className={checkPillClass(check.status)}>{check.status}</span>
                </div>
              ))}
            </div>
          </section>

          <div className="two-column-grid">
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>Sustained stability</h2>
                  <p className="placeholder-copy">Longer operation or the selected benchmark candidate reveals disconnects, timing degradation and stale-frame stalls.</p>
                </div>
                <span className={report.stability.grade === "stable" ? "status-pill status-implemented" : report.stability.grade === "unstable" ? "status-pill status-planned" : "status-pill status-info"}>
                  {report.stability.grade}
                </span>
              </div>
              <div className="settings-list">
                <div><span>Stability score</span><code>{report.stability.score}%</code></div>
                <div><span>Target / achieved</span><code>{report.metrics.stability_target_fps} / {report.metrics.stability_measured_fps.toFixed(2)} FPS</code></div>
                <div><span>Frame interval p95</span><code>{displayNumber(report.metrics.stability_interval_p95_ms, " ms", 1)}</code></div>
                <div><span>Worst frame interval</span><code>{displayNumber(report.metrics.stability_interval_max_ms, " ms", 1)}</code></div>
                <div><span>Interval jitter</span><code>{displayNumber(report.metrics.stability_jitter_ms, " ms", 1)}</code></div>
                <div><span>Long stalls</span><code>{report.metrics.stability_stall_intervals}</code></div>
                <div><span>Disconnects / sequence gaps</span><code>{report.metrics.stability_disconnects} / {report.metrics.stability_sequence_gaps}</code></div>
                <div><span>Invalid JPEGs</span><code>{report.metrics.stability_bad_frames}</code></div>
              </div>
            </section>

            <section className="panel">
              <div className="panel-header"><div><h2>Candidate isolation matrix</h2><p className="placeholder-copy">Separates camera-independent TCP, camera load, direct PSRAM sending, DRAM staging/copy, MJPEG/UDP fallbacks and the production managed receiver where applicable.</p></div><span className="status-pill muted">{report.candidate_isolation.supported ? report.candidate_isolation.primary_candidate : "firmware support required"}</span></div>
              {!report.candidate_isolation.supported ? <p className="error-message">Flash a compatible diagnostic-isolation ESP firmware, then rerun Diagnose camera.</p> : <>
                <div className="settings-list">{Object.entries(report.candidate_isolation.matrix).map(([name, passed]) => <div key={name}><span>{name.replace(/_/g," ")}</span><code>{passed ? "PASS" : "FAIL"}</code></div>)}</div>
                {report.candidate_isolation.findings.map((item) => <div key={item.code} className="small-note"><strong>{item.code}</strong> — {item.evidence}<br />Action: {item.action}</div>)}
                {report.candidate_isolation.ruled_out.length > 0 && <p className="small-note">Ruled out: {report.candidate_isolation.ruled_out.join("; ")}</p>}
              </>}
            </section>

            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>Bottleneck analysis</h2>
                  <p className="placeholder-copy">Findings are ranked from the strongest limiting evidence to secondary warnings.</p>
                </div>
                <span className="status-pill muted">{report.bottleneck_analysis.findings.length} findings</span>
              </div>
              {report.bottleneck_analysis.findings.length ? (
                <div className="settings-list">
                  {report.bottleneck_analysis.findings.map((finding) => (
                    <div key={finding.id}>
                      <span>
                        <strong>{finding.title}</strong><br />
                        <small>{finding.evidence} {finding.impact}</small><br />
                        <small>Action: {finding.recommendation}</small>
                      </span>
                      <span className={findingPillClass(finding.severity)}>{finding.layer}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="success-message">No material bottleneck was detected within the tested load range.</p>
              )}
              <div className="settings-list">
                <div><span>Estimated sustainable target</span><code>{report.bottleneck_analysis.estimated_sustainable_target_fps || "—"} FPS</code></div>
                <div><span>Peak measured frame rate</span><code>{report.bottleneck_analysis.peak_measured_fps.toFixed(2)} FPS</code></div>
                <div><span>Peak measured throughput</span><code>{report.bottleneck_analysis.peak_throughput_mbps.toFixed(3)} Mbps</code></div>
              </div>
            </section>
          </div>

          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>FPS / throughput load ladder</h2>
                <p className="placeholder-copy">The selected production candidate is compared across available target FPS points using the same benchmark image settings.</p>
              </div>
            </div>
            <div className="settings-list">
              {report.load_ladder.length > 0 ? report.load_ladder.map((phase, index) => (
                <div key={`${phase.target_fps}-${index}`}>
                  <span><strong>{phase.target_fps} FPS target</strong><br /><small>{phase.frames} frames · payload avg {displayNumber(phase.payload_avg_bytes, " B")} · p95 interval {displayNumber(phase.interval_p95_ms, " ms", 1)}</small></span>
                  <code>{phaseResult(phase)} · {displayNumber(phase.throughput_mbps, " Mbps", 3)}</code>
                </div>
              )) : <p className="placeholder-copy">No stable candidate reached the follow-up load ladder.</p>}
            </div>
          </section>

          <div className="two-column-grid">
            <section className="panel">
              <div className="panel-header"><div><h2>Control & transport evidence</h2><p className="placeholder-copy">Measured evidence behind the classifier.</p></div></div>
              <div className="settings-list">
                <div><span>HTTP control</span><code>{report.metrics.control_successes} ok / {report.metrics.control_failures} fail</code></div>
                <div><span>Control avg / p95 / max</span><code>{displayNumber(report.metrics.control_avg_ms, "", 1)} / {displayNumber(report.metrics.control_p95_ms, "", 1)} / {displayNumber(report.metrics.control_max_ms, " ms", 1)}</code></div>
                <div><span>Control jitter</span><code>{displayNumber(report.metrics.control_jitter_ms, " ms", 1)}</code></div>
                <div><span>RSSI range / BSSID</span><code>{report.metrics.rssi_min ?? "—"}..{report.metrics.rssi_max ?? "—"} dBm / {report.metrics.wifi_bssid ?? "—"}</code></div>
                <div><span>Status-poll coexistence</span><code>{report.metrics.direct_polled_fps.toFixed(2)} FPS / {report.metrics.status_poll_failures} poll failures</code></div>
                <div><span>Managed PC Studio</span><code>{report.metrics.managed_fps.toFixed(2)} FPS / {report.metrics.managed_failed_fetches} failures / {report.metrics.managed_reconnects} reconnects</code></div>
                <div><span>Active ESP send failures / deadlines</span><code>{report.metrics.device_send_failures_delta} / {report.metrics.device_deadline_drops_delta}</code></div>
                <div><span>Diagnostic boundary resets excluded</span><code>{report.metrics.phase_boundary_send_resets}</code></div>
                <div><span>ESP send EWMA</span><code>{displayNumber(report.metrics.send_ewma_ms, " ms", 1)}</code></div>
                <div><span>Last accepted / frame bytes</span><code>{report.metrics.last_send_accepted_bytes ?? "—"} / {report.metrics.last_frame_bytes ?? "—"}</code></div>
              </div>
              <p className="small-note">R5 benchmark firmware intentionally isolates transports. The managed PC Studio worker is verified after the selected fix is moved back into normal compatible firmware.</p>
            </section>

            <section className="panel">
              <div className="panel-header"><div><h2>What to do next</h2><p className="placeholder-copy">Actions are tied to the strongest evidence from this run.</p></div></div>
              {report.likely_causes.length > 0 && <><h3>Likely causes</h3><ul>{report.likely_causes.map((cause) => <li key={cause}>{cause}</li>)}</ul></>}
              <h3>Recommended action</h3>
              <ul>{report.recommendations.map((recommendation) => <li key={recommendation}>{recommendation}</li>)}</ul>
              {!report.state_restored && report.restore_error && <p className="error-message">Restore warning: {report.restore_error}</p>}
              <p className="small-note">Run ID: <code>{report.run_id}</code></p>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
