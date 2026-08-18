import { FunctionChecklist } from "../components/FunctionChecklist";
import { MetricStrip } from "../components/MetricStrip";
import { PROJECT_VERSION } from "../constants/projectVersion";
import type { ApiConnectionState, BackendHealth, SmokeStatus } from "../types";

type Props = {
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

export function DashboardPage({ health, smokeStatus, apiState, onRefresh, refreshing }: Props) {
  const passCount = smokeStatus?.checks.filter((check) => check.status === "pass").length ?? 0;
  const warnCount = smokeStatus?.checks.filter((check) => check.status === "warn").length ?? 0;
  const version = health?.version ?? smokeStatus?.version ?? PROJECT_VERSION;

  return (
    <div className="page-stack">
      <MetricStrip
        metrics={[
          { label: "Release", value: version, note: "current candidate" },
          { label: "Backend", value: apiState.status, note: health?.mode ?? "checking" },
          { label: "Validation", value: `${passCount} passed`, note: warnCount ? `${warnCount} warning${warnCount === 1 ? "" : "s"}` : "no smoke warnings" },
          { label: "Operating scope", value: "local prototype", note: "simulation, vision, datasets, analytics" },
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
        <div className="smoke-grid">
          {(smokeStatus?.checks ?? []).map((check) => (
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
          <div className="panel-header"><h2>Available now</h2><span className="status-pill status-implemented">test-ready</span></div>
          <ul className="check-list">
            {(smokeStatus?.ready_for ?? []).map((item) => <li key={item}>{item.split("_").join(" ")}</li>)}
          </ul>
        </section>
        <section className="panel">
          <div className="panel-header"><h2>Not available / out of scope</h2><span className="status-pill muted">bounded scope</span></div>
          <ul className="check-list">
            {(smokeStatus?.not_ready_for ?? []).map((item) => <li key={item}>{item.split("_").join(" ")}</li>)}
          </ul>
          <p className="small-note">Signal decisions and timing changes are confined to the software simulation. PC Studio does not connect to physical public-road signal infrastructure.</p>
        </section>
      </div>
      <FunctionChecklist limit={10} />
    </div>
  );
}
