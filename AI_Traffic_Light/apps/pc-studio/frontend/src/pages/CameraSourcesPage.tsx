import { useEffect, useState } from "react";
import { API_BASE } from "../api";
import { FunctionChecklist } from "../components/FunctionChecklist";
import { SimulationControls } from "../components/SimulationControls";
import {
  connectRemoteCamera,
  DEFAULT_REMOTE_CAMERA_SETTINGS,
  deleteRemoteCamera,
  disconnectRemoteCamera,
  fetchRemoteCameraStatus,
  liveCameraMjpegUrl,
  refreshCameraAfterRemoteChange,
  saveRemoteCamera,
  selectRemoteCamera,
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
const FRAME_SIZE_DIMENSIONS: Record<RemoteFrameSize, string> = {
  QQVGA: "160 × 120",
  HQVGA: "240 × 176",
  QVGA: "320 × 240",
  CIF: "400 × 296",
  VGA: "640 × 480",
  SVGA: "800 × 600",
  XGA: "1024 × 768",
  SXGA: "1280 × 1024",
  UXGA: "1600 × 1200",
};
const NEW_CAMERA = "__new_camera__";

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
  const [selectedId, setSelectedId] = useState(NEW_CAMERA);
  const [host, setHost] = useState("");
  const [sourceId, setSourceId] = useState("esp32_cam_01");
  const [targetFps, setTargetFps] = useState(15);
  const [settings, setSettings] = useState<RemoteCameraSettings>({ ...DEFAULT_REMOTE_CAMERA_SETTINGS });
  const [busy, setBusy] = useState(false);
  const [remoteMessage, setRemoteMessage] = useState<string | null>(null);
  const [remoteError, setRemoteError] = useState<string | null>(null);

  function loadSelectedProfile(next: RemoteCameraStatus) {
    setRemote(next);
    const profile = next.cameras.find((camera) => camera.source_id === next.active_source_id);
    if (!profile) {
      setSelectedId(NEW_CAMERA);
      return;
    }
    setSelectedId(profile.source_id);
    setHost(profile.host);
    setSourceId(profile.source_id);
    setTargetFps(profile.target_fps);
    setSettings(profile.settings);
  }

  function resetNewCamera(nextNumber?: number) {
    const suffix = Math.max(1, nextNumber ?? ((remote?.camera_count ?? 0) + 1));
    setSelectedId(NEW_CAMERA);
    setHost("");
    setSourceId(`esp32_cam_${String(suffix).padStart(2, "0")}`);
    setTargetFps(15);
    setSettings({ ...DEFAULT_REMOTE_CAMERA_SETTINGS });
    setRemoteError(null);
    setRemoteMessage("Enter a new ESP IP, adjust its settings, then Save or Connect.");
  }

  useEffect(() => {
    void fetchRemoteCameraStatus()
      .then((next) => {
        setRemote(next);
        const profile = next.cameras.find((camera) => camera.source_id === next.active_source_id);
        if (profile) {
          setSelectedId(profile.source_id);
          setHost(profile.host);
          setSourceId(profile.source_id);
          setTargetFps(profile.target_fps);
          setSettings(profile.settings);
        }
      })
      .catch(() => undefined);
  }, []);

  useSerialPolling(
    async () => {
      const next = await fetchRemoteCameraStatus();
      setRemote(next);
    },
    1000,
    { onError: () => undefined },
  );

  const selectedSaved = selectedId !== NEW_CAMERA;
  const selectedProfile = selectedSaved
    ? remote?.cameras.find((camera) => camera.source_id === selectedId) ?? null
    : null;
  const selectedStreaming = Boolean(selectedProfile?.streaming);
  const backgroundStreams = remote?.cameras.filter((camera) => camera.streaming && camera.source_id !== remote.active_source_id).length ?? 0;
  const deviceEffectiveQuality = typeof remote?.device?.effective_jpeg_quality === "number" ? remote.device.effective_jpeg_quality : null;
  const deviceConfiguredQuality = typeof remote?.device?.configured_jpeg_quality === "number" ? remote.device.configured_jpeg_quality : null;
  const deviceSendEwma = typeof remote?.device?.send_ewma_ms === "number" ? remote.device.send_ewma_ms : null;
  const deviceQualityPreserving = remote?.device?.quality_preserving_transport === true;
  const deviceEffectiveFrameSize = typeof remote?.device?.effective_frame_size === "string" ? remote.device.effective_frame_size : null;
  const deviceConfiguredFrameSize = typeof remote?.device?.configured_frame_size === "string" ? remote.device.configured_frame_size : null;
  const deviceWifiRssi = typeof remote?.device?.rssi === "number" ? remote.device.rssi : null;
  const deviceWifiBssid = typeof remote?.device?.wifi_bssid === "string" ? remote.device.wifi_bssid : null;
  const deviceWifiChannel = typeof remote?.device?.wifi_channel === "number" ? remote.device.wifi_channel : null;
  const deviceWifiDisconnects = typeof remote?.device?.wifi_disconnects === "number" ? remote.device.wifi_disconnects : null;
  const deviceWifiReconnects = typeof remote?.device?.wifi_reconnects === "number" ? remote.device.wifi_reconnects : null;
  const deviceTransportSlowFrames = typeof remote?.device?.transport_slow_frames === "number" ? remote.device.transport_slow_frames : null;
  const selectedFrameAvailable = Boolean(
    status?.frame_available
      && (status.simulation_enabled || !remote?.active_source_id || status.active_source_id === remote.active_source_id),
  );
  const useLivePreview = Boolean(status?.simulation_enabled || (selectedSaved && remote?.streaming));
  const imageUrl = useLivePreview
    ? liveCameraMjpegUrl()
    : selectedFrameAvailable
      ? `${API_BASE}/api/camera/frame?v=${status?.frame_number ?? 0}`
      : null;

  const statusLabel = !status
    ? "checking"
    : status.simulation_enabled
      ? status.simulation_paused ? "simulation paused" : "simulation running"
      : !selectedSaved
        ? "new camera draft"
        : remote?.streaming
          ? remote.paused_for_simulation
            ? "ESP paused for simulation"
            : remote.stream_connected
              ? "ESP streaming"
              : "ESP reconnecting"
          : remote?.configured
            ? remote.device_reachable ? "ESP ready" : "ESP unreachable"
            : selectedProfile
              ? "ESP saved"
              : "waiting for device";

  function setSetting<K extends keyof RemoteCameraSettings>(key: K, value: RemoteCameraSettings[K]) {
    setSettings((current) => ({ ...current, [key]: value }));
  }

  async function chooseSavedCamera(nextSourceId: string) {
    if (nextSourceId === NEW_CAMERA) {
      resetNewCamera();
      return;
    }
    setBusy(true);
    setRemoteError(null);
    setRemoteMessage(null);
    try {
      const next = await selectRemoteCamera(nextSourceId);
      loadSelectedProfile(next);
      onStatusChange(await refreshCameraAfterRemoteChange());
      const selected = next.cameras.find((camera) => camera.source_id === nextSourceId);
      setRemoteMessage(
        selected?.streaming
          ? `Switched active view to ${nextSourceId}. Its existing stream remains live.`
          : `Selected ${nextSourceId}. Saved IP and camera settings restored.`,
      );
    } catch (error) {
      setRemoteError(error instanceof Error ? error.message : "ESP32-CAM selection failed.");
    } finally {
      setBusy(false);
    }
  }

  async function saveEspProfile() {
    setBusy(true);
    setRemoteError(null);
    setRemoteMessage(null);
    try {
      const next = await saveRemoteCamera({
        host: host.trim(),
        source_id: sourceId.trim() || "esp32_cam_01",
        target_fps: targetFps,
        settings,
      });
      loadSelectedProfile(next);
      onStatusChange(await refreshCameraAfterRemoteChange());
      setRemoteMessage(`Saved ${next.source_id} at ${next.host}. These values will be restored after PC Studio restarts.`);
    } catch (error) {
      setRemoteError(error instanceof Error ? error.message : "ESP32-CAM profile could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  async function connectEsp() {
    setBusy(true);
    setRemoteError(null);
    setRemoteMessage(null);
    try {
      await saveRemoteCamera({
        host: host.trim(),
        source_id: sourceId.trim() || "esp32_cam_01",
        target_fps: targetFps,
        settings,
      });
      const next = await connectRemoteCamera({
        host: host.trim(),
        source_id: sourceId.trim() || "esp32_cam_01",
      });
      loadSelectedProfile(next);
      onStatusChange(await refreshCameraAfterRemoteChange());
      setRemoteMessage(`ESP32-CAM ${next.host} is ready. Other ESP streams can remain connected while this camera is selected.`);
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
      loadSelectedProfile(next);
      onStatusChange(await refreshCameraAfterRemoteChange());
      setRemoteMessage("Settings saved and applied. Low-latency TCP JPEG streaming started for the selected ESP.");
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
      loadSelectedProfile(next);
      onStatusChange(await refreshCameraAfterRemoteChange());
      setRemoteMessage("Selected ESP stream stopped. Other ESP streams are unchanged.");
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
      loadSelectedProfile(next);
      onStatusChange(await refreshCameraAfterRemoteChange());
      setRemoteMessage("Selected ESP disconnected. Its saved IP and settings were kept.");
    } catch (error) {
      setRemoteError(error instanceof Error ? error.message : "ESP32-CAM could not be disconnected.");
    } finally {
      setBusy(false);
    }
  }

  async function deleteEspProfile() {
    if (!selectedSaved) return;
    setBusy(true);
    setRemoteError(null);
    setRemoteMessage(null);
    try {
      const deletedId = selectedId;
      const next = await deleteRemoteCamera(deletedId);
      setRemote(next);
      const profile = next.cameras.find((camera) => camera.source_id === next.active_source_id);
      if (profile) {
        loadSelectedProfile(next);
      } else {
        resetNewCamera(1);
      }
      onStatusChange(await refreshCameraAfterRemoteChange());
      setRemoteMessage(`Removed saved camera ${deletedId}.`);
    } catch (error) {
      setRemoteError(error instanceof Error ? error.message : "Saved ESP camera could not be removed.");
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
                Saved ESP profiles keep the selected OV2640 image settings while the binary TCP stream carries complete JPEG frames. Select which ESP feeds the shared PC Studio AI, capture, zone and analytics pipeline; use Camera Test when a physical connection is unstable.
              </p>
            </div>
            <span className={`status-pill ${status?.stale ? "status-planned" : selectedFrameAvailable ? "status-implemented" : ""}`}>
              {statusLabel}
            </span>
          </div>

          <div className="camera-frame-wrapper">
            {imageUrl ? (
              <img
                className="camera-frame"
                src={imageUrl}
                alt={`Latest frame from ${status?.active_source_id ?? remote?.active_source_id ?? "camera"}`}
              />
            ) : (
              <div className="camera-empty-state">
                <strong>No selected-camera frame available</strong>
                <p>Select a saved ESP, connect it and start its stream. Other ESP streams may continue in the background.</p>
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

          {(remote?.cameras.some((camera) => camera.streaming) ?? false) && status?.simulation_enabled && (
            <p className="small-note">
              Physical ESP image sockets pause while simulation is active and resume automatically after simulation stops.
            </p>
          )}

          <SimulationControls status={status} onStatusChange={onStatusChange} />
        </section>

        <aside className="side-column">
          <section className="panel compact-panel training-form">
            <div className="panel-header">
              <div>
                <h2>ESP camera manager</h2>
                <p className="placeholder-copy">Saved IPs and per-camera settings are restored automatically. Switching cameras does not stop the other ESP streams.</p>
              </div>
              <span className="status-pill muted">{remote?.camera_count ?? 0} / {remote?.max_saved_cameras ?? 12} saved</span>
            </div>

            <div className="form-grid">
              <label>
                Saved ESP camera
                <select value={selectedId} onChange={(event) => void chooseSavedCamera(event.target.value)} disabled={busy}>
                  <option value={NEW_CAMERA}>+ New ESP camera</option>
                  {remote?.cameras.map((camera) => (
                    <option key={camera.source_id} value={camera.source_id}>
                      {camera.source_id} — {camera.host}{camera.streaming ? " • streaming" : camera.connected ? " • connected" : ""}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                ESP IPv4 address
                <input value={host} onChange={(event) => setHost(event.target.value)} placeholder="192.168.1.87" disabled={busy || selectedStreaming} />
              </label>
              <label>
                Source ID
                <input value={sourceId} onChange={(event) => setSourceId(event.target.value)} placeholder="esp32_cam_01" disabled={busy || selectedSaved} />
              </label>
            </div>

            <div className="button-row">
              <button type="button" onClick={() => resetNewCamera()} disabled={busy}>New camera</button>
              <button type="button" onClick={() => void saveEspProfile()} disabled={busy || !host.trim() || !sourceId.trim() || selectedStreaming}>Save</button>
              <button className="primary" type="button" onClick={() => void connectEsp()} disabled={busy || !host.trim() || !sourceId.trim() || selectedStreaming}>
                {busy ? "Working..." : remote?.configured && selectedSaved ? "Reconnect" : "Connect"}
              </button>
              <button type="button" onClick={() => void disconnectEsp()} disabled={busy || !selectedSaved || !remote?.configured}>
                Disconnect
              </button>
              <button type="button" onClick={() => void deleteEspProfile()} disabled={busy || !selectedSaved}>
                Remove saved
              </button>
            </div>

            {backgroundStreams > 0 && (
              <p className="small-note">{backgroundStreams} other ESP stream{backgroundStreams === 1 ? " is" : "s are"} still running in the background for faster switching.</p>
            )}
            {remote?.registry_warning && <p className="error-message">{remote.registry_warning}</p>}
          </section>

          <section className="panel compact-panel training-form">
            <div className="panel-header">
              <div>
                <h2>Camera settings</h2>
                <p className="placeholder-copy">Each saved ESP keeps its own OV2640 settings and target FPS. V037 may temporarily increase JPEG compression above the saved quality value to preserve freshness, then recover quality when the link is fast.</p>
              </div>
              <span className="status-pill muted">{selectedStreaming ? "locked while streaming" : "saved per camera"}</span>
            </div>

            <div className="form-grid">
              <label>
                Resolution
                <select value={settings.frame_size} onChange={(event) => setSetting("frame_size", event.target.value as RemoteFrameSize)} disabled={busy || selectedStreaming}>
                  {FRAME_SIZES.map((size) => <option key={size} value={size}>{FRAME_SIZE_DIMENSIONS[size]}</option>)}
                </select>
              </label>
              <label>
                JPEG quality (4 best – 63 smallest)
                <input type="number" min={4} max={63} value={settings.jpeg_quality} onChange={(event) => setSetting("jpeg_quality", numberValue(event.target.value))} disabled={busy || selectedStreaming} />
              </label>
              <label>
                Target stream FPS
                <input type="number" min={1} max={30} step={1} value={targetFps} onChange={(event) => setTargetFps(numberValue(event.target.value))} disabled={busy || selectedStreaming} />
              </label>
              <label>
                Brightness (-2 to 2)
                <input type="number" min={-2} max={2} value={settings.brightness} onChange={(event) => setSetting("brightness", numberValue(event.target.value))} disabled={busy || selectedStreaming} />
              </label>
              <label>
                Contrast (-2 to 2)
                <input type="number" min={-2} max={2} value={settings.contrast} onChange={(event) => setSetting("contrast", numberValue(event.target.value))} disabled={busy || selectedStreaming} />
              </label>
              <label>
                Saturation (-2 to 2)
                <input type="number" min={-2} max={2} value={settings.saturation} onChange={(event) => setSetting("saturation", numberValue(event.target.value))} disabled={busy || selectedStreaming} />
              </label>
            </div>

            <details>
              <summary>Advanced OV2640 settings</summary>
              <div className="form-grid">
                <label>Special effect (0–6)<input type="number" min={0} max={6} value={settings.special_effect} onChange={(event) => setSetting("special_effect", numberValue(event.target.value))} disabled={busy || selectedStreaming} /></label>
                <label>White balance mode (0–4)<input type="number" min={0} max={4} value={settings.wb_mode} onChange={(event) => setSetting("wb_mode", numberValue(event.target.value))} disabled={busy || selectedStreaming} /></label>
                <label>AE level (-2 to 2)<input type="number" min={-2} max={2} value={settings.ae_level} onChange={(event) => setSetting("ae_level", numberValue(event.target.value))} disabled={busy || selectedStreaming} /></label>
                <label>AEC value (0–1200)<input type="number" min={0} max={1200} value={settings.aec_value} onChange={(event) => setSetting("aec_value", numberValue(event.target.value))} disabled={busy || selectedStreaming} /></label>
                <label>AGC gain (0–30)<input type="number" min={0} max={30} value={settings.agc_gain} onChange={(event) => setSetting("agc_gain", numberValue(event.target.value))} disabled={busy || selectedStreaming} /></label>
                <label>Gain ceiling (0–6)<input type="number" min={0} max={6} value={settings.gainceiling} onChange={(event) => setSetting("gainceiling", numberValue(event.target.value))} disabled={busy || selectedStreaming} /></label>
              </div>

              <div className="checklist">
                {([
                  ["awb", "Auto white balance"], ["awb_gain", "Auto white-balance gain"],
                  ["aec", "Auto exposure"], ["aec2", "AEC2 DSP"], ["agc", "Auto gain"],
                  ["bpc", "Black-pixel correction"], ["wpc", "White-pixel correction"],
                  ["raw_gma", "Raw gamma"], ["lenc", "Lens correction"],
                  ["hmirror", "Horizontal mirror"], ["vflip", "Vertical flip"],
                  ["dcw", "Downsize/crop"], ["colorbar", "Color test bar"],
                ] as const).map(([key, label]) => (
                  <label key={key}>
                    <input
                      type="checkbox"
                      checked={settings[key]}
                      onChange={(event) => setSetting(key, event.target.checked)}
                      disabled={busy || selectedStreaming}
                    />
                    {label}
                  </label>
                ))}
              </div>
            </details>

            <div className="button-row">
              <button className="primary" type="button" onClick={() => void startEsp()} disabled={busy || !selectedSaved || !remote?.configured || !remote.device_reachable || remote.streaming}>
                Start Stream
              </button>
              <button type="button" onClick={() => void stopEsp()} disabled={busy || !selectedSaved || !remote?.streaming}>
                Stop Stream
              </button>
            </div>

            {remoteMessage && <p className="success-message">{remoteMessage}</p>}
            {remoteError && <p className="error-message">{remoteError}</p>}
            {remote?.last_error && selectedSaved && <p className="small-note">Last selected-ESP error: {remote.last_error}</p>}
          </section>

          <section className="panel compact-panel">
            <div className="panel-header"><h2>Selected input status</h2></div>
            <div className="camera-status-list">
              <div><span>Saved cameras</span><strong>{remote?.camera_count ?? 0}</strong></div>
              <div><span>Selected ESP</span><strong>{remote?.active_source_id ?? "none"}</strong></div>
              <div><span>ESP address</span><strong>{selectedSaved ? remote?.host ?? host : host || "none"}</strong></div>
              <div><span>Device</span><strong>{remote?.device_reachable ? "reachable" : remote?.configured ? "unreachable" : selectedSaved ? "not connected" : "new draft"}</strong></div>
              <div><span>ESP session</span><strong>{remote?.streaming ? "active" : "idle"}</strong></div>
              <div><span>Transport</span><strong>{remote?.paused_for_simulation ? "TCP JPEG paused" : remote?.stream_connected ? "TCP JPEG connected" : remote?.streaming ? "reconnecting" : "idle"}</strong></div>
              <div><span>Target FPS</span><strong>{remote?.target_fps ?? targetFps}</strong></div>
              <div><span>Measured FPS</span><strong>{remote?.measured_fps ? remote.measured_fps.toFixed(1) : "—"}</strong></div>
              <div><span>JPEG quality</span><strong>{deviceEffectiveQuality !== null ? `${deviceEffectiveQuality} effective / ${deviceConfiguredQuality ?? settings.jpeg_quality} saved` : settings.jpeg_quality}</strong></div>
              <div><span>Image policy</span><strong>{deviceQualityPreserving ? "fixed saved quality / resolution" : "legacy adaptive firmware"}</strong></div>
              <div><span>ESP effective size</span><strong>{deviceEffectiveFrameSize ? `${deviceEffectiveFrameSize} effective / ${deviceConfiguredFrameSize ?? settings.frame_size} saved` : FRAME_SIZE_DIMENSIONS[settings.frame_size]}</strong></div>
              <div><span>ESP send EWMA</span><strong>{deviceSendEwma !== null ? `${deviceSendEwma.toFixed(0)} ms` : "—"}</strong></div>
              <div><span>Slow-send frames</span><strong>{deviceTransportSlowFrames ?? 0}</strong></div>
              <div><span>Wi-Fi RSSI</span><strong>{deviceWifiRssi !== null ? `${deviceWifiRssi} dBm` : "—"}</strong></div>
              <div><span>Wi-Fi BSSID</span><strong>{deviceWifiBssid ?? "—"}</strong></div>
              <div><span>Wi-Fi channel</span><strong>{deviceWifiChannel ?? "—"}</strong></div>
              <div><span>ESP Wi-Fi recovery</span><strong>{`${deviceWifiDisconnects ?? 0} lost / ${deviceWifiReconnects ?? 0} reconnected`}</strong></div>
              <div><span>Stream reconnects</span><strong>{remote?.stream_reconnects ?? 0}</strong></div>
              <div><span>Session recoveries</span><strong>{remote?.session_recoveries ?? 0}</strong></div>
              <div><span>Failure streak</span><strong>{remote?.consecutive_failures ?? 0}</strong></div>
              <div><span>Reconnect backoff</span><strong>{remote?.reconnect_backoff_ms ? `${remote.reconnect_backoff_ms} ms` : "—"}</strong></div>
              <div><span>Source sequence gaps</span><strong>{remote?.source_sequence_gaps ?? 0}</strong></div>
              <div><span>Pipeline source</span><strong>{status?.active_source_id ?? "none"}</strong></div>
              <div><span>Resolution</span><strong>{selectedFrameAvailable && status?.resolution ? `${status.resolution.width} × ${status.resolution.height}` : FRAME_SIZE_DIMENSIONS[settings.frame_size]}</strong></div>
              <div><span>Frame age</span><strong>{selectedFrameAvailable ? formatAge(status?.age_ms ?? null) : "No selected frame"}</strong></div>
              <div><span>Frames received</span><strong>{remote?.successful_fetches ?? 0}</strong></div>
            </div>
          </section>

          <section className="panel compact-panel">
            <div className="panel-header"><h2>Compatibility</h2><span className="status-pill muted">local prototype</span></div>
            <p className="placeholder-copy">
              V037 R6 keeps the V036-compatible length-prefixed TCP JPEG wire format but no longer forces JPEGs into one lwIP send window. Saved JPEG quality and resolution stay fixed across transport pressure; the ESP exposes RSSI/BSSID/channel diagnostics and lets achieved FPS fall to sustainable throughput. Multiple ESP streams can run independently; only the selected source is forwarded into the existing PC Studio frame pipeline.
            </p>
            <code className="endpoint-code">POST {API_BASE}/api/camera/remote/select</code>
          </section>
        </aside>
      </div>
      <FunctionChecklist area="Camera" />
    </div>
  );
}
