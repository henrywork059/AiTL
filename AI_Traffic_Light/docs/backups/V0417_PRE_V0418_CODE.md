# V0417 source snapshot before V0418

This is a verbatim snapshot of the **six affected pre-patch files** at Git commit `85eb480a09be8d140ef065eec073e88ef3a5b9d7`. It is provided as a recovery reference, not as active implementation; it must not be imported or executed. To recover the exact original file through Git, run `git show 85eb480a09be8d140ef065eec073e88ef3a5b9d7:AI_Traffic_Light/<relative-path>`.

## Error-prevention reminders

- Never change serialized camera identifiers or region vertex coordinates to implement UI-only changes.
- Simulation image drawing is independent of the traffic-signal decision clock; remove only visuals, not signal state or phase safety rules.
- Saved-camera selection must reuse `chooseSavedCamera` / `selectRemoteCamera`, not duplicate network selection logic.
- Region selected/unselected fill must stay **none**; selected outlines can be emphasized without painting the camera image.
- Region side choices must change preview-side state, **not** mutate the crosswalk camera assignment or stored region coordinates.
- When changing rendering, update `test_simulation_frame_layout.py` and run the previously relevant camera simulation checks. When changing JSX/CSS, check its structural test and frontend TypeScript/build. Do not treat source-level checks as runtime PASS.

---

## `apps/pc-studio/frontend/src/pages/CameraSourcesPage.tsx`

~~~~tsx
import { useRef, useState } from "react";
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
  saveSimulationCamera,
  selectRemoteCamera,
  startRemoteCamera,
  stopRemoteCamera,
  type RemoteCameraProfile,
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
  view?: "sources" | "settings";
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

function cameraIndicator(camera: RemoteCameraProfile): { label: string; tone: string } {
  if (camera.kind === "simulation") return camera.streaming ? { label: "Simulating", tone: "status-implemented" } : { label: "Saved", tone: "muted" };
  if (camera.streaming) {
    if (camera.paused_for_simulation) return { label: "Paused", tone: "status-planned" };
    return camera.stream_connected
      ? { label: "Streaming", tone: "status-implemented" }
      : { label: "Reconnecting", tone: "status-planned" };
  }
  if (camera.connected) {
    return camera.device_reachable
      ? { label: "Connected", tone: "status-info" }
      : { label: "Unreachable", tone: "status-error" };
  }
  return camera.last_error
    ? { label: "Error", tone: "status-error" }
    : { label: "Saved", tone: "muted" };
}

export function CameraSourcesPage({ status, onSimulationChange, onStatusChange, changingMode, view = "sources" }: Props) {
  const cameraSettingsView = view === "settings";
  const [remote, setRemote] = useState<RemoteCameraStatus | null>(null);
  const [selectedId, setSelectedId] = useState(NEW_CAMERA);
  const [host, setHost] = useState("");
  const [newCameraType, setNewCameraType] = useState<"esp32" | "simulation">("esp32");
  const [sourceId, setSourceId] = useState("esp32_cam_01");
  const [targetFps, setTargetFps] = useState(15);
  const [settings, setSettings] = useState<RemoteCameraSettings>({ ...DEFAULT_REMOTE_CAMERA_SETTINGS });
  const [busy, setBusy] = useState(false);
  const [remoteMessage, setRemoteMessage] = useState<string | null>(null);
  const [remoteError, setRemoteError] = useState<string | null>(null);
  const initializedRef = useRef(false);

  function loadSelectedProfile(next: RemoteCameraStatus) {
    setRemote(next);
    const profile = next.cameras.find((camera) => camera.source_id === next.active_source_id);
    if (!profile) {
      setSelectedId(NEW_CAMERA);
      return;
    }
    setSelectedId(profile.source_id);
    setNewCameraType(profile.kind);
    setHost(profile.host);
    setSourceId(profile.source_id);
    setTargetFps(profile.target_fps);
    setSettings(profile.settings);
  }

  function resetNewCamera(nextNumber?: number) {
    const suffix = Math.max(1, nextNumber ?? ((remote?.camera_count ?? 0) + 1));
    setSelectedId(NEW_CAMERA);
    setNewCameraType("esp32");
    setHost("");
    setSourceId(`esp32_cam_${String(suffix).padStart(2, "0")}`);
    setTargetFps(15);
    setSettings({ ...DEFAULT_REMOTE_CAMERA_SETTINGS });
    setRemoteError(null);
    setRemoteMessage("Choose ESP32-CAM or a mirrored simulation pair.");
  }

  useSerialPolling(
    async () => {
      const next = await fetchRemoteCameraStatus();
      if (!initializedRef.current) {
        loadSelectedProfile(next);
        initializedRef.current = true;
      } else {
        setRemote(next);
      }
    },
    1000,
    { onError: () => undefined },
  );

  const selectedSaved = selectedId !== NEW_CAMERA;
  const selectedProfile = selectedSaved
    ? remote?.cameras.find((camera) => camera.source_id === selectedId) ?? null
    : null;
  const selectedSimulation = selectedProfile?.kind === "simulation";
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
  // The Settings preview must never display a simulation or stale frame as the selected ESP.
  const imageUrl = cameraSettingsView
    ? selectedSimulation && status?.simulation_enabled
      ? liveCameraMjpegUrl()
      : selectedSaved && !selectedSimulation && selectedStreaming && !status?.simulation_enabled && !remote?.paused_for_simulation
        ? liveCameraMjpegUrl()
        : null
    : status?.simulation_enabled
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
        selected?.kind === "simulation"
          ? "Simulation camera selected and started."
          : selected?.streaming
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
      const next = newCameraType === "simulation" && !selectedSaved
        ? await saveSimulationCamera()
        : await saveRemoteCamera({
        host: host.trim(),
        source_id: sourceId.trim() || "esp32_cam_01",
        target_fps: targetFps,
        settings,
      });
      loadSelectedProfile(next);
      onStatusChange(await refreshCameraAfterRemoteChange());
      setRemoteMessage(newCameraType === "simulation" && !selectedSaved ? "Simulation camera pair saved and started." : `Saved ${next.source_id} at ${next.host}. These values will be restored after PC Studio restarts.`);
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
      {cameraSettingsView && (
        <section className="panel compact-panel camera-status-strip" aria-label="Saved camera connection status">
          <div className="camera-status-strip-header">
            <strong>Saved cameras</strong>
            <span>{remote?.camera_count ?? "—"} saved · {remote?.cameras.filter((camera) => camera.stream_connected).length ?? 0} live</span>
          </div>
          <div className="camera-status-strip-items" role="list">
            {remote?.cameras.map((camera) => {
              const indicator = cameraIndicator(camera);
              return (
                <div
                  role="listitem"
                  key={camera.source_id}
                  className={`camera-status-entry${camera.selected ? " is-selected" : ""}`}
                >
                  <div className="camera-status-entry-name">
                    <strong title={camera.source_id}>{camera.source_id}</strong>
                    {camera.selected && <small>Active preview</small>}
                  </div>
                  <small title={camera.host || "PC simulation"}>{camera.kind === "simulation" ? "PC simulation" : camera.host}</small>
                  <span className={`status-pill ${indicator.tone}`}>{indicator.label}</span>
                </div>
              );
            })}
            {!remote && <span className="small-note">Loading saved cameras…</span>}
            {remote?.camera_count === 0 && <span className="small-note">No cameras saved. Add one using the manager below.</span>}
          </div>
        </section>
      )}
      <div className={cameraSettingsView ? "camera-layout" : "page-stack"}>
        <section className="panel camera-preview-panel">
          <div className="panel-header">
            <div>
              <h2>{cameraSettingsView ? "Selected camera live preview" : "Camera input and simulation"}</h2>
              {!cameraSettingsView && (
                <p className="placeholder-copy">Preview the current frame input or run the built-in traffic simulation.</p>
              )}
            </div>
            <span className={`status-pill ${status?.stale ? "status-planned" : selectedFrameAvailable ? "status-implemented" : ""}`}>
              {statusLabel}
            </span>
          </div>

          <div className="camera-frame-wrapper">
            {imageUrl ? (
              <img
                key={cameraSettingsView ? remote?.active_source_id ?? "none" : status?.simulation_enabled ? "simulation" : status?.active_source_id ?? "input"}
                className="camera-frame"
                src={imageUrl}
                alt={`Live frame from ${cameraSettingsView ? selectedId : status?.active_source_id ?? "camera"}`}
              />
            ) : (
              <div className="camera-empty-state">
                <strong>{cameraSettingsView ? selectedSimulation ? "Simulation stopped" : "No live camera preview" : "No camera frame available"}</strong>
                <p>{cameraSettingsView
                  ? selectedSimulation
                    ? "Start simulation to preview the synthetic traffic scene."
                    : status?.simulation_enabled
                    ? "Simulation is active. Select a saved physical ESP to preview its stream."
                    : "Select a saved ESP, connect it and start its stream. Other ESP streams may continue in the background."
                  : "Start simulation, select an ESP in Camera Settings, or upload a device frame."}</p>
              </div>
            )}
          </div>

          {!cameraSettingsView && (
            <>
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
            </>
          )}
          {cameraSettingsView && (
            <div className="camera-status-list">
              <div><span>Preview camera</span><strong>{selectedSaved ? selectedId : "Select a saved camera"}</strong></div>
              <div><span>IP address</span><strong>{selectedSimulation ? "Not required" : selectedSaved ? selectedProfile?.host ?? "—" : "—"}</strong></div>
              <div><span>Live connection</span><strong>{selectedSaved && remote?.stream_connected && !status?.simulation_enabled ? "Connected" : selectedStreaming ? "Waiting / paused" : "Offline"}</strong></div>
              <div><span>Measured stream FPS</span><strong>{selectedSaved && remote?.measured_fps ? remote.measured_fps.toFixed(1) : "—"}</strong></div>
              <div><span>Frame age</span><strong>{selectedSaved && selectedFrameAvailable ? formatAge(status?.age_ms ?? null) : "No live frame"}</strong></div>
            </div>
          )}
        </section>

        {cameraSettingsView && (
        <aside className="side-column">
          <section className="panel compact-panel training-form">
            <div className="panel-header">
              <div>
                <h2>Camera manager</h2>
              </div>
              <span className="status-pill muted">{remote?.camera_count ?? 0} / {remote?.max_saved_cameras ?? 12} saved</span>
            </div>

            <div className="form-grid">
              <label>
                Saved camera
                <select value={selectedId} onChange={(event) => void chooseSavedCamera(event.target.value)} disabled={busy}>
                  <option value={NEW_CAMERA}>+ New camera</option>
                  {remote?.cameras.map((camera) => (
                    <option key={camera.source_id} value={camera.source_id}>
                      {camera.source_id} — {camera.kind === "simulation" ? "PC simulation" : camera.host}{camera.streaming ? " • streaming" : camera.connected ? " • connected" : ""}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {!selectedSaved && <label>New camera type
              <select value={newCameraType} onChange={(event) => setNewCameraType(event.target.value as "esp32" | "simulation")} disabled={busy}>
                <option value="esp32">ESP32-CAM (IP)</option>
                <option value="simulation">Simulation pair (2 mirrored cameras)</option>
              </select>
            </label>}
            {!selectedSaved && newCameraType === "simulation" && <div className="button-row">
              <button className="primary" type="button" onClick={() => void saveEspProfile()}
                disabled={busy || (remote?.cameras.some((camera) => camera.source_id === "simulation_camera_b") ?? false)}>
                Add simulation pair
              </button>
            </div>}
            {!selectedSimulation && newCameraType === "esp32" && <details className="camera-fold">
              <summary>Manage IP addresses and connections</summary>
              <div className="form-grid">
              {newCameraType === "esp32" && <label>
                ESP IPv4 address
                <input value={host} onChange={(event) => setHost(event.target.value)} placeholder="192.168.1.87" disabled={busy || selectedStreaming} />
              </label>}
              {newCameraType === "esp32" && <label>
                Source ID
                <input value={sourceId} onChange={(event) => setSourceId(event.target.value)} placeholder="esp32_cam_01" disabled={busy || selectedSaved} />
              </label>}
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
            </details>}

            {!selectedSimulation && <div className="button-row">
              <button className="primary" type="button" onClick={() => void startEsp()} disabled={busy || !selectedSaved || !remote?.configured || !remote.device_reachable || remote.streaming}>
                Start Stream
              </button>
              <button type="button" onClick={() => void stopEsp()} disabled={busy || !selectedSaved || !remote?.streaming}>
                Stop Stream
              </button>
            </div>}
            {selectedSimulation && <div className="button-row">
              <button className="primary" type="button" onClick={() => onSimulationChange(!status?.simulation_enabled)} disabled={busy || changingMode || !status}>{status?.simulation_enabled ? "Stop Simulation" : "Start Simulation"}</button>
              <button type="button" onClick={() => void deleteEspProfile()} disabled={busy}>Remove saved</button>
            </div>}
            {selectedSimulation && <SimulationControls status={status} onStatusChange={onStatusChange} />}

            {remoteMessage && <p className="success-message">{remoteMessage}</p>}
            {remoteError && <p className="error-message">{remoteError}</p>}
            {remote?.last_error && selectedSaved && <p className="small-note">Last selected-ESP error: {remote.last_error}</p>}

            {backgroundStreams > 0 && (
              <p className="small-note">{backgroundStreams} other ESP stream{backgroundStreams === 1 ? " is" : "s are"} still running in the background for faster switching.</p>
            )}
            {remote?.registry_warning && <p className="error-message">{remote.registry_warning}</p>}
          </section>

          {!selectedSimulation && <details className="panel compact-panel training-form camera-fold">
            <summary>
              <span>Camera settings</span>
              <span className="status-pill muted">{selectedStreaming ? "Locked while streaming" : "Image & FPS"}</span>
            </summary>

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

          </details>}

          {!selectedSimulation && <details className="panel compact-panel camera-fold">
            <summary>Detailed camera & stream status</summary>
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
          </details>}
        </aside>
        )}
      </div>
      {!cameraSettingsView && <FunctionChecklist area="Camera" />}
    </div>
  );
}

// The dedicated Settings route reuses the existing camera session and form owner.
export function CameraSettingsPage(props: Omit<Props, "view">) {
  return <CameraSourcesPage {...props} view="settings" />;
}
~~~~

## `apps/pc-studio/frontend/src/pages/CrosswalkRegionEditor.tsx`

~~~~tsx
import { useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import type { CameraStatus } from "../types";
import { liveCameraMjpegUrl, refreshCameraAfterRemoteChange, selectRemoteCamera, type RemoteCameraProfile } from "../lib/remoteCameraApi";
import type { Crosswalk, CrosswalkRegion } from "../types/crosswalks";
import "./crosswalkRegionEditor.css";

const WIDTH = 1280;
const HEIGHT = 720;
const MAX_REGIONS = 24;
type Side = "camera_side_a_id" | "camera_side_b_id";

function newRegion(regions: CrosswalkRegion[]): CrosswalkRegion {
  const ids = new Set(regions.map((item) => item.id));
  let number = 1;
  while (ids.has("region_" + number)) number++;
  return {
    id: "region_" + number,
    label: "New region " + number,
    vertices: [[390, 220], [890, 220], [890, 500], [390, 500]],
  };
}

type Props = {
  crosswalk: Crosswalk;
  cameras: RemoteCameraProfile[];
  cameraStatus: CameraStatus | null;
  changingMode: boolean;
  onSimulationChange: (enabled: boolean) => Promise<void>;
  onCameraStatusChange: (status: CameraStatus) => void;
  onRegionsChange: (regions: CrosswalkRegion[]) => void;
  onClose: () => void;
};

export function CrosswalkRegionEditor({
  crosswalk, cameras, cameraStatus, changingMode,
  onSimulationChange, onCameraStatusChange, onRegionsChange, onClose,
}: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(crosswalk.regions[0]?.id ?? null);
  const [side, setSide] = useState<Side>("camera_side_a_id");
  const [drag, setDrag] = useState<{ id: string; index: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = crosswalk.regions.find((region) => region.id === selectedId) ?? null;
  const sourceId = crosswalk[side];
  const selectedCamera = cameras.find((camera) => camera.source_id === sourceId);
  const simulated = Boolean(cameraStatus?.simulation_enabled);
  const previewReady = simulated
    ? Boolean(cameraStatus?.frame_available && selectedCamera?.kind === "simulation")
    : Boolean(sourceId && selectedCamera?.stream_connected && cameraStatus?.active_source_id === sourceId && !cameraStatus?.stale);
  const previewName = sourceId ?? "No camera assigned";
  const polygon = (region: CrosswalkRegion) => region.vertices.map(([x, y]) => x + "," + y).join(" ");

  function updateRegion(id: string, patch: Partial<CrosswalkRegion>) {
    onRegionsChange(crosswalk.regions.map((region) => region.id === id ? { ...region, ...patch } : region));
  }

  function addRegion() {
    if (crosswalk.regions.length >= MAX_REGIONS) return;
    const region = newRegion(crosswalk.regions);
    onRegionsChange([...crosswalk.regions, region]);
    setSelectedId(region.id);
    setError(null);
  }

  function removeRegion() {
    if (!selected) return;
    const remaining = crosswalk.regions.filter((region) => region.id !== selected.id);
    onRegionsChange(remaining);
    setSelectedId(remaining[0]?.id ?? null);
  }

  function onVertexDown(event: ReactPointerEvent<SVGCircleElement>, id: string, index: number) {
    event.preventDefault();
    event.stopPropagation();
    setSelectedId(id);
    setDrag({ id, index });
    event.currentTarget.ownerSVGElement?.setPointerCapture(event.pointerId);
  }

  function moveVertex(event: ReactPointerEvent<SVGSVGElement>) {
    if (!drag) return;
    const box = event.currentTarget.getBoundingClientRect();
    if (!box.width || !box.height) return;
    const x = Math.max(0, Math.min(WIDTH, Math.round((event.clientX - box.left) / box.width * WIDTH)));
    const y = Math.max(0, Math.min(HEIGHT, Math.round((event.clientY - box.top) / box.height * HEIGHT)));
    const region = crosswalk.regions.find((item) => item.id === drag.id);
    if (!region) return;
    const vertices = structuredClone(region.vertices);
    vertices[drag.index] = [x, y];
    updateRegion(region.id, { vertices });
  }

  function endDrag(event: ReactPointerEvent<SVGSVGElement>) {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    setDrag(null);
  }

  async function previewPhysicalCamera() {
    if (!sourceId || !selectedCamera || simulated) return;
    setBusy(true);
    setError(null);
    try {
      await selectRemoteCamera(sourceId);
      onCameraStatusChange(await refreshCameraAfterRemoteChange());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not select camera.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleSimulation() {
    setBusy(true);
    setError(null);
    try {
      await onSimulationChange(!simulated);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not change simulation mode.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="crosswalk-region-workspace page-stack">
      <div className="panel-header">
        <div>
          <h2>{crosswalk.label} — Region editor</h2>
          <p className="placeholder-copy">Four draggable vertices per region. The geometry belongs to this crosswalk and is shared by both camera slots.</p>
        </div>
        <button type="button" onClick={onClose}>Back to crosswalks</button>
      </div>
      <div className="crosswalk-region-layout">
        <aside className="panel compact-panel crosswalk-region-tools">
          <div className="panel-header">
            <h3>Regions</h3>
            <span className="status-pill muted">{crosswalk.regions.length} / {MAX_REGIONS}</span>
          </div>
          <div className="crosswalk-region-list">
            {crosswalk.regions.map((region) => (
              <button
                type="button" key={region.id}
                className={selected?.id === region.id ? "active" : ""}
                onClick={() => setSelectedId(region.id)}
              >{region.label}</button>
            ))}
            {crosswalk.regions.length === 0 && <p className="small-note">No regions yet.</p>}
          </div>
          <div className="button-row">
            <button className="primary" type="button" onClick={addRegion} disabled={crosswalk.regions.length >= MAX_REGIONS}>Add region</button>
            <button type="button" onClick={removeRegion} disabled={!selected}>Delete</button>
          </div>
          {selected && (
            <label>
              Region name
              <input
                maxLength={120}
                value={selected.label}
                onChange={(event) => updateRegion(selected.id, { label: event.target.value })}
              />
            </label>
          )}
          <hr />
          <h3>Preview source</h3>
          <span className="status-pill">{simulated ? "Simulation pair" : "Physical cameras"}</span>
          {(
            <>
              <label>Camera side
                <select value={side} onChange={(event) => setSide(event.target.value as Side)}>
                  <option value="camera_side_a_id">Side A</option>
                  <option value="camera_side_b_id">Side B</option>
                </select>
              </label>
              {!simulated && <button type="button" onClick={() => void previewPhysicalCamera()}
                disabled={busy || changingMode || !selectedCamera}>
                Select camera for preview
              </button>}
            </>
          )}
          <button type="button" onClick={() => void toggleSimulation()} disabled={busy || changingMode}>
            {simulated ? "Stop simulation" : "Use simulation camera"}
          </button>
          <p className="small-note">Side A and B are mirrored views of the same simulation.</p>
          {error && <p role="alert" className="error-message">{error}</p>}
        </aside>
        <section className="panel crosswalk-region-canvas-panel">
          <div className="panel-header">
            <strong>{previewName}</strong>
            <span className={previewReady ? "status-pill status-implemented" : "status-pill status-planned"}>
              {previewReady ? "Live preview" : "Preview unavailable"}
            </span>
          </div>
          <div className="crosswalk-region-frame">
            {previewReady
              ? <img key={previewName} src={simulated && selectedCamera?.kind === "simulation" && sourceId ? `${liveCameraMjpegUrl()}?source_id=${encodeURIComponent(sourceId)}` : liveCameraMjpegUrl()} alt={previewName} className="crosswalk-region-camera" />
              : <p className="crosswalk-region-frame-empty">
                  {simulated
                    ? "Waiting for the shared simulation frame."
                    : "Select a saved streaming side camera to align regions. Regions remain editable without a feed."}
                </p>}
            <svg
              viewBox={"0 0 " + WIDTH + " " + HEIGHT}
              className="crosswalk-region-overlay"
              aria-label="Drag the four numbered vertices to reshape the selected quadrilateral region"
              onPointerMove={moveVertex}
              onPointerUp={endDrag}
              onPointerCancel={endDrag}
            >
              {crosswalk.regions.map((region) => (
                <g key={region.id}>
                  <polygon
                    points={polygon(region)}
                    className={selected?.id === region.id ? "crosswalk-region-polygon is-selected" : "crosswalk-region-polygon"}
                  />
                  {selected?.id === region.id && region.vertices.map(([x, y], index) => (
                    <g key={index}>
                      <circle
                        cx={x} cy={y} r="17"
                        className="crosswalk-region-vertex"
                        onPointerDown={(event) => onVertexDown(event, region.id, index)}
                      />
                      <text x={x} y={y + 5} textAnchor="middle" className="crosswalk-region-vertex-label"
                        pointerEvents="none">{index + 1}</text>
                    </g>
                  ))}
                </g>
              ))}
            </svg>
          </div>
          <p className="small-note">Editing coordinates: {WIDTH} × {HEIGHT}. Same coordinates are overlaid for Side A and Side B; viewpoints are not automatically calibrated. Return to Crosswalks and select Save changes to persist.</p>
        </section>
      </div>
    </div>
  );
}
~~~~

## `apps/pc-studio/frontend/src/pages/crosswalkRegionEditor.css`

~~~~css
.crosswalk-region-workspace { width: 100%; }
.crosswalk-region-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  align-items: start;
  gap: var(--space-4);
}
.crosswalk-region-tools {
  display: grid;
  gap: var(--space-3);
}
.crosswalk-region-tools label { display: grid; gap: var(--space-2); }
.crosswalk-region-tools input, .crosswalk-region-tools select { width: 100%; min-width: 0; }
.crosswalk-region-tools hr { width: 100%; border: 0; border-top: 1px solid var(--color-border-subtle); }
.crosswalk-region-list { display: grid; gap: var(--space-2); max-height: 240px; overflow: auto; }
.crosswalk-region-list button { text-align: left; overflow-wrap: anywhere; }
.crosswalk-region-list button.active { border-color: var(--color-primary); background: var(--color-primary-surface); }
.crosswalk-region-canvas-panel { min-width: 0; }
.crosswalk-region-frame {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: var(--color-media);
  overflow: hidden;
  border-radius: var(--radius-md);
}
.crosswalk-region-camera, .crosswalk-region-overlay {
  display: block;
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.crosswalk-region-camera { object-fit: fill; }
.crosswalk-region-overlay { touch-action: none; }
.crosswalk-region-frame-empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: white;
  text-align: center;
  padding: var(--space-4);
}
.crosswalk-region-polygon { fill: none; stroke: var(--color-primary); stroke-width: 3; }
.crosswalk-region-polygon.is-selected { fill: none; stroke: var(--color-warning); stroke-width: 5; stroke-dasharray: 14 7; }
.crosswalk-region-vertex { fill: #ffffff; stroke: var(--color-primary); stroke-width: 5; cursor: grab; }
.crosswalk-region-vertex:active { cursor: grabbing; }
.crosswalk-region-vertex-label { fill: #113c6d; font-weight: 700; font-size: 19px; }
@media (max-width: 1300px) { .crosswalk-region-layout { grid-template-columns: minmax(0, 1fr); } }

.crosswalk-region-list button.active { box-shadow: inset 3px 0 0 var(--color-primary); }
~~~~

## `apps/pc-studio/frontend/src/styles/components.css`

~~~~css
.brand-block p,
.page-header p,
.placeholder-copy,
.function-item p,
.reason-text,
.small-note {
  color: var(--color-text-muted);
  line-height: 1.55;
}

.eyebrow {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  margin-bottom: var(--space-1);
}

.brand-block h1 {
  font-size: 19px;
  line-height: 1.25;
}

.brand-block p {
  font-size: 12px;
}

.nav-section h2 {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin: 0 0 var(--space-2);
  padding: var(--space-2) var(--space-2) var(--space-1);
  color: var(--color-nav-heading-text);
  text-transform: uppercase;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.07em;
}

.nav-section h2::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--color-nav-divider);
}

.nav-button {
  width: 100%;
  display: flex;
  justify-content: space-between;
  gap: var(--space-2);
  align-items: center;
  margin-bottom: 2px;
  padding-inline: var(--space-3);
  text-align: left;
  background: transparent;
  border-color: transparent;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  font-weight: 550;
}

.nav-button:hover:not(:disabled) {
  background: var(--color-nav-hover);
  border-color: transparent;
}

.nav-button small {
  color: var(--color-text-muted);
}

.nav-button.active,
.nav-button.active:hover:not(:disabled),
.nav-button.active:active:not(:disabled) {
  background: var(--color-nav-selected);
  border-color: transparent;
  color: var(--color-text-primary);
  font-weight: 650;
}

.nav-button.active small {
  color: var(--color-text-secondary);
}

.panel {
  border: var(--border-width) solid var(--color-border-subtle);
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  box-shadow: var(--shadow-panel);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
  gap: var(--space-2);
}

.compact-panel {
  padding: var(--space-4);
}

.compact-header {
  margin-bottom: 0;
}

.status-pill,
.status-placeholder {
  border: var(--border-width) solid var(--color-border-subtle);
  background: var(--color-surface-muted);
  color: var(--color-text-secondary);
  border-radius: var(--radius-pill);
  padding: 3px 9px;
  font-size: 12px;
  line-height: 1.35;
  font-weight: 600;
  white-space: nowrap;
}

.status-pill.muted,
.status-placeholder {
  border-color: var(--color-border-subtle);
  background: transparent;
  color: var(--color-text-muted);
}

.status-planned,
.status-later {
  border-color: var(--color-warning);
  background: var(--color-warning-surface);
  color: var(--color-warning);
}

.status-implemented {
  border-color: var(--color-success);
  background: var(--color-success-surface);
  color: var(--color-success);
}

.status-error {
  border-color: var(--color-danger);
  background: var(--color-danger-surface);
  color: var(--color-danger);
}

.live-view-wrapper,
.camera-frame-wrapper {
  border: var(--border-width) solid var(--color-border-default);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--color-media);
}

.live-view {
  display: block;
  width: 100%;
  height: auto;
}

.camera-frame-wrapper {
  aspect-ratio: 16 / 9;
  display: grid;
  place-items: center;
}

.camera-frame {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.camera-empty-state {
  display: grid;
  gap: var(--space-2);
  max-width: 460px;
  padding: 28px;
  text-align: center;
  color: var(--color-text-muted);
}

.camera-empty-state strong {
  color: var(--color-text-primary);
  font-size: 18px;
}

.sky { fill: var(--color-scene-sky); }
.road { fill: var(--color-scene-road); }

.road-line {
  stroke: var(--color-road-line);
  stroke-width: 8;
  stroke-dasharray: 42 40;
}

.crosswalk {
  fill: var(--color-crosswalk-fill);
  stroke: var(--color-crosswalk-stroke);
  stroke-width: 4;
  stroke-dasharray: 18 20;
}

.zone {
  fill: none;
  stroke-width: 4;
}

.zone-pedestrian_waiting { stroke: var(--color-person); }
.zone-crossing { stroke: var(--color-crossing); }
.zone-vehicle_queue { stroke: var(--color-queue); }

.zone-label {
  fill: var(--color-overlay-label);
  font-size: 22px;
  font-weight: 700;
  paint-order: stroke;
  stroke: var(--color-overlay-label-stroke);
  stroke-width: 4px;
}

.box {
  fill: transparent;
  stroke-width: 5;
}

.box-person { stroke: var(--color-person); }
.box-car,
.box-bus,
.box-truck,
.box-motorcycle,
.box-bicycle { stroke: var(--color-vehicle); }

.box-label-bg {
  fill: var(--color-overlay-label-bg);
  rx: 4;
}

.box-label {
  fill: var(--color-overlay-label);
  font-size: 22px;
  font-weight: 700;
}

.traffic-light-card {
  display: grid;
  grid-template-columns: 90px 1fr;
  gap: var(--space-4);
  align-items: center;
}

.signal-head {
  background: var(--color-media);
  border: var(--border-width) solid var(--color-border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.lamp {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 2px solid var(--color-signal-lamp-border);
}

.red { background: var(--color-signal-red); }
.amber { background: var(--color-signal-amber); }
.green { background: var(--color-signal-green); }
.off { background: var(--color-signal-off); opacity: 0.6; }

.label {
  color: var(--color-text-muted);
  font-size: 12px;
  margin-bottom: var(--space-1);
}

.phase-text,
.decision-text {
  text-transform: capitalize;
  font-weight: 650;
  margin-bottom: var(--space-3);
}

.metric-grid,
.metric-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-3);
}

.metric-grid {
  grid-template-columns: 1fr 1fr;
}

.metric-card,
.zone-list li,
.function-item,
.smoke-card,
.settings-list div,
.log-row {
  border: var(--border-width) solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised);
}

.metric-card {
  padding: var(--space-4);
}

.metric-card span {
  display: block;
  color: var(--color-text-muted);
  font-size: 12px;
  margin-bottom: var(--space-2);
}

.metric-card strong {
  display: block;
  font-size: 24px;
  line-height: 1.2;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}

.metric-card em {
  display: block;
  margin-top: 6px;
  color: var(--color-text-muted);
  font-size: 12px;
  font-style: normal;
}

.control-label {
  display: grid;
  gap: 10px;
  color: var(--color-text-secondary);
}

input[type="range"] {
  width: 100%;
}

.button-row {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-3);
  flex-wrap: wrap;
}

.zone-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: var(--space-2);
}

.zone-list li {
  padding: 10px;
}

.zone-list strong,
.zone-list span {
  display: block;
}

.zone-list span {
  color: var(--color-text-muted);
  margin-top: var(--space-1);
  font-size: 12px;
}

.table-wrapper {
  overflow: auto;
  border: var(--border-width) solid var(--color-border-subtle);
  border-radius: var(--radius-md);
}

table {
  width: 100%;
  border-collapse: collapse;
  background: var(--color-surface);
}

th,
td {
  padding: 12px 14px;
  border-bottom: var(--border-width) solid var(--color-border-subtle);
  text-align: left;
  font-size: 14px;
}

tr:last-child td {
  border-bottom: 0;
}

th {
  color: var(--color-text-muted);
  background: var(--color-surface-muted);
  font-weight: 600;
}

.placeholder-panel {
  min-height: 220px;
}

.check-list {
  display: grid;
  gap: var(--space-2);
  margin: 14px 0 0;
  padding-left: 20px;
  color: var(--color-text-secondary);
}

.function-list {
  display: grid;
  gap: 10px;
}

.function-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-3);
  align-items: start;
  padding: var(--space-3);
}

.function-item code,
.endpoint-code,
.smoke-card code,
.settings-list code,
.log-row code {
  color: var(--color-primary);
  font-size: 12px;
}

.function-item code {
  display: inline-block;
  margin-top: var(--space-2);
}

.status-bar {
  height: 40px;
  border-top: var(--border-width) solid var(--color-border-subtle);
  background: var(--color-shell);
  color: var(--color-text-muted);
  display: flex;
  gap: var(--space-4);
  align-items: center;
  padding: 0 var(--space-5);
  font-size: 12px;
}

.capture-form,
.training-form {
  display: grid;
  gap: var(--space-3);
}

.capture-form label,
.training-form label {
  display: grid;
  gap: 6px;
  color: var(--color-text-secondary);
  font-size: 13px;
}

.capture-form input,
.capture-form select,
.capture-form textarea,
.training-form input {
  width: 100%;
}

.capture-form textarea {
  resize: vertical;
}

.success-message,
.error-message,
.warning-box {
  line-height: 1.45;
  overflow-wrap: anywhere;
  padding: 9px 11px;
  border: var(--border-width) solid transparent;
  border-radius: var(--radius-md);
}

.success-message {
  color: var(--color-success);
  background: var(--color-success-surface);
  border-color: color-mix(in srgb, var(--color-success) 36%, transparent);
}

.error-message {
  color: var(--color-danger);
  background: var(--color-danger-surface);
  border-color: color-mix(in srgb, var(--color-danger) 36%, transparent);
}

.warning-box {
  color: var(--color-warning);
  background: var(--color-warning-surface);
  border-color: color-mix(in srgb, var(--color-warning) 36%, transparent);
}

.progress-track {
  height: 10px;
  margin: 6px 0 14px;
  overflow: hidden;
  border: var(--border-width) solid var(--color-border-default);
  border-radius: var(--radius-sm);
  background: var(--color-field);
}

.progress-track div {
  height: 100%;
  background: var(--color-secondary);
  transition: width 180ms ease;
}

.training-status-list {
  margin: var(--space-3) 0;
}

.training-status-list strong {
  max-width: 230px;
  overflow-wrap: anywhere;
}

.camera-status-list {
  display: grid;
  gap: var(--space-2);
}

.camera-status-list div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: 9px 0;
  border-bottom: var(--border-width) solid var(--color-border-subtle);
}

.camera-status-list div:last-child {
  border-bottom: 0;
}

.camera-status-list span { color: var(--color-text-muted); }
.camera-status-list strong { text-align: right; }

.endpoint-code {
  display: block;
  overflow-wrap: anywhere;
  margin: var(--space-3) 0;
  padding: 10px;
  border: var(--border-width) solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-field);
  line-height: 1.5;
}

.smoke-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
}

.smoke-card {
  padding: var(--space-3);
}

.smoke-card p {
  color: var(--color-text-muted);
  line-height: 1.45;
  margin: var(--space-2) 0;
}

.settings-list {
  display: grid;
  gap: 10px;
}

.settings-list div {
  display: grid;
  grid-template-columns: 170px minmax(0, 1fr);
  gap: var(--space-3);
  padding: 10px;
}

.settings-list span { color: var(--color-text-muted); }

.log-list {
  display: grid;
  gap: 10px;
}

.log-row {
  display: grid;
  grid-template-columns: 90px 150px 110px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  padding: 10px;
}

.log-row p { color: var(--color-text-secondary); }

.log-level-warning,
.log-level-warn {
  border-color: var(--color-warning);
  background: var(--color-warning-surface);
  color: var(--color-warning);
}

.log-level-error {
  border-color: var(--color-danger);
  background: var(--color-danger-surface);
  color: var(--color-danger);
}

/* Material color hierarchy refinements. */
.panel-header > div:first-child {
  min-width: 0;
}

.panel-header h2 + .placeholder-copy,
.panel-header h2 + p {
  margin-top: var(--space-1);
}

.metric-card strong {
  color: var(--color-text-primary);
}

.metric-card small {
  display: block;
  margin-top: var(--space-1);
  color: var(--color-text-muted);
  line-height: 1.35;
}

.status-info {
  border-color: var(--color-primary);
  background: var(--color-primary-surface);
  color: var(--color-primary);
}

.status-secondary {
  border-color: var(--color-secondary);
  background: var(--color-secondary-surface);
  color: var(--color-secondary);
}

.section-intro {
  max-width: 820px;
}

.action-note {
  padding: var(--space-3);
  border-left: 3px solid var(--color-primary);
  background: var(--color-primary-surface);
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.destructive-note {
  border-left-color: var(--color-danger);
  background: var(--color-danger-surface);
}
 

/* Compact, continuously refreshed saved-camera status strip. */
.camera-status-strip {
  display: grid;
  gap: var(--space-2);
}

.camera-status-strip-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
}

.camera-status-strip-header span {
  color: var(--color-text-muted);
  font-size: 12px;
}

.camera-status-strip-items {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.camera-status-entry {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding: var(--space-2);
  min-width: 0;
  border: var(--border-width) solid var(--color-border-subtle);
  border-radius: var(--radius-md);
}

.camera-status-entry.is-selected {
  border-color: var(--color-primary);
}

.camera-status-entry-name {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.camera-status-entry-name strong,
.camera-status-entry small {
  overflow-wrap: anywhere;
}

.camera-status-entry-name small {
  color: var(--color-primary);
}

.camera-status-entry > small {
  color: var(--color-text-muted);
}

.camera-fold > summary {
  cursor: pointer;
  font-weight: 600;
  color: var(--color-text-primary);
}

.camera-fold[open] > summary {
  margin-bottom: var(--space-3);
}

.camera-fold > summary:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 3px;
}

.camera-fold > summary .status-pill {
  float: right;
}

/* Consistent interactive card, form and dashboard treatments. */
.nav-button:focus-visible, .camera-fold > summary:focus-visible { outline: 3px solid var(--color-focus); outline-offset: 2px; }
.panel-header { min-width: 0; }
.panel-header > * { min-width: 0; }
.metric-card { background: var(--color-surface); box-shadow: var(--shadow-panel); }
.metric-card span { font-weight: 500; }
.metric-card strong { font-weight: 700; }
.camera-status-entry { background: var(--color-surface-raised); }
.camera-status-entry.is-selected { background: var(--color-primary-surface); }
input:not([type="checkbox"]):not([type="radio"]):not([type="range"]):focus-visible,
select:focus-visible, textarea:focus-visible { border-color: var(--color-primary); }
tbody tr:hover { background: var(--color-surface-muted); }
@media (max-width: 1100px) { .metric-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 600px) { .metric-strip, .smoke-grid { grid-template-columns: 1fr; } }

/* Camera selection keeps a visible state marker; navigation uses a quiet filled row. */
.camera-status-entry.is-selected::before {
  content: "";
  flex: 0 0 7px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-primary);
}
.camera-status-entry.is-selected { border-left: 3px solid var(--color-primary); }

button[aria-pressed="true"]:not(.primary):not(.danger) {
  border-color: var(--color-primary);
  background: var(--color-primary-surface);
  color: var(--color-primary);
}
.traffic-mode-tabs button[aria-pressed="true"]::before,
.experiment-toggle button[aria-pressed="true"]::before,
.junction-crosswalk-edge-choice[aria-pressed="true"]::before {
  content: "";
  display: inline-block;
  flex: 0 0 7px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  vertical-align: middle;
  margin-right: 7px;
}
~~~~

## `apps/pc-studio/backend/app/services/camera_frames.py`

~~~~python
from __future__ import annotations

from dataclasses import dataclass
import random
import re
from threading import Lock
import time

import cv2
import numpy as np

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.services.signal_rules import signal_rules_service

MAX_FRAME_BYTES = 8 * 1024 * 1024
SOURCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
SUPPORTED_UPLOAD_TYPES = {"image/jpeg", "image/png"}
SIMULATION_DENSITIES = {"light", "normal", "busy"}

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
ROAD_TOP = 179
ROAD_BOTTOM = 625
CROSSING_LEFT = 520
CROSSING_RIGHT = 760
EASTBOUND_STOP_LINE = 495
WESTBOUND_STOP_LINE = 785
TOP_PEDESTRIAN_WAIT_Y = 126
BOTTOM_PEDESTRIAN_WAIT_Y = 674


@dataclass(frozen=True)
class CameraFrame:
    """One displayable camera frame held in memory by PC Studio."""

    content: bytes
    content_type: str
    source_id: str
    width: int
    height: int
    received_at_ms: int
    frame_number: int
    origin: str

    def metadata(self) -> dict:
        return {
            "source_id": self.source_id,
            "content_type": self.content_type,
            "width": self.width,
            "height": self.height,
            "received_at_ms": self.received_at_ms,
            "frame_number": self.frame_number,
            "size_bytes": len(self.content),
            "origin": self.origin,
        }


@dataclass
class _SimVehicle:
    x: float
    y: int
    width: int
    speed: float
    direction: int
    color: tuple[int, int, int]
    vehicle_type: str


@dataclass
class _SimPedestrian:
    x: int
    y: float
    speed: float
    direction: int
    color: tuple[int, int, int]


def _png_dimensions(content: bytes) -> tuple[int, int] | None:
    if len(content) < 24 or content[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width = int.from_bytes(content[16:20], "big")
    height = int.from_bytes(content[20:24], "big")
    return (width, height) if width > 0 and height > 0 else None


def _jpeg_dimensions(content: bytes) -> tuple[int, int] | None:
    if len(content) < 4 or content[:2] != b"\xff\xd8":
        return None
    index = 2
    start_of_frame_markers = {
        0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
        0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
    }
    while index < len(content):
        while index < len(content) and content[index] != 0xFF:
            index += 1
        while index < len(content) and content[index] == 0xFF:
            index += 1
        if index >= len(content):
            break
        marker = content[index]
        index += 1
        if marker in {0x01, 0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if index + 2 > len(content):
            break
        segment_length = int.from_bytes(content[index:index + 2], "big")
        if segment_length < 2 or index + segment_length > len(content):
            break
        if marker in start_of_frame_markers and segment_length >= 7:
            height = int.from_bytes(content[index + 3:index + 5], "big")
            width = int.from_bytes(content[index + 5:index + 7], "big")
            return (width, height) if width > 0 and height > 0 else None
        index += segment_length
    return None


def _image_dimensions(content: bytes, content_type: str) -> tuple[int, int] | None:
    if content_type == "image/png":
        return _png_dimensions(content)
    if content_type == "image/jpeg":
        return _jpeg_dimensions(content)
    return None


def _draw_pedestrian(canvas: np.ndarray, x: int, y: int, color: tuple[int, int, int], stride: int) -> None:
    cv2.circle(canvas, (x, y - 28), 14, color, thickness=-1)
    cv2.line(canvas, (x, y - 12), (x, y + 24), color, thickness=10)
    cv2.line(canvas, (x, y), (x - 18, y + 18), color, thickness=8)
    cv2.line(canvas, (x, y), (x + 18, y + 18), color, thickness=8)
    cv2.line(canvas, (x, y + 22), (x - 12 - stride, y + 48), color, thickness=8)
    cv2.line(canvas, (x, y + 22), (x + 12 + stride, y + 48), color, thickness=8)


def _draw_vehicle(
    canvas: np.ndarray,
    *,
    x: int,
    y: int,
    width: int,
    color: tuple[int, int, int],
    vehicle_type: str,
) -> None:
    height = 58 if vehicle_type == "car" else 72
    body_top = y - height // 2
    body_bottom = y + height // 2
    cv2.rectangle(canvas, (x, body_top), (x + width, body_bottom), color, thickness=-1)
    if vehicle_type == "car":
        roof_left = x + width // 4
        roof_right = x + (width * 3) // 4
        cv2.rectangle(canvas, (roof_left, body_top - 22), (roof_right, body_top + 4), color, thickness=-1)
        cv2.rectangle(canvas, (roof_left + 7, body_top - 17), (roof_right - 7, body_top - 2), (77, 93, 110), thickness=-1)
    else:
        for window_x in range(x + 18, x + width - 20, 44):
            cv2.rectangle(
                canvas,
                (window_x, body_top + 10),
                (min(window_x + 28, x + width - 12), body_top + 31),
                (77, 93, 110),
                thickness=-1,
            )
    wheel_y = body_bottom + 4
    cv2.circle(canvas, (x + 34, wheel_y), 14, (18, 20, 23), thickness=-1)
    cv2.circle(canvas, (x + width - 34, wheel_y), 14, (18, 20, 23), thickness=-1)
    cv2.circle(canvas, (x + 34, wheel_y), 6, (125, 133, 144), thickness=-1)
    cv2.circle(canvas, (x + width - 34, wheel_y), 6, (125, 133, 144), thickness=-1)


class CameraFrameService:
    """Store the latest uploaded frame and provide a signal-aware hardware-free simulator."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._uploaded_frame: CameraFrame | None = None
        self._simulation_frame: CameraFrame | None = None
        self._mirrored_frame: CameraFrame | None = None
        self._simulation_source_id = "simulation_camera"
        self._simulation_enabled = False
        self._simulation_paused = False
        self._simulation_density = "normal"
        self._simulation_seed = int(time.time() * 1000) & 0x7FFFFFFF
        self._frame_counter = 0
        self._last_simulation_tick = -1
        self._simulation_clock_s = 0.0
        self._simulation_last_update_monotonic: float | None = None
        self._vehicles: list[_SimVehicle] = []
        self._pedestrians: list[_SimPedestrian] = []
        self._simulation_rng = random.Random(self._simulation_seed)

    def store_upload(self, *, source_id: str, content_type: str, content: bytes) -> CameraFrame:
        normalized_type = content_type.split(";", maxsplit=1)[0].strip().lower()
        if not SOURCE_ID_PATTERN.fullmatch(source_id):
            raise AppError(
                ErrorCode.CAMERA_SOURCE_INVALID,
                "source_id must contain 1-64 letters, numbers, dots, dashes, or underscores.",
                status_code=422,
                details={"source_id": source_id},
            )
        if normalized_type not in SUPPORTED_UPLOAD_TYPES:
            raise AppError(
                ErrorCode.CAMERA_FRAME_TYPE_UNSUPPORTED,
                "Camera uploads must be JPEG or PNG images.",
                status_code=415,
                details={"content_type": normalized_type or "missing"},
            )
        if not content:
            raise AppError(ErrorCode.CAMERA_FRAME_INVALID, "The camera upload did not contain image bytes.", status_code=422)
        if len(content) > MAX_FRAME_BYTES:
            raise AppError(
                ErrorCode.CAMERA_FRAME_TOO_LARGE,
                "The camera frame is larger than the 8 MiB limit.",
                status_code=413,
                details={"size_bytes": len(content), "max_size_bytes": MAX_FRAME_BYTES},
            )
        dimensions = _image_dimensions(content, normalized_type)
        if dimensions is None:
            raise AppError(
                ErrorCode.CAMERA_FRAME_INVALID,
                "The uploaded bytes are not a valid supported image.",
                status_code=422,
                details={"content_type": normalized_type},
            )
        with self._lock:
            self._frame_counter += 1
            frame = CameraFrame(
                content=content,
                content_type=normalized_type,
                source_id=source_id,
                width=dimensions[0],
                height=dimensions[1],
                received_at_ms=int(time.time() * 1000),
                frame_number=self._frame_counter,
                origin="upload",
            )
            self._uploaded_frame = frame
            return frame

    def _reset_simulation_locked(self) -> None:
        self._simulation_frame = None
        self._mirrored_frame = None
        self._last_simulation_tick = -1
        self._simulation_clock_s = 0.0
        self._simulation_last_update_monotonic = time.monotonic()
        signal_rules_service.reset_runtime(0.0)
        density_offset = {"light": 101, "normal": 211, "busy": 307}[self._simulation_density]
        self._simulation_rng = random.Random(self._simulation_seed + density_offset)
        self._initialize_agents_locked()

    def set_simulation(self, enabled: bool) -> dict:
        with self._lock:
            self._simulation_enabled = enabled
            self._simulation_paused = False
            if enabled:
                self._reset_simulation_locked()
            else:
                self._simulation_frame = None
                self._mirrored_frame = None
                self._last_simulation_tick = -1
                self._simulation_last_update_monotonic = None
                self._vehicles = []
                self._pedestrians = []
                signal_rules_service.reset_runtime(0.0)
        return self.status()

    def configure_simulation(self, *, density: str | None = None, paused: bool | None = None) -> dict:
        with self._lock:
            reset_agents = False
            if density is not None:
                normalized_density = density.strip().lower()
                if normalized_density not in SIMULATION_DENSITIES:
                    raise AppError(
                        ErrorCode.INVALID_REQUEST,
                        "Simulation density must be light, normal, or busy.",
                        status_code=422,
                        details={"density": density, "allowed": sorted(SIMULATION_DENSITIES)},
                    )
                if normalized_density != self._simulation_density:
                    self._simulation_density = normalized_density
                    reset_agents = True
            if paused is not None:
                if not self._simulation_enabled:
                    raise AppError(
                        ErrorCode.CAMERA_STREAM_NOT_STARTED,
                        "Start simulation mode before pausing or resuming the synthetic scene.",
                        status_code=409,
                    )
                if paused != self._simulation_paused:
                    self._simulation_paused = paused
                    self._simulation_last_update_monotonic = time.monotonic()
                    if not paused:
                        self._simulation_frame = None
                        self._last_simulation_tick = -1
            if reset_agents and self._simulation_enabled:
                self._reset_simulation_locked()
        return self.status()

    def set_simulation_source(self, source_id: str) -> None:
        if source_id not in {"simulation_camera", "simulation_camera_b"}:
            raise ValueError("Unknown simulation camera")
        with self._lock:
            self._simulation_source_id = source_id

    def _simulation_frame_for_locked(self, source_id: str) -> CameraFrame | None:
        if not self._simulation_enabled:
            return None
        if self._simulation_frame is None or not self._simulation_paused:
            self._refresh_simulation_locked()
        original = self._simulation_frame
        if original is None or source_id == "simulation_camera":
            return original
        if source_id != "simulation_camera_b":
            raise ValueError("Unknown simulation camera")
        if self._mirrored_frame is None or self._mirrored_frame.frame_number != original.frame_number:
            image = cv2.imdecode(np.frombuffer(original.content, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                raise AppError(ErrorCode.CAMERA_FRAME_READ_FAILED, "Simulation frame decode failed.", status_code=500)
            success, encoded = cv2.imencode(".png", cv2.flip(image, 0))
            if not success:
                raise AppError(ErrorCode.CAMERA_FRAME_READ_FAILED, "Mirrored simulation frame encoding failed.", status_code=500)
            self._mirrored_frame = CameraFrame(
                content=encoded.tobytes(), content_type="image/png",
                source_id="simulation_camera_b", width=original.width, height=original.height,
                received_at_ms=original.received_at_ms, frame_number=original.frame_number,
                origin="simulation",
            )
        return self._mirrored_frame

    def simulation_frame_for(self, source_id: str) -> CameraFrame | None:
        with self._lock:
            return self._simulation_frame_for_locked(source_id)

    def latest_frame(self) -> CameraFrame | None:
        with self._lock:
            if self._simulation_enabled:
                return self._simulation_frame_for_locked(self._simulation_source_id)
            return self._uploaded_frame

    def simulation_signal_state(self) -> dict:
        with self._lock:
            return dict(self._simulation_signal_state_locked())

    def reset_simulation_signal_policy(self) -> dict:
        """Reset transient adaptive policy state at the current simulation clock."""
        with self._lock:
            return signal_rules_service.reset_runtime(self._simulation_clock_s)

    def status(self) -> dict:
        frame = self.latest_frame()
        now_ms = int(time.time() * 1000)
        age_ms = now_ms - frame.received_at_ms if frame else None
        with self._lock:
            simulation_enabled = self._simulation_enabled
            simulation_paused = self._simulation_paused
            simulation_density = self._simulation_density
            signal = self._simulation_signal_state_locked() if simulation_enabled else None
        return {
            "mode": "simulation" if simulation_enabled else "receiver",
            "simulation_enabled": simulation_enabled,
            "simulation_paused": simulation_paused,
            "simulation_density": simulation_density,
            "simulation_signal_phase": signal["phase"] if signal else None,
            "simulation_signal_seconds_remaining": signal["seconds_remaining"] if signal else None,
            "simulation_signal_cycle_seconds": signal["base_cycle_seconds"] if signal else None,
            "simulation_signal_vehicle_go": signal["vehicle_go"] if signal else False,
            "simulation_signal_pedestrian_walk": signal["pedestrian_walk"] if signal else False,
            "simulation_signal_mode": signal["mode"] if signal else None,
            "simulation_signal_profile": signal["active_profile"] if signal else None,
            "simulation_signal_active_rules": signal["active_rules"] if signal else [],
            "frame_available": frame is not None,
            "streaming": frame is not None and (
                (simulation_enabled and not simulation_paused)
                or (not simulation_enabled and age_ms is not None and age_ms <= 5000)
            ),
            "active_source_id": frame.source_id if frame else None,
            "resolution": {"width": frame.width, "height": frame.height} if frame else None,
            "content_type": frame.content_type if frame else None,
            "received_at_ms": frame.received_at_ms if frame else None,
            "age_ms": age_ms,
            "frame_number": frame.frame_number if frame else 0,
            "size_bytes": len(frame.content) if frame else 0,
            "origin": frame.origin if frame else None,
            "stale": bool(frame and not simulation_enabled and age_ms is not None and age_ms > 5000),
            "frame_url": "/api/camera/frame" if frame else None,
            "upload_endpoint": "/api/camera/frame?source_id=<camera_id>",
        }

    @property
    def simulation_enabled(self) -> bool:
        with self._lock:
            return self._simulation_enabled

    def _simulation_signal_state_locked(self) -> dict:
        return signal_rules_service.signal_state(self._simulation_clock_s)

    def _initialize_agents_locked(self) -> None:
        vehicle_count = {"light": 4, "normal": 8, "busy": 12}[self._simulation_density]
        pedestrian_count = {"light": 4, "normal": 7, "busy": 11}[self._simulation_density]
        vehicle_palette = [
            (66, 135, 245), (94, 176, 110), (230, 144, 81),
            (181, 105, 200), (94, 188, 214), (122, 128, 137),
        ]
        pedestrian_palette = [
            (196, 111, 255), (119, 187, 255), (119, 220, 157),
            (255, 158, 132), (164, 142, 245), (114, 212, 229),
        ]
        self._vehicles = []
        for index in range(vehicle_count):
            direction = 1 if index % 2 == 0 else -1
            lane_index = index // 2
            vehicle_type = "bus" if index % 5 == 4 else "car"
            width = 220 if vehicle_type == "bus" else self._simulation_rng.randint(125, 170)
            spacing = 300
            if direction > 0:
                x = -240.0 + lane_index * spacing
                y = 265
            else:
                x = float(FRAME_WIDTH + 60 - width - lane_index * spacing)
                y = 455
            speed = float(self._simulation_rng.randint(92, 125))
            self._vehicles.append(
                _SimVehicle(
                    x=x,
                    y=y,
                    width=width,
                    speed=speed,
                    direction=direction,
                    color=vehicle_palette[index % len(vehicle_palette)],
                    vehicle_type=vehicle_type,
                )
            )
        self._pedestrians = []
        for index in range(pedestrian_count):
            direction = 1 if index % 2 == 0 else -1
            x = CROSSING_LEFT + 42 + (index * 47) % (CROSSING_RIGHT - CROSSING_LEFT - 84)
            if direction > 0:
                y = float(max(65, TOP_PEDESTRIAN_WAIT_Y - (index // 2) * 22))
            else:
                y = float(min(710, BOTTOM_PEDESTRIAN_WAIT_Y + (index // 2) * 18))
            self._pedestrians.append(
                _SimPedestrian(
                    x=x,
                    y=y,
                    speed=float(self._simulation_rng.randint(88, 106)),
                    direction=direction,
                    color=pedestrian_palette[index % len(pedestrian_palette)],
                )
            )

    def _advance_simulation_locked(self, dt: float) -> None:
        if dt <= 0 or self._simulation_paused:
            return
        remaining = min(dt, 2.0)
        while remaining > 1e-9:
            step = min(0.05, remaining)
            self._simulation_clock_s += step
            self._advance_vehicles_locked(step)
            self._advance_pedestrians_locked(step)
            remaining -= step

    def _advance_vehicles_locked(self, dt: float) -> None:
        phase = self._simulation_signal_state_locked()["phase"]
        vehicle_go = phase == "vehicle_green"
        gap = 22.0
        eastbound = sorted((v for v in self._vehicles if v.direction > 0), key=lambda item: item.x, reverse=True)
        ahead: _SimVehicle | None = None
        for vehicle in eastbound:
            proposed = vehicle.x + vehicle.speed * dt
            front = vehicle.x + vehicle.width
            already_committed = front > EASTBOUND_STOP_LINE
            if not vehicle_go and not already_committed:
                proposed = min(proposed, EASTBOUND_STOP_LINE - 8 - vehicle.width)
            if ahead is not None:
                proposed = min(proposed, ahead.x - gap - vehicle.width)
            vehicle.x = proposed
            ahead = vehicle
        westbound = sorted((v for v in self._vehicles if v.direction < 0), key=lambda item: item.x)
        ahead = None
        for vehicle in westbound:
            proposed = vehicle.x - vehicle.speed * dt
            front = vehicle.x
            already_committed = front < WESTBOUND_STOP_LINE
            if not vehicle_go and not already_committed:
                proposed = max(proposed, WESTBOUND_STOP_LINE + 8)
            if ahead is not None:
                proposed = max(proposed, ahead.x + ahead.width + gap)
            vehicle.x = proposed
            ahead = vehicle
        for vehicle in self._vehicles:
            if vehicle.direction > 0 and vehicle.x > FRAME_WIDTH + 120:
                peers = [item.x for item in self._vehicles if item.direction > 0 and item is not vehicle]
                vehicle.x = min(
                    -vehicle.width - self._simulation_rng.randint(80, 180),
                    min(peers, default=-120.0) - vehicle.width - self._simulation_rng.randint(70, 140),
                )
            elif vehicle.direction < 0 and vehicle.x + vehicle.width < -120:
                peers = [item.x + item.width for item in self._vehicles if item.direction < 0 and item is not vehicle]
                vehicle.x = max(
                    float(FRAME_WIDTH + self._simulation_rng.randint(80, 180)),
                    max(peers, default=float(FRAME_WIDTH + 120)) + self._simulation_rng.randint(70, 140),
                )

    def _advance_pedestrians_locked(self, dt: float) -> None:
        phase = self._simulation_signal_state_locked()["phase"]
        can_start_crossing = phase == "pedestrian_green"
        for pedestrian in self._pedestrians:
            delta = pedestrian.speed * dt * pedestrian.direction
            if pedestrian.direction > 0:
                if pedestrian.y < TOP_PEDESTRIAN_WAIT_Y:
                    pedestrian.y = min(TOP_PEDESTRIAN_WAIT_Y, pedestrian.y + pedestrian.speed * dt)
                elif pedestrian.y <= TOP_PEDESTRIAN_WAIT_Y + 0.5 and not can_start_crossing:
                    pedestrian.y = float(TOP_PEDESTRIAN_WAIT_Y)
                else:
                    pedestrian.y += pedestrian.speed * dt
                if pedestrian.y > FRAME_HEIGHT + 25:
                    pedestrian.y = float(70 - self._simulation_rng.randint(0, 42))
            else:
                if pedestrian.y > BOTTOM_PEDESTRIAN_WAIT_Y:
                    pedestrian.y = max(BOTTOM_PEDESTRIAN_WAIT_Y, pedestrian.y - pedestrian.speed * dt)
                elif pedestrian.y >= BOTTOM_PEDESTRIAN_WAIT_Y - 0.5 and not can_start_crossing:
                    pedestrian.y = float(BOTTOM_PEDESTRIAN_WAIT_Y)
                else:
                    pedestrian.y += delta
                if pedestrian.y < 20:
                    pedestrian.y = float(FRAME_HEIGHT - 10 + self._simulation_rng.randint(0, 36))

    def _refresh_simulation_locked(self) -> None:
        now_mono = time.monotonic()
        if self._simulation_last_update_monotonic is None:
            self._simulation_last_update_monotonic = now_mono
        dt = now_mono - self._simulation_last_update_monotonic
        self._simulation_last_update_monotonic = now_mono
        if not self._simulation_paused:
            self._advance_simulation_locked(dt)
        tick = int(self._simulation_clock_s * 2)
        if self._simulation_frame is not None and tick == self._last_simulation_tick:
            return
        self._last_simulation_tick = tick
        self._mirrored_frame = None
        self._frame_counter += 1
        now_ms = int(time.time() * 1000)
        signal = self._simulation_signal_state_locked()

        canvas = np.full((FRAME_HEIGHT, FRAME_WIDTH, 3), (29, 33, 37), dtype=np.uint8)
        cv2.rectangle(canvas, (0, 0), (FRAME_WIDTH - 1, ROAD_TOP - 1), (72, 79, 84), thickness=-1)
        cv2.rectangle(canvas, (0, ROAD_TOP), (FRAME_WIDTH - 1, ROAD_BOTTOM - 1), (48, 52, 57), thickness=-1)
        cv2.rectangle(canvas, (0, ROAD_BOTTOM), (FRAME_WIDTH - 1, FRAME_HEIGHT - 1), (72, 79, 84), thickness=-1)
        cv2.line(canvas, (0, ROAD_TOP), (FRAME_WIDTH - 1, ROAD_TOP), (128, 136, 144), thickness=5)
        cv2.line(canvas, (0, ROAD_BOTTOM), (FRAME_WIDTH - 1, ROAD_BOTTOM), (128, 136, 144), thickness=5)
        for lane_y in (310, 500):
            for x in range(0, FRAME_WIDTH, 86):
                cv2.line(canvas, (x, lane_y), (min(x + 50, FRAME_WIDTH - 1), lane_y), (46, 176, 224), thickness=5)
        cv2.rectangle(canvas, (CROSSING_LEFT, ROAD_TOP), (CROSSING_RIGHT, ROAD_BOTTOM), (55, 59, 63), thickness=-1)
        for stripe_y in range(205, 610, 46):
            cv2.rectangle(
                canvas,
                (CROSSING_LEFT + 18, stripe_y),
                (CROSSING_RIGHT - 18, stripe_y + 22),
                (225, 228, 230),
                thickness=-1,
            )
        cv2.line(canvas, (EASTBOUND_STOP_LINE, ROAD_TOP), (EASTBOUND_STOP_LINE, ROAD_BOTTOM), (240, 240, 240), thickness=6)
        cv2.line(canvas, (WESTBOUND_STOP_LINE, ROAD_TOP), (WESTBOUND_STOP_LINE, ROAD_BOTTOM), (240, 240, 240), thickness=6)
        cv2.putText(canvas, "STOP", (410, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (220, 220, 220), 2)
        cv2.putText(canvas, "STOP", (800, 445), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (220, 220, 220), 2)
        for vehicle in self._vehicles:
            _draw_vehicle(
                canvas,
                x=int(round(vehicle.x)),
                y=vehicle.y,
                width=vehicle.width,
                color=vehicle.color,
                vehicle_type=vehicle.vehicle_type,
            )
        stride_sign = 5 if tick % 2 == 0 else -5
        for index, pedestrian in enumerate(self._pedestrians):
            _draw_pedestrian(
                canvas,
                x=pedestrian.x,
                y=int(round(pedestrian.y)),
                color=pedestrian.color,
                stride=stride_sign if index % 2 == 0 else -stride_sign,
            )
        self._draw_signal_heads(canvas, signal)
        cv2.rectangle(canvas, (24, 20), (564, 126), (14, 17, 20), thickness=-1)
        cv2.putText(canvas, "PC CAMERA SIMULATION - SIGNAL AWARE", (42, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (126, 231, 135), 2)
        cv2.putText(
            canvas,
            f"density: {self._simulation_density}   pedestrians: {len(self._pedestrians)}   vehicles: {len(self._vehicles)}",
            (42, 72),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (217, 221, 224),
            1,
        )
        cv2.putText(
            canvas,
            f"signal: {signal['phase'].replace('_', ' ')}   {signal['seconds_remaining']:.1f}s",
            (42, 94),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.44,
            (217, 221, 224),
            1,
        )
        rule_label = ", ".join(signal.get("active_rules", [])[:2]) or "normal timing"
        state_label = "paused" if self._simulation_paused else f"frame {self._frame_counter}"
        cv2.putText(
            canvas,
            f"policy: {signal.get('mode', 'fixed')} / {signal.get('active_profile', 'Normal')}   {rule_label}   {state_label}",
            (42, 116),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            (217, 221, 224),
            1,
        )
        encoded_ok, encoded = cv2.imencode(".png", canvas)
        if not encoded_ok:
            raise AppError(
                ErrorCode.CAMERA_FRAME_READ_FAILED,
                "Failed to encode the synthetic camera frame.",
                status_code=500,
            )
        self._simulation_frame = CameraFrame(
            content=encoded.tobytes(),
            content_type="image/png",
            source_id="simulation_camera",
            width=FRAME_WIDTH,
            height=FRAME_HEIGHT,
            received_at_ms=now_ms,
            frame_number=self._frame_counter,
            origin="simulation",
        )

    @staticmethod
    def _draw_signal_heads(canvas: np.ndarray, signal: dict) -> None:
        phase = signal["phase"]
        red_on = phase not in {"vehicle_green", "vehicle_yellow"}
        amber_on = phase == "vehicle_yellow"
        green_on = phase == "vehicle_green"
        housing_x, housing_y = 1084, 206
        housing_width, housing_height = 66, 186
        cv2.rectangle(canvas, (housing_x, housing_y), (housing_x + housing_width, housing_y + housing_height), (18, 20, 23), thickness=-1)
        lamps = [
            ((housing_x + 33, housing_y + 34), (35, 35, 120), (70, 70, 255), red_on),
            ((housing_x + 33, housing_y + 93), (35, 95, 110), (0, 205, 255), amber_on),
            ((housing_x + 33, housing_y + 152), (35, 95, 35), (60, 220, 80), green_on),
        ]
        for center, off_color, on_color, active in lamps:
            cv2.circle(canvas, center, 19, on_color if active else off_color, thickness=-1)
        ped_walk = phase == "pedestrian_green"
        ped_clear = phase == "pedestrian_flashing"
        ped_x, ped_y = 1158, 228
        ped_width, ped_height = 84, 92
        cv2.rectangle(canvas, (ped_x, ped_y), (ped_x + ped_width, ped_y + ped_height), (18, 20, 23), thickness=-1)
        ped_text = "WALK" if ped_walk else "CLEAR" if ped_clear else "WAIT"
        ped_color = (70, 230, 90) if ped_walk else (0, 205, 255) if ped_clear else (70, 70, 255)
        cv2.putText(canvas, "PED", (ped_x + 20, ped_y + 27), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (220, 220, 220), 1)
        text_x = ped_x + 10 if ped_text == "CLEAR" else ped_x + 15
        cv2.putText(canvas, ped_text, (text_x, ped_y + 63), cv2.FONT_HERSHEY_SIMPLEX, 0.48, ped_color, 2)


camera_frame_service = CameraFrameService()
~~~~

## `scripts/test_simulation_frame_layout.py`

~~~~python
"""Focused layout checks for the signal-aware simulation frame."""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.camera_frames import CameraFrameService  # noqa: E402


def _decode_png(png_bytes: bytes) -> np.ndarray:
    frame = cv2.imdecode(np.frombuffer(png_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise AssertionError("Simulation frame did not decode as PNG")
    return frame


def main() -> int:
    service = CameraFrameService()
    service.set_simulation(True)
    frame = service.latest_frame()
    assert frame is not None
    image = _decode_png(frame.content)

    # The compact metadata panel still exists in the top-left corner.
    assert int(image[40, 40].mean()) < 40
    # The resized panel should no longer extend deep into the upper-left scene.
    assert int(image[90, 620].mean()) > 45
    assert int(image[150, 120].mean()) > 45

    # The traffic signal housing remains visible.
    assert int(image[240, 1095].mean()) < 40
    # The pedestrian signal should be smaller, leaving the far-right lane visible.
    assert int(image[300, 1250].mean()) > 45

    print("[PASS] simulation metadata panel stays compact and leaves more scene visible")
    print("[PASS] pedestrian signal housing is reduced and no longer dominates the right lane")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
~~~~

