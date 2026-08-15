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
  if (status === "pass" || status === "connected") return "status-pill";
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
          { label: "Project stage", value: version, note: "traffic analytics + counting regions candidate" },
          { label: "Backend", value: apiState.status, note: health?.mode ?? "checking" },
          { label: "Smoke checks", value: `${passCount} pass`, note: `${warnCount} warnings` },
          { label: "Analytics", value: "history + regions", note: "sampled occupancy over time" },
        ]}
      />

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Local prototype status</h2>
            <p className="placeholder-copy">{apiState.message}</p>
          </div>
          <button onClick={onRefresh} disabled={refreshing}>{refreshing ? "Refreshing..." : "Refresh live APIs"}</button>
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
          <div className="panel-header"><h2>Working prototype functions</h2><span className="status-pill">test-ready</span></div>
          <ul className="check-list">
            {(smokeStatus?.ready_for ?? []).map((item) => <li key={item}>{item.split("_").join(" ")}</li>)}
          </ul>
        </section>
        <section className="panel">
          <div className="panel-header"><h2>Explicit boundaries</h2><span className="status-pill status-planned">not enabled</span></div>
          <ul className="check-list">
            {(smokeStatus?.not_ready_for ?? []).map((item) => <li key={item}>{item.split("_").join(" ")}</li>)}
          </ul>
          <p className="small-note">Zone-aware traffic decisions are simulation-only and remain disconnected from physical traffic infrastructure.</p>
        </section>
      </div>
      <FunctionChecklist limit={10} />
    </div>
  );
}
