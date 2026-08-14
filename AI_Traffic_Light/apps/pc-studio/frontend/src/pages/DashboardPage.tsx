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
          { label: "Project stage", value: "0_1_5", note: "model management candidate" },
          { label: "Backend", value: apiState.status, note: health?.version ?? "checking" },
          { label: "Smoke checks", value: `${passCount} pass`, note: `${warnCount} warnings` },
          { label: "Real AI", value: "live detection", note: "latest trained best.pt" },
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
          title="What 0_1_5 can test"
          description="This version loads the newest locally trained YOLO best.pt and overlays its detections on receiver or simulation frames."
          status="test ready"
          bullets={smokeStatus?.ready_for ?? [
            "persistent capture and manual labels",
            "managed YOLO dataset build",
            "optional local training",
            "trained-model live camera inference",
          ]}
        />
        <PlaceholderPanel
          title="What is still disabled"
          description="The project remains prototype-only. These functions should not be expected to work in 0_1_5."
          status="not implemented"
          bullets={smokeStatus?.not_ready_for ?? [
            "automatic labeling",
            "zone counts from live detections",
            "model export",
            "physical traffic-light control",
          ]}
        />
      </div>
      <FunctionChecklist limit={8} />
    </div>
  );
}
