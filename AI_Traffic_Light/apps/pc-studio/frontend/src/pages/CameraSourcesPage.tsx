import { useEffect, useState } from "react";
import { API_BASE } from "../api";
import { FunctionChecklist } from "../components/FunctionChecklist";
import { SimulationControls } from "../components/SimulationControls";
import {
  connectRemoteCamera,
  DEFAULT_REMOTE_CAMERA_SETTINGS,
  disconnectRemoteCamera,
  fetchRemoteCameraStatus,
  liveCameraMjpegUrl,
  refreshCameraAfterRemoteChange,
  startRemoteCamera,
  stopRemoteCamera,
  type RemoteCameraSettings,
  type RemoteCameraStatus,
  type RemoteFrameSize,
} from "../lib/remoteCameraApi";
import { useSerialPolling } from "../lib/useSerialPolling";
import type { CameraStatus } from "../types";

type Props = {
  status: CameraStatus | null;
  onSimulationChange: (enabled: boolean) => void;
  onStatusChange: (status: CameraStatus) => void;
  changingMode: boolean;
};

const FRAME_SIZES: RemoteFrameSize[] = ["QQVGA", "HQVGA", "QVGA", "CIF", "VGA", "SVGA", "XGA", "SXGA", "UXGA"];

function formatAge(ageMs: number | null): string {
  if (ageMs === null) return "No frame received";
  if (ageMs < 1000) return `${ageMs} ms ago`;
  return `${(ageMs / 1000).toFixed(1)} s ago`;
}

function numberValue(value: string): number {
  return Number.parseInt(value, 10);
}

export function CameraSourcesPage({ status, onSimulationChange, onStatusChange, changingMode }: Props) {
  const [remote, setRemote] = useState<RemoteCameraStatus | null>(null);
  const [host, setHost] = useState("");
  const [sourceId, setSourceId] = useState("esp32_cam_01");
  const [targetFps, setTargetFps] = useState(15);
  const [settings, setSettings] = useState<RemoteCameraSettings>({ ...DEFAULT_REMOTE_CAMERA_SETTINGS });
  const [busy, setBusy] = useState(false);
  const [remoteMessage, setRemoteMessage] = useState<string | null>(null);
  const [remoteError, setRemoteError] = useState<string | null>(null);

  useEffect(() => {
    void fetchRemoteCameraStatus()
      .then((next) => {
        setRemote(next);
        if (next.host) setHost(next.host);
        if (next.source_id) setSourceId(next.source_id);
        if (next.settings) setSettings(next.settings);
        setTargetFps(next.target_fps);
      })
      .catch(() => undefined);
  }, []);

  useSerialPolling(
    async () => {
      const next = await fetchRemoteCameraStatus();
      setRemote(next);
      if (next.settings && next.streaming) setSettings(next.settings);
    },
    1000,
    { onError: () => undefined },
  );

  const useLivePreview = Boolean(remote?.streaming || status?.simulation_enabled);
  const imageUrl = useLivePreview
    ? liveCameraMjpegUrl()
    : status?.frame_available
      ? `${API_BASE}/api/camera/frame?v=${status.frame_number}`
      : null;

  const statusLabel = !status
    ? "checking"
    : status.simulation_enabled
      ? status.simulation_paused ? "simulation paused" : "simulation running"
      : remote?.streaming
        ? remote.paused_for_simulation ? "ESP paused for simulation" : "ESP streaming"
        : remote?.configured
          ? remote.device_reachable ? "ESP ready" : "ESP unreachable"
          : status.frame_available
            ? status.stale ? "frame stale" : "device frame live"
            : "waiting for device";

  function setSetting<K extends keyof RemoteCameraSettings>(key: K, value: RemoteCameraSettings[K]) {
    setSettings((current) => ({ ...current, [key]: value }));
  }

  async function connectEsp() {
    setBusy(true);
    setRemoteError(null);
    setRemoteMessage(null);
    try {
      const next = await connectRemoteCamera({
        host: host.trim(),
        source_id: sourceId.trim() || "esp32_cam_01",
      });
      setRemote(next);
      if (next.settings) setSettings(next.settings);
      setRemoteMessage(`ESP32-CAM ${next.host} is ready. No image transfer has started.`);
    } catch (error) {
      setRemoteError(error instanceof Error ? error.message : "ESP32-CAM connection failed.");
    } finally {
      setBusy(false);
    }
  }

  async function startEsp() {
    setBusy(true);
    setRemoteError(null);
    setRemoteMessage(null);
    try {
      const next = await startRemoteCamera({
        target_fps: targetFps,
        settings,
      });
      setRemote(next);
      if (next.settings) setSettings(next.settings);
      onStatusChange(await refreshCameraAfterRemoteChange());
      setRemoteMessage("Settings applied. Low-latency persistent MJPEG streaming started.");
    } catch (error) {
      setRemoteError(error instanceof Error ? error.message : "ESP32-CAM stream could not start.");
    } finally {
      setBusy(false);
    }
  }

  async function stopEsp() {
    setBusy(true);
    setRemoteError(null);
    setRemoteMessage(null);
    try {
      const next = await stopRemoteCamera();
      setRemote(next);
      onStatusChange(await refreshCameraAfterRemoteChange());
      setRemoteMessage("Streaming stopped. ESP remains connected but no image bytes are requested.");
    } catch (error) {
      setRemoteError(error instanceof Error ? error.message : "ESP32-CAM stream could not stop.");
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
      setRemoteMessage("ESP32-CAM disconnected.");
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
                The ESP waits idle after connection. PC Studio applies all camera settings and starts image requests only when you press Start Stream.
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
              />
            ) : (
              <div className="camera-empty-state">
                <strong>No frame available</strong>
                <p>Connect the ESP, choose camera settings, then press Start Stream. Simulation remains available without hardware.</p>
              </div>
            )}
          </div>

          <div className="button-row">
            <button
              className="primary"
              onClick={() => onSimulationChange(!status?.simulation_enabled)}
              disabled={changingMode || !status}
            >
              {changingMode ? "Changing source..." : status?.simulation_enabled ? "Stop simulation" : "Start simulation"}
            </button>
          </div>

          {remote?.streaming && status?.simulation_enabled && (
            <p className="small-note">
              ESP frame requests are paused while simulation is active and resume automatically after simulation stops.
            </p>
          )}

          <SimulationControls status={status} onStatusChange={onStatusChange} />
        </section>

        <aside className="side-column">
          <section className="panel compact-panel training-form">
            <div className="panel-header">
              <div>
                <h2>ESP32-CAM connection</h2>
                <p className="placeholder-copy">Connect establishes status/control only. It does not transfer images.</p>
              </div>
              <span className={`status-pill ${remote?.device_reachable ? "status-implemented" : ""}`}>
                {!remote?.configured ? "not connected" : remote.device_reachable ? "ready" : "unreachable"}
              </span>
            </div>

            <div className="form-grid">
              <label>
                ESP IPv4 address
                <input value={host} onChange={(event) => setHost(event.target.value)} placeholder="192.168.1.87" disabled={busy || remote?.streaming} />
              </label>
              <label>
                Source ID
                <input value={sourceId} onChange={(event) => setSourceId(event.target.value)} placeholder="esp32_cam_01" disabled={busy || remote?.streaming} />
              </label>
            </div>

            <div className="button-row">
              <button className="primary" type="button" onClick={() => void connectEsp()} disabled={busy || !host.trim() || remote?.streaming}>
                {busy ? "Working..." : remote?.configured ? "Reconnect" : "Connect"}
              </button>
              <button type="button" onClick={() => void disconnectEsp()} disabled={busy || !remote?.configured}>
                Disconnect
              </button>
            </div>
          </section>

          <section className="panel compact-panel training-form">
            <div className="panel-header">
              <div>
                <h2>Camera settings</h2>
                <p className="placeholder-copy">These values are sent to the ESP immediately before Start Stream activates the camera session.</p>
              </div>
              <span className="status-pill muted">{remote?.streaming ? "locked while streaming" : "PC controlled"}</span>
            </div>

            <div className="form-grid">
              <label>
                Resolution
                <select value={settings.frame_size} onChange={(event) => setSetting("frame_size", event.target.value as RemoteFrameSize)} disabled={busy || remote?.streaming}>
                  {FRAME_SIZES.map((size) => <option key={size} value={size}>{size}</option>)}
                </select>
              </label>
              <label>
                JPEG quality (4 best – 63 smallest)
                <input type="number" min={4} max={63} value={settings.jpeg_quality} onChange={(event) => setSetting("jpeg_quality", numberValue(event.target.value))} disabled={busy || remote?.streaming} />
              </label>
              <label>
                Target stream FPS
                <input type="number" min={1} max={30} step={1} value={targetFps} onChange={(event) => setTargetFps(numberValue(event.target.value))} disabled={busy || remote?.streaming} />
              </label>
              <label>
                Brightness (-2 to 2)
                <input type="number" min={-2} max={2} value={settings.brightness} onChange={(event) => setSetting("brightness", numberValue(event.target.value))} disabled={busy || remote?.streaming} />
              </label>
              <label>
                Contrast (-2 to 2)
                <input type="number" min={-2} max={2} value={settings.contrast} onChange={(event) => setSetting("contrast", numberValue(event.target.value))} disabled={busy || remote?.streaming} />
              </label>
              <label>
                Saturation (-2 to 2)
                <input type="number" min={-2} max={2} value={settings.saturation} onChange={(event) => setSetting("saturation", numberValue(event.target.value))} disabled={busy || remote?.streaming} />
              </label>
            </div>

            <details>
              <summary>Advanced OV2640 settings</summary>
              <div className="form-grid">
                <label>Special effect (0–6)<input type="number" min={0} max={6} value={settings.special_effect} onChange={(event) => setSetting("special_effect", numberValue(event.target.value))} disabled={busy || remote?.streaming} /></label>
                <label>White balance mode (0–4)<input type="number" min={0} max={4} value={settings.wb_mode} onChange={(event) => setSetting("wb_mode", numberValue(event.target.value))} disabled={busy || remote?.streaming} /></label>
                <label>AE level (-2 to 2)<input type="number" min={-2} max={2} value={settings.ae_level} onChange={(event) => setSetting("ae_level", numberValue(event.target.value))} disabled={busy || remote?.streaming} /></label>
                <label>AEC value (0–1200)<input type="number" min={0} max={1200} value={settings.aec_value} onChange={(event) => setSetting("aec_value", numberValue(event.target.value))} disabled={busy || remote?.streaming} /></label>
                <label>AGC gain (0–30)<input type="number" min={0} max={30} value={settings.agc_gain} onChange={(event) => setSetting("agc_gain", numberValue(event.target.value))} disabled={busy || remote?.streaming} /></label>
                <label>Gain ceiling (0–6)<input type="number" min={0} max={6} value={settings.gainceiling} onChange={(event) => setSetting("gainceiling", numberValue(event.target.value))} disabled={busy || remote?.streaming} /></label>
              </div>

              <div className="checklist">
                {([
                  ["awb", "Auto white balance"],
                  ["awb_gain", "Auto white-balance gain"],
                  ["aec", "Auto exposure"],
                  ["aec2", "AEC2 DSP"],
                  ["agc", "Auto gain"],
                  ["bpc", "Black-pixel correction"],
                  ["wpc", "White-pixel correction"],
                  ["raw_gma", "Raw gamma"],
                  ["lenc", "Lens correction"],
                  ["hmirror", "Horizontal mirror"],
                  ["vflip", "Vertical flip"],
                  ["dcw", "Downsize/crop"],
                  ["colorbar", "Color test bar"],
                ] as const).map(([key, label]) => (
                  <label key={key}>
                    <input
                      type="checkbox"
                      checked={settings[key]}
                      onChange={(event) => setSetting(key, event.target.checked)}
                      disabled={busy || remote?.streaming}
                    />
                    {label}
                  </label>
                ))}
              </div>
            </details>

            <div className="button-row">
              <button className="primary" type="button" onClick={() => void startEsp()} disabled={busy || !remote?.configured || !remote.device_reachable || remote.streaming}>
                Start Stream
              </button>
              <button type="button" onClick={() => void stopEsp()} disabled={busy || !remote?.streaming}>
                Stop Stream
              </button>
            </div>

            {remoteMessage && <p className="success-message">{remoteMessage}</p>}
            {remoteError && <p className="error-message">{remoteError}</p>}
            {remote?.last_error && <p className="small-note">Last ESP error: {remote.last_error}</p>}
          </section>

          <section className="panel compact-panel">
            <div className="panel-header"><h2>Input status</h2></div>
            <div className="camera-status-list">
              <div><span>ESP address</span><strong>{remote?.host ?? "none"}</strong></div>
              <div><span>Device</span><strong>{remote?.device_reachable ? "reachable" : remote?.configured ? "unreachable" : "not connected"}</strong></div>
              <div><span>ESP session</span><strong>{remote?.streaming ? "active" : "idle"}</strong></div>
              <div><span>Transport</span><strong>{remote?.paused_for_simulation ? "MJPEG paused" : remote?.streaming ? "persistent MJPEG" : "idle"}</strong></div>
              <div><span>Target FPS</span><strong>{remote?.target_fps ?? targetFps}</strong></div>
              <div><span>Measured FPS</span><strong>{remote?.measured_fps ? remote.measured_fps.toFixed(1) : "—"}</strong></div>
              <div><span>Stream reconnects</span><strong>{remote?.stream_reconnects ?? 0}</strong></div>
              <div><span>Stale frames dropped</span><strong>{remote?.dropped_stale_frames ?? 0}</strong></div>
              <div><span>Source</span><strong>{status?.active_source_id ?? "none"}</strong></div>
              <div><span>Resolution</span><strong>{status?.resolution ? `${status.resolution.width} × ${status.resolution.height}` : settings.frame_size}</strong></div>
              <div><span>Frame age</span><strong>{formatAge(status?.age_ms ?? null)}</strong></div>
              <div><span>Frames received</span><strong>{remote?.successful_fetches ?? 0}</strong></div>
            </div>
          </section>

          <section className="panel compact-panel">
            <div className="panel-header"><h2>Compatibility</h2><span className="status-pill muted">local prototype</span></div>
            <p className="placeholder-copy">
              V034 keeps PC-owned Start/Stop control but uses one persistent ESP MJPEG connection instead of repeated /capture HTTP requests.
            </p>
            <code className="endpoint-code">POST {API_BASE}/api/camera/frame?source_id=esp_cam_01</code>
          </section>
        </aside>
      </div>
      <FunctionChecklist area="Camera" />
    </div>
  );
}
