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
                PC Studio tests the selected ESP control endpoint, firmware protocol, Wi-Fi telemetry, direct ATL1/JPEG transport,
                streaming while status requests are active, and the normal PC Studio stream worker.
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
            The test temporarily pauses the selected physical stream and simulation if needed, runs at 5 FPS for diagnosis, then
            restores the previous saved FPS/settings and connection state. Your saved profile values are restored after the run.
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
              Running staged checks. This normally takes about 20–30 seconds; keep the ESP powered and on the same LAN.
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
                <div><span>Control latency</span><code>{displayNumber(report.metrics.control_avg_ms, " ms")}</code></div>
                <div><span>RSSI range</span><code>{report.metrics.rssi_min ?? "—"} .. {report.metrics.rssi_max ?? "—"} dBm</code></div>
                <div><span>BSSID</span><code>{report.metrics.wifi_bssid ?? "—"}</code></div>
                <div><span>Direct stream</span><code>{report.metrics.direct_clean_frames} frames / {report.metrics.direct_clean_fps.toFixed(2)} FPS</code></div>
                <div><span>Direct disconnects / invalid JPEGs</span><code>{report.metrics.direct_clean_disconnects} / {report.metrics.direct_clean_bad_frames}</code></div>
                <div><span>With status polling</span><code>{report.metrics.direct_polled_frames} frames / {report.metrics.direct_polled_disconnects} disconnects / {report.metrics.direct_polled_bad_frames} invalid</code></div>
                <div><span>PC Studio worker</span><code>{report.metrics.managed_frames} frames / {report.metrics.managed_failed_fetches} failures</code></div>
                <div><span>ESP send failures added</span><code>{report.metrics.device_send_failures_delta}</code></div>
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
