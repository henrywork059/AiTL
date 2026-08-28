import { useEffect, useState } from "react";
import { API_BASE } from "../api";
import { FunctionChecklist } from "../components/FunctionChecklist";
import { SimulationControls } from "../components/SimulationControls";
import {
  connectRemoteCamera,
  disconnectRemoteCamera,
  fetchRemoteCameraStatus,
  refreshCameraAfterRemoteChange,
  type RemoteCameraStatus,
} from "../lib/remoteCameraApi";
import { useSerialPolling } from "../lib/useSerialPolling";
import type { CameraStatus } from "../types";

type Props = {
  status: CameraStatus | null;
  onSimulationChange: (enabled: boolean) => void;
  onStatusChange: (status: CameraStatus) => void;
  changingMode: boolean;
};

function formatAge(ageMs: number | null): string {
  if (ageMs === null) return "No frame received";
  if (ageMs < 1000) return `${ageMs} ms ago`;
  return `${(ageMs / 1000).toFixed(1)} s ago`;
}

export function CameraSourcesPage({ status, onSimulationChange, onStatusChange, changingMode }: Props) {
  const [remote, setRemote] = useState<RemoteCameraStatus | null>(null);
  const [host, setHost] = useState("");
  const [sourceId, setSourceId] = useState("esp32_cam_01");
  const [busy, setBusy] = useState(false);
  const [streamFailed, setStreamFailed] = useState(false);
  const [remoteMessage, setRemoteMessage] = useState<string | null>(null);
  const [remoteError, setRemoteError] = useState<string | null>(null);

  useEffect(() => {
    void fetchRemoteCameraStatus()
      .then((next) => {
        setRemote(next);
        if (next.host) setHost(next.host);
        if (next.source_id) setSourceId(next.source_id);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    setStreamFailed(false);
  }, [remote?.host, remote?.connected]);

  useSerialPolling(
    async () => {
      const next = await fetchRemoteCameraStatus();
      setRemote(next);
    },
    1000,
    { onError: () => undefined },
  );

  const backendImageUrl = status?.frame_available
    ? `${API_BASE}/api/camera/frame?v=${status.frame_number}`
    : null;
  const directStreamUrl = remote?.connected && !status?.simulation_enabled && !streamFailed ? remote.stream_url : null;
  const imageUrl = directStreamUrl ?? backendImageUrl;

  const statusLabel = !status
    ? "checking"
    : status.simulation_enabled
      ? status.simulation_paused
        ? "simulation paused"
        : "simulation running"
      : remote?.configured
        ? remote.connected
          ? "ESP camera live"
          : "ESP reconnecting"
        : status.frame_available
          ? status.stale
            ? "frame stale"
            : "device frame live"
          : "waiting for device";

  async function connectEsp() {
    setBusy(true);
    setRemoteError(null);
    setRemoteMessage(null);
    try {
      const next = await connectRemoteCamera({
        host: host.trim(),
        source_id: sourceId.trim() || "esp32_cam_01",
        fetch_interval_ms: 500,
      });
      setRemote(next);
      onStatusChange(await refreshCameraAfterRemoteChange());
      setRemoteMessage(`Connected to ESP32-CAM at ${next.host}.`);
    } catch (error) {
      setRemoteError(error instanceof Error ? error.message : "ESP32-CAM connection failed.");
    } finally {
      setBusy(false);
    }
  }

  async function disconnectEsp() {
    setBusy(true);
    setRemoteError(null);
    setRemoteMessage(null);
    try {
      const next = await disconnectRemoteCamera();
      setRemote(next);
      onStatusChange(await refreshCameraAfterRemoteChange());
      setRemoteMessage("ESP32-CAM disconnected. The last received frame is retained until replaced.");
    } catch (error) {
      setRemoteError(error instanceof Error ? error.message : "ESP32-CAM could not be disconnected.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-stack">
      <div className="camera-layout">
        <section className="panel camera-preview-panel">
          <div className="panel-header">
            <div>
              <h2>Camera input</h2>
              <p className="placeholder-copy">
                Connect the ESP32-CAM by its private LAN IP, or use the built-in simulation when hardware is unavailable.
              </p>
            </div>
            <span className={`status-pill ${status?.stale ? "status-planned" : status?.frame_available ? "status-implemented" : ""}`}>
              {statusLabel}
            </span>
          </div>

          <div className="camera-frame-wrapper">
            {imageUrl ? (
              <img
                className="camera-frame"
                src={imageUrl}
                alt={`Latest frame from ${status?.active_source_id ?? remote?.source_id ?? "camera"}`}
                onError={directStreamUrl ? () => setStreamFailed(true) : undefined}
              />
            ) : (
              <div className="camera-empty-state">
                <strong>No frame available</strong>
                <p>Enter the ESP32-CAM IP and connect, start local simulation, or use the legacy upload receiver.</p>
              </div>
            )}
          </div>

          <div className="button-row">
            <button
              className="primary"
              onClick={() => onSimulationChange(!status?.simulation_enabled)}
              disabled={changingMode || !status}
            >
              {changingMode
                ? "Changing source..."
                : status?.simulation_enabled
                  ? "Stop simulation"
                  : "Start simulation"}
            </button>
          </div>

          {remote?.configured && status?.simulation_enabled && (
            <p className="small-note">
              ESP pulling is paused while simulation is active and resumes automatically when simulation stops.
            </p>
          )}

          <SimulationControls status={status} onStatusChange={onStatusChange} />
        </section>

        <aside className="side-column">
          <section className="panel compact-panel training-form">
            <div className="panel-header">
              <div>
                <h2>ESP32-CAM connection</h2>
                <p className="placeholder-copy">Use the IP printed by Arduino CameraWebServer in Serial Monitor.</p>
              </div>
              <span className={`status-pill ${remote?.connected ? "status-implemented" : ""}`}>
                {remote?.connected ? "connected" : remote?.configured ? "reconnecting" : "not connected"}
              </span>
            </div>

            <div className="form-grid">
              <label>
                ESP IPv4 address
                <input
                  value={host}
                  onChange={(event) => setHost(event.target.value)}
                  placeholder="192.168.1.87"
                  disabled={busy}
                />
              </label>
              <label>
                Source ID
                <input
                  value={sourceId}
                  onChange={(event) => setSourceId(event.target.value)}
                  placeholder="esp32_cam_01"
                  disabled={busy}
                />
              </label>
            </div>

            <div className="button-row">
              <button className="primary" type="button" onClick={() => void connectEsp()} disabled={busy || !host.trim()}>
                {busy ? "Working..." : remote?.configured ? "Reconnect" : "Connect"}
              </button>
              <button type="button" onClick={() => void disconnectEsp()} disabled={busy || !remote?.configured}>
                Disconnect
              </button>
            </div>

            {remoteMessage && <p className="success-message">{remoteMessage}</p>}
            {remoteError && <p className="error-message">{remoteError}</p>}
            {remote?.last_error && <p className="small-note">Last pull error: {remote.last_error}</p>}
          </section>

          <section className="panel compact-panel">
            <div className="panel-header"><h2>Input status</h2></div>
            <div className="camera-status-list">
              <div><span>Mode</span><strong>{status?.mode ?? "checking"}</strong></div>
              <div><span>Source</span><strong>{status?.active_source_id ?? "none"}</strong></div>
              <div><span>ESP address</span><strong>{remote?.host ?? "none"}</strong></div>
              <div><span>ESP pull</span><strong>{remote?.paused_for_simulation ? "paused for simulation" : remote?.connected ? "healthy" : remote?.configured ? "retrying" : "off"}</strong></div>
              <div><span>Resolution</span><strong>{status?.resolution ? `${status.resolution.width} × ${status.resolution.height}` : "unknown"}</strong></div>
              <div><span>Frame age</span><strong>{formatAge(status?.age_ms ?? null)}</strong></div>
              <div><span>Frame number</span><strong>#{status?.frame_number ?? 0}</strong></div>
              <div><span>ESP frames</span><strong>{remote?.successful_fetches ?? 0}</strong></div>
            </div>
          </section>

          <section className="panel compact-panel">
            <div className="panel-header"><h2>Compatibility</h2><span className="status-pill muted">local API</span></div>
            <p className="placeholder-copy">
              V032 adds PC-pull CameraWebServer support. The original raw JPEG/PNG upload endpoint remains available.
            </p>
            <code className="endpoint-code">POST {API_BASE}/api/camera/frame?source_id=esp_cam_01</code>
            <p className="small-note">Remote ESP addresses are restricted to private RFC1918 IPv4 ranges.</p>
          </section>
        </aside>
      </div>
      <FunctionChecklist area="Camera" />
    </div>
  );
}
