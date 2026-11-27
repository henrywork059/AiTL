import { FunctionChecklist } from "../components/FunctionChecklist";
import { MetricStrip } from "../components/MetricStrip";
import { PROJECT_VERSION } from "../constants/projectVersion";
import type { ApiConnectionState, BackendHealth, CameraStatus, SmokeStatus } from "../types";

import type { AppPageId } from "../types/app";

type Props = {
  cameraStatus: CameraStatus | null;
  onNavigate: (page: AppPageId) => void;
  health: BackendHealth | null;
  smokeStatus: SmokeStatus | null;
  apiState: ApiConnectionState;
  onRefresh: () => void;
  refreshing: boolean;
};

function statusClass(status: string) {
  if (status === "pass" || status === "connected") return "status-pill status-implemented";
  if (status === "warn" || status === "fallback" || status === "checking") return "status-pill status-planned";
  return "status-pill status-error";
}

export function DashboardPage({ health, smokeStatus, apiState, onRefresh, refreshing, cameraStatus, onNavigate }: Props) {
  const verifiedSmoke = apiState.status === "connected" ? smokeStatus : null;
  const passCount = verifiedSmoke?.checks.filter((check) => check.status === "pass").length ?? 0;
  const warnCount = verifiedSmoke?.checks.filter((check) => check.status === "warn").length ?? 0;
  const version = health?.version ?? smokeStatus?.version ?? PROJECT_VERSION;

  const source = apiState.status === "connected" ? cameraStatus : null;
  const sourceState = !source ? "Unavailable" : source.simulation_fault ? "Simulation fault" : source.simulation_enabled && source.simulation_paused ? "Simulation paused" : !source.frame_available ? "No frame" : source.stale ? "Stale frame" : "Frame available";
  return (
    <div className="page-stack">
      <section className="panel workspace-device-summary" aria-label="Device overview">
        <div className="panel-header"><div><h2>Camera input</h2><p className="small-note">Last reported source status. Open Devices for live preview and controls.</p></div><span className="status-pill muted">{sourceState}</span></div>
        <div className="workspace-device-facts"><div><span>Source</span><strong>{source?.active_source_id ?? "Not available"}</strong></div><div><span>Mode</span><strong>{!source ? "Unknown" : source.simulation_enabled ? "Synthetic" : "Receiver"}</strong></div><div><span>Frame size</span><strong>{source?.frame_available && source.resolution ? `${source.resolution.width} × ${source.resolution.height}` : "—"}</strong></div></div>
        <div className="button-row wrap-row"><button type="button" className="primary" onClick={() => onNavigate("camera_settings")}>Open cameras</button><button type="button" onClick={() => onNavigate("camera_diagnostics")}>Diagnostics</button><button type="button" onClick={() => onNavigate("junction_network")}>Network</button><button type="button" onClick={onRefresh} disabled={refreshing}>{refreshing ? "Refreshing..." : "Refresh"}</button></div>
      </section>
      <MetricStrip
        metrics={[
          { label: "Release", value: version, note: "installed version" },
          { label: "Backend", value: apiState.status, note: health?.mode ?? "checking" },
          { label: "Validation", value: verifiedSmoke ? `${passCount} passed` : "Unavailable", note: verifiedSmoke ? (warnCount ? `${warnCount} warning${warnCount === 1 ? "" : "s"}` : "no smoke warnings") : "No verified checks" },
          { label: "Mode", value: health?.mode ?? "checking", note: "PC Studio" },
        ]}
      />

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>System overview</h2>
            <p className="placeholder-copy">{apiState.message}</p>
          </div>
          <button className="primary" onClick={onRefresh} disabled={refreshing}>{refreshing ? "Refreshing..." : "Refresh status"}</button>
        </div>
        {!verifiedSmoke && <p className="small-note" role="status">Validation results are unavailable.</p>}
        <div className="smoke-grid">
          {(verifiedSmoke?.checks ?? []).map((check) => (
            <article className="smoke-card" key={check.id}>
              <div className="panel-header compact-header">
                <strong>{check.label}</strong>
                <span className={statusClass(check.status)}>{check.status}</span>
              </div>
              <p>{check.detail}</p>
              <code>{check.id}</code>
            </article>
          ))}
        </div>
      </section>

      <div className="two-column-grid">
        <section className="panel">
          <div className="panel-header"><h2>Available now</h2></div>
          {!verifiedSmoke && <p className="small-note">Availability has not been verified.</p>}
          <ul className="check-list">
            {(verifiedSmoke?.ready_for ?? []).map((item) => <li key={item}>{item.split("_").join(" ")}</li>)}
          </ul>
        </section>
        <section className="panel">
          <div className="panel-header"><h2>Out of scope</h2></div>
          <ul className="check-list">
            {(verifiedSmoke?.not_ready_for ?? []).map((item) => <li key={item}>{item.split("_").join(" ")}</li>)}
          </ul>
          <p className="small-note">Signal decisions and timing changes are confined to the software simulation. PC Studio does not connect to physical public-road signal infrastructure.</p>
        </section>
      </div>
      <FunctionChecklist limit={10} />
    </div>
  );
}
