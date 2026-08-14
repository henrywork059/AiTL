import { FunctionChecklist } from "../components/FunctionChecklist";
import { PlaceholderPanel } from "../components/PlaceholderPanel";
import type { SmokeStatus, TrafficState } from "../types";

type Props = {
  traffic: TrafficState | null;
  smokeStatus: SmokeStatus | null;
};

export function TrafficLogicPage({ traffic, smokeStatus }: Props) {
  return (
    <div className="page-stack">
      <div className="two-column-grid">
        <section className="panel">
          <div className="panel-header">
            <h2>Current mock decision</h2>
            <span className="status-pill">simulation only</span>
          </div>
          {traffic ? (
            <div className="metric-grid">
              <div className="metric-card"><span>Phase</span><strong>{traffic.phase.replaceAll("_", " ")}</strong></div>
              <div className="metric-card"><span>Decision</span><strong>{traffic.decision.replaceAll("_", " ")}</strong></div>
              <div className="metric-card"><span>Pedestrians waiting</span><strong>{traffic.pedestrians_waiting}</strong></div>
              <div className="metric-card"><span>Vehicles waiting</span><strong>{traffic.vehicles_waiting}</strong></div>
            </div>
          ) : <p>Loading traffic state...</p>}
          {traffic && <p className="reason-text">{traffic.decision_reason}</p>}
        </section>

        <PlaceholderPanel
          title="Rule engine plan"
          description="This page will later expose the rule-based decision engine. In 0_1_2 it only confirms the intended layout and mock state display."
          status="mock"
          bullets={[
            "extend pedestrian green when enough people are waiting",
            "keep vehicle red while pedestrians are still crossing",
            "extend vehicle green when vehicle queue is high and crossing is empty",
            "record every decision with reason and error code if failed",
          ]}
        />
      </div>

      <PlaceholderPanel
        title="Smoke-test endpoints used"
        description="These endpoints are expected to respond during local mock testing."
        status="test checklist"
        bullets={smokeStatus?.endpoints ?? ["/health", "/api/smoke/status", "/api/traffic/state"]}
      />
      <FunctionChecklist area="Traffic logic" />
    </div>
  );
}
