import { API_BASE } from "../api";
import { FunctionChecklist } from "../components/FunctionChecklist";
import type { CameraStatus } from "../types";

type Props = {
  status: CameraStatus | null;
  onSimulationChange: (enabled: boolean) => void;
  changingMode: boolean;
};

function formatAge(ageMs: number | null): string {
  if (ageMs === null) return "No frame received";
  if (ageMs < 1000) return `${ageMs} ms ago`;
  return `${(ageMs / 1000).toFixed(1)} s ago`;
}

export function CameraSourcesPage({ status, onSimulationChange, changingMode }: Props) {
  const imageUrl = status?.frame_available
    ? `${API_BASE}/api/camera/frame?v=${status.frame_number}`
    : null;
  const statusLabel = !status
    ? "checking"
    : status.simulation_enabled
      ? "simulation active"
      : status.frame_available
        ? status.stale
          ? "frame stale"
          : "device frame received"
        : "waiting for device";

  return (
    <div className="page-stack">
      <div className="camera-layout">
        <section className="panel camera-preview-panel">
          <div className="panel-header">
            <div>
              <h2>Latest camera frame</h2>
              <p className="placeholder-copy">The preview updates automatically when a device uploads a new image.</p>
            </div>
            <span className={`status-pill ${status?.stale ? "status-planned" : ""}`}>{statusLabel}</span>
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
                <strong>Waiting for the first image</strong>
                <p>Start simulation mode now, or upload a JPEG/PNG from the future camera node.</p>
              </div>
            )}
          </div>

          <div className="button-row">
            <button
              onClick={() => onSimulationChange(!status?.simulation_enabled)}
              disabled={changingMode || !status}
            >
              {changingMode
                ? "Changing mode..."
                : status?.simulation_enabled
                  ? "Stop simulation"
                  : "Start simulation"}
            </button>
          </div>
        </section>

        <aside className="side-column">
          <section className="panel compact-panel">
            <div className="panel-header"><h2>Receiver status</h2></div>
            <div className="camera-status-list">
              <div><span>Mode</span><strong>{status?.mode ?? "checking"}</strong></div>
              <div><span>Source</span><strong>{status?.active_source_id ?? "none"}</strong></div>
              <div><span>Resolution</span><strong>{status?.resolution ? `${status.resolution.width} × ${status.resolution.height}` : "unknown"}</strong></div>
              <div><span>Last update</span><strong>{formatAge(status?.age_ms ?? null)}</strong></div>
              <div><span>Frame</span><strong>#{status?.frame_number ?? 0}</strong></div>
            </div>
          </section>

          <section className="panel compact-panel">
            <div className="panel-header"><h2>Future device upload</h2></div>
            <p className="placeholder-copy">Send a raw JPEG or PNG body to the PC backend:</p>
            <code className="endpoint-code">POST {API_BASE}/api/camera/frame?source_id=esp_cam_01</code>
            <p className="small-note">Header: Content-Type: image/jpeg or image/png · Maximum: 8 MiB</p>
          </section>
        </aside>
      </div>
      <FunctionChecklist area="Camera" />
    </div>
  );
}
