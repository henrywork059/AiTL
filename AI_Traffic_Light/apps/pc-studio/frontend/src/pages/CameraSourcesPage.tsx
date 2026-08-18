import { API_BASE } from "../api";
import { FunctionChecklist } from "../components/FunctionChecklist";
import { SimulationControls } from "../components/SimulationControls";
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
  const imageUrl = status?.frame_available
    ? `${API_BASE}/api/camera/frame?v=${status.frame_number}`
    : null;
  const statusLabel = !status
    ? "checking"
    : status.simulation_enabled
      ? status.simulation_paused
        ? "simulation paused"
        : "simulation running"
      : status.frame_available
        ? status.stale
          ? "frame stale"
          : "device frame live"
        : "waiting for device";

  return (
    <div className="page-stack">
      <div className="camera-layout">
        <section className="panel camera-preview-panel">
          <div className="panel-header">
            <div>
              <h2>Camera input</h2>
              <p className="placeholder-copy">Shows the newest frame accepted by the backend. Use the built-in simulation when camera hardware is unavailable.</p>
            </div>
            <span className={`status-pill ${status?.stale ? "status-planned" : status?.frame_available ? "status-implemented" : ""}`}>{statusLabel}</span>
          </div>

          <div className="camera-frame-wrapper">
            {imageUrl ? (
              <img
                className="camera-frame"
                src={imageUrl}
                alt={`Latest frame from ${status?.active_source_id ?? "camera"}`}
              />
            ) : (
              <div className="camera-empty-state">
                <strong>No frame available</strong>
                <p>Start the local simulation or send a JPEG/PNG frame from a configured camera node.</p>
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

          <SimulationControls status={status} onStatusChange={onStatusChange} />
        </section>

        <aside className="side-column">
          <section className="panel compact-panel">
            <div className="panel-header"><h2>Input status</h2></div>
            <div className="camera-status-list">
              <div><span>Mode</span><strong>{status?.mode ?? "checking"}</strong></div>
              <div><span>Source</span><strong>{status?.active_source_id ?? "none"}</strong></div>
              <div><span>Resolution</span><strong>{status?.resolution ? `${status.resolution.width} × ${status.resolution.height}` : "unknown"}</strong></div>
              <div><span>Frame age</span><strong>{formatAge(status?.age_ms ?? null)}</strong></div>
              <div><span>Frame number</span><strong>#{status?.frame_number ?? 0}</strong></div>
              <div><span>Simulation density</span><strong>{status?.simulation_density ?? "normal"}</strong></div>
              <div><span>Simulation motion</span><strong>{status?.simulation_paused ? "paused" : "running"}</strong></div>
            </div>
          </section>

          <section className="panel compact-panel">
            <div className="panel-header"><h2>Camera-node upload</h2><span className="status-pill muted">local API</span></div>
            <p className="placeholder-copy">Camera devices can post a raw JPEG or PNG body to the backend receiver.</p>
            <code className="endpoint-code">POST {API_BASE}/api/camera/frame?source_id=esp_cam_01</code>
            <p className="small-note">Content-Type: image/jpeg or image/png · Maximum payload: 8 MiB.</p>
          </section>
        </aside>
      </div>
      <FunctionChecklist area="Camera" />
    </div>
  );
}
