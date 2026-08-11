import { FunctionChecklist } from "../components/FunctionChecklist";
import { MetricStrip } from "../components/MetricStrip";
import { PlaceholderPanel } from "../components/PlaceholderPanel";
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

  return (
    <div className="page-stack">
      <MetricStrip
        metrics={[
          { label: "Project stage", value: "0_1_0", note: "test-ready mock" },
          { label: "Backend", value: apiState.status, note: health?.version ?? "checking" },
          { label: "Smoke checks", value: `${passCount} pass`, note: `${warnCount} warnings` },
          { label: "Real AI", value: "off", note: "safe mock mode" },
        ]}
      />

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Local smoke-test status</h2>
            <p className="placeholder-copy">{apiState.message}</p>
          </div>
          <button onClick={onRefresh} disabled={refreshing}>{refreshing ? "Refreshing..." : "Refresh mock APIs"}</button>
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
        <PlaceholderPanel
          title="What 0_1_0 can test"
          description="This version is intended for local app startup, layout review, frontend-backend connection checks, and mock API testing."
          status="test ready"
          bullets={smokeStatus?.ready_for ?? [
            "frontend layout test",
            "backend startup test",
            "mock API test",
            "frontend-backend connection test",
          ]}
        />
        <PlaceholderPanel
          title="What is still disabled"
          description="The project remains safe-mode only. These functions should not be expected to work in 0_1_0."
          status="not implemented"
          bullets={smokeStatus?.not_ready_for ?? [
            "real camera capture",
            "YOLO inference",
            "training",
            "physical traffic-light control",
          ]}
        />
      </div>
      <FunctionChecklist limit={8} />
    </div>
  );
}
