import { useEffect, useMemo, useState } from "react";
import {
  runCameraDiagnostics,
  type CameraDiagnosticCheckStatus,
  type CameraDiagnosticReport,
} from "../lib/cameraDiagnosticsApi";
import { fetchRemoteCameraStatus, type RemoteCameraStatus } from "../lib/remoteCameraApi";

function checkPillClass(status: CameraDiagnosticCheckStatus): string {
  if (status === "pass") return "status-pill status-implemented";
  if (status === "fail") return "status-pill status-planned";
  if (status === "warn") return "status-pill status-info";
  return "status-pill muted";
}

function overallPillClass(report: CameraDiagnosticReport): string {
  if (report.overall === "healthy") return "status-pill status-implemented";
  if (report.overall === "failed") return "status-pill status-planned";
  return "status-pill status-info";
}

function displayNumber(value: number | null, suffix = ""): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${value}${suffix}`;
}

export function CameraDiagnosticsPage() {
  const [remote, setRemote] = useState<RemoteCameraStatus | null>(null);
  const [report, setReport] = useState<CameraDiagnosticReport | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchRemoteCameraStatus()
      .then(setRemote)
      .catch((nextError) => setError(nextError instanceof Error ? nextError.message : "Camera status could not be loaded."));
  }, []);

  const activeProfile = useMemo(
    () => remote?.cameras.find((camera) => camera.source_id === remote.active_source_id) ?? null,
    [remote],
  );

  async function diagnose() {
    setRunning(true);
    setError(null);
    setReport(null);
    try {
      const next = await runCameraDiagnostics();
      setReport(next);
      setRemote(await fetchRemoteCameraStatus());
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Camera diagnosis failed to run.");
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
              <h2>One-click camera diagnosis</h2>
              <p className="placeholder-copy">
                PC Studio runs a detailed staged test of control responsiveness, camera lifecycle, direct ATL1/JPEG integrity,
                sustained throughput, latency/jitter, concurrent status traffic, reconnect behavior, and the normal PC Studio worker.
              </p>
            </div>
            <span className="status-pill status-info">V038</span>
          </div>

          <div className="settings-list">
            <div><span>Selected camera</span><code>{activeProfile?.source_id ?? "none"}</code></div>
            <div><span>ESP address</span><code>{activeProfile?.host ?? "not configured"}</code></div>
            <div><span>Saved target FPS</span><code>{activeProfile?.target_fps ?? "—"}</code></div>
            <div><span>Current state</span><code>{activeProfile?.streaming ? "streaming" : activeProfile?.connected ? "connected" : "idle"}</code></div>
          </div>

          <p className="small-note">
            The test temporarily pauses the selected physical stream and simulation if needed. It measures a conservative 5 FPS baseline,
            then tests the saved target up to 15 FPS for capacity/headroom, verifies reconnect and managed-worker behavior, and restores the previous state.
          </p>

          <div className="button-row">
            <button className="primary" type="button" onClick={() => void diagnose()} disabled={running || !activeProfile}>
              {running ? "Diagnosing camera..." : "Diagnose camera"}
            </button>
          </div>

          {!activeProfile && (
            <p className="error-message">Save and select an ESP camera in Camera Sources first.</p>
          )}
          {error && <p className="error-message">{error}</p>}
          {running && (
            <p className="small-note">
              Running detailed staged checks. This normally takes about 40–60 seconds; keep the ESP powered and on the same LAN.
            </p>
          )}
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Diagnosis</h2>
              <p className="placeholder-copy">The result identifies the most likely failing layer instead of only returning raw socket errors.</p>
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
                <div><span>Run ID</span><code>{report.run_id}</code></div>
                <div><span>Duration</span><code>{(report.duration_ms / 1000).toFixed(1)} s</code></div>
                <div><span>State restored</span><code>{report.state_restored ? "yes" : "needs attention"}</code></div>
              </div>
            </>
          ) : (
            <p className="placeholder-copy">Press Diagnose camera to generate a layer-by-layer report.</p>
          )}
        </section>
      </div>

      {report && (
        <>
          <div className="two-column-grid">
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>Functionality</h2>
                  <p className="placeholder-copy">End-to-end functions verified during this run.</p>
                </div>
              </div>
              <div className="settings-list">
                {Object.entries(report.functionality).map(([name, passed]) => (
                  <div key={name}><span>{name.replace(/_/g, " ")}</span><code>{passed ? "PASS" : "FAIL"}</code></div>
                ))}
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>Stability score</h2>
                  <p className="placeholder-copy">Combines failures, reconnects, RF events, throughput headroom, and frame timing.</p>
                </div>
                <span className={report.stability.score >= 75 ? "status-pill status-implemented" : report.stability.score >= 55 ? "status-pill status-info" : "status-pill status-planned"}>
                  {report.stability.score}/100 — {report.stability.grade}
                </span>
              </div>
              <div className="settings-list">
                <div><span>Load target / sustained</span><code>{report.stability.target_fps} / {report.stability.sustained_fps.toFixed(2)} FPS</code></div>
                <div><span>FPS headroom</span><code>{Math.round(report.stability.fps_headroom_ratio * 100)}%</code></div>
                <div><span>Frame interval p95 / max</span><code>{displayNumber(report.stability.frame_interval_p95_ms, " ms")} / {displayNumber(report.stability.frame_interval_max_ms, " ms")}</code></div>
                <div><span>Unexpected ESP send failures</span><code>{report.stability.unexpected_send_failures}</code></div>
                <div><span>Deadline drops</span><code>{report.stability.deadline_drops}</code></div>
                <div><span>Wi-Fi disconnect / reconnect</span><code>{report.stability.wifi_disconnects_delta} / {report.stability.wifi_reconnects_delta}</code></div>
              </div>
            </section>
          </div>

          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>Bottleneck analysis</h2>
                <p className="placeholder-copy">Measured constraints are attributed to the most likely layer instead of being reduced to one generic failure.</p>
              </div>
              <span className="status-pill muted">{report.bottlenecks.length} detected</span>
            </div>
            {report.bottlenecks.length === 0 ? (
              <p className="success-message">No material bottleneck was detected during this run.</p>
            ) : (
              <div className="settings-list">
                {report.bottlenecks.map((item, index) => (
                  <div key={`${item.layer}-${index}`}>
                    <span><strong>{item.layer}</strong><br /><small>{item.evidence}</small></span>
                    <span className={item.severity === "high" ? "status-pill status-planned" : "status-pill status-info"}>{item.severity}</span>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>Layer checks</h2>
                <p className="placeholder-copy">Each test isolates a different part of the camera connection path.</p>
              </div>
              <span className="status-pill muted">{report.checks.length} checks</span>
            </div>
            <div className="settings-list">
              {report.checks.map((check) => (
                <div key={check.id}>
                  <span>
                    <strong>{check.label}</strong>
                    <br />
                    <small>{check.detail}</small>
                  </span>
                  <span className={checkPillClass(check.status)}>{check.status}</span>
                </div>
              ))}
            </div>
          </section>

          <div className="two-column-grid">
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>Measured transport</h2>
                  <p className="placeholder-copy">Key evidence used by the diagnosis classifier.</p>
                </div>
              </div>
              <div className="settings-list">
                <div><span>HTTP control</span><code>{report.metrics.control_successes} ok / {report.metrics.control_failures} fail</code></div>
                <div><span>Control latency avg / p95 / max</span><code>{displayNumber(report.metrics.control_avg_ms, " ms")} / {displayNumber(report.metrics.control_p95_ms, " ms")} / {displayNumber(report.metrics.control_max_ms, " ms")}</code></div>
                <div><span>RSSI range</span><code>{report.metrics.rssi_min ?? "—"} .. {report.metrics.rssi_max ?? "—"} dBm</code></div>
                <div><span>BSSID</span><code>{report.metrics.wifi_bssid ?? "—"}</code></div>
                <div><span>Direct stream</span><code>{report.metrics.direct_clean_frames} frames / {report.metrics.direct_clean_fps.toFixed(2)} FPS</code></div>
                <div><span>Direct disconnects / invalid / sequence gaps</span><code>{report.metrics.direct_clean_disconnects} / {report.metrics.direct_clean_bad_frames} / {report.metrics.direct_clean_sequence_gaps}</code></div>
                <div><span>Direct frame interval p95</span><code>{displayNumber(report.metrics.direct_clean_p95_interval_ms, " ms")}</code></div>
                <div><span>With status polling</span><code>{report.metrics.direct_polled_frames} frames / {report.metrics.direct_polled_disconnects} disconnects / {report.metrics.direct_polled_bad_frames} invalid</code></div>
                <div><span>Load test</span><code>{report.metrics.load_fps.toFixed(2)} / {report.metrics.load_target_fps} FPS ({Math.round(report.metrics.load_fps_ratio * 100)}%)</code></div>
                <div><span>Load throughput / JPEG avg</span><code>{report.metrics.load_throughput_mbps.toFixed(3)} Mbps / {report.metrics.load_payload_avg_bytes} B</code></div>
                <div><span>Load interval p95 / max</span><code>{displayNumber(report.metrics.load_frame_interval_p95_ms, " ms")} / {displayNumber(report.metrics.load_frame_interval_max_ms, " ms")}</code></div>
                <div><span>Reconnect test</span><code>{report.metrics.reconnect_success ? "pass" : "fail"} / {displayNumber(report.metrics.reconnect_ms, " ms")}</code></div>
                <div><span>PC Studio worker</span><code>{report.metrics.managed_frames} frames / {report.metrics.managed_fps.toFixed(2)} FPS / {report.metrics.managed_failed_fetches} failures</code></div>
                <div><span>ESP send failures total / unexpected</span><code>{report.metrics.device_send_failures_delta} / {report.metrics.device_unexpected_send_failures_delta}</code></div>
                <div><span>Diagnostic transition resets</span><code>{report.metrics.diagnostic_transition_resets}</code></div>
                <div><span>ESP deadline drops added</span><code>{report.metrics.device_deadline_drops_delta}</code></div>
                <div><span>Last send errno</span><code>{report.metrics.last_send_errno ?? "—"}</code></div>
                <div><span>Last accepted bytes</span><code>{report.metrics.last_send_accepted_bytes ?? "—"}</code></div>
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>What to do next</h2>
                  <p className="placeholder-copy">Recommendations are based on the failing layer measured in this run.</p>
                </div>
              </div>

              {report.likely_causes.length > 0 && (
                <>
                  <h3>Likely causes</h3>
                  <ul>
                    {report.likely_causes.map((cause) => <li key={cause}>{cause}</li>)}
                  </ul>
                </>
              )}

              <h3>Recommended action</h3>
              <ul>
                {report.recommendations.map((recommendation) => <li key={recommendation}>{recommendation}</li>)}
              </ul>

              {!report.state_restored && report.restore_error && (
                <p className="error-message">Restore warning: {report.restore_error}</p>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
