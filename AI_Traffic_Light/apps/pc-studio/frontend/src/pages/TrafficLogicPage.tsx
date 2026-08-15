import { useEffect, useState } from "react";
import { fetchTrafficState } from "../api";
import { FunctionChecklist } from "../components/FunctionChecklist";
import type { TrafficState } from "../types";

function phaseClass(phase: string | undefined): string {
  if (phase === "pedestrian_green" || phase === "vehicle_green") return "status-pill status-implemented";
  if (phase === "vehicle_yellow" || phase === "pedestrian_flashing") return "status-pill status-planned";
  return "status-pill";
}

export function TrafficLogicPage() {
  const [traffic, setTraffic] = useState<TrafficState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function refresh() {
      try {
        const next = await fetchTrafficState();
        if (!cancelled) {
          setTraffic(next);
          setError(null);
        }
      } catch (nextError) {
        if (!cancelled) setError(nextError instanceof Error ? nextError.message : "Traffic state could not be evaluated.");
      }
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), 1000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const zoneCounts = Object.entries(traffic?.zone_counts ?? {});
  const regionCounts = Object.entries(traffic?.region_counts ?? {});

  return (
    <div className="page-stack">
      <div className="two-column-grid">
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Live zone decision</h2>
              <p className="placeholder-copy">Uses the current trained-model detection frame and your persisted zone configuration.</p>
            </div>
            <span className={phaseClass(traffic?.phase)}>{traffic?.phase?.split("_").join(" ") ?? "checking"}</span>
          </div>
          {traffic ? (
            <div className="metric-grid">
              <div className="metric-card"><span>Total pedestrians</span><strong>{traffic.pedestrians_total ?? 0}</strong></div>
              <div className="metric-card"><span>Total vehicles</span><strong>{traffic.vehicles_total ?? 0}</strong></div>
              <div className="metric-card"><span>Pedestrians waiting</span><strong>{traffic.pedestrians_waiting}</strong></div>
              <div className="metric-card"><span>Pedestrians crossing</span><strong>{traffic.pedestrians_crossing}</strong></div>
              <div className="metric-card"><span>Vehicles queued</span><strong>{traffic.vehicles_waiting}</strong></div>
              <div className="metric-card"><span>{traffic.recommended_phase ? "Phase remaining" : "Suggested extension"}</span><strong>{traffic.extension_seconds}s</strong></div>
            </div>
          ) : <p>Evaluating current traffic state...</p>}
          {traffic && (
            <>
              <div className="camera-status-list training-status-list">
                <div><span>Decision</span><strong>{traffic.decision.split("_").join(" ")}</strong></div>
                {traffic.recommended_phase && <div><span>Detection recommendation</span><strong>{traffic.recommended_phase.split("_").join(" ")}</strong></div>}
                <div><span>Data source</span><strong>{traffic.data_source ?? "unknown"}</strong></div>
                <div><span>Frame</span><strong>{traffic.evaluated_frame_number ?? "none"}</strong></div>
              </div>
              <p className="reason-text">{traffic.decision_reason}</p>
            </>
          )}
          {error && <p className="error-message">{error}</p>}
        </section>

        <section className="panel">
          <div className="panel-header"><h2>Decision-zone counts</h2><span className="status-pill">live centres</span></div>
          {zoneCounts.length === 0 ? (
            <p className="placeholder-copy">No zone-count result is available until the backend has a camera frame, loaded model, and active zones.</p>
          ) : (
            <div className="camera-status-list training-status-list">
              {zoneCounts.map(([zoneId, count]) => <div key={zoneId}><span>{zoneId}</span><strong>{count}</strong></div>)}
            </div>
          )}
          <p className="small-note">Decision-zone counts preserve the detection-based recommendation logic. In simulation mode the active phase follows the deterministic simulator signal; the detection recommendation is shown separately. Counting-region totals remain analytics-only.</p>
        </section>
      </div>

      <section className="panel">
        <div className="panel-header"><h2>Per-region pedestrian / vehicle counts</h2><span className="status-pill">all non-ignore zones</span></div>
        {regionCounts.length === 0 ? (
          <p className="placeholder-copy">No region occupancy result is available yet.</p>
        ) : (
          <div className="function-list">
            {regionCounts.map(([zoneId, counts]) => (
              <article className="function-item" key={zoneId}>
                <div><strong>{zoneId}</strong><p>{counts.pedestrians} pedestrian(s), {counts.vehicles} vehicle(s), {counts.total} total detected centres.</p></div>
                <span className="status-pill">{counts.total}</span>
              </article>
            ))}
          </div>
        )}
        <p className="small-note">Detection box centres are scaled into the 1280 × 720 reference frame. Ignore zones take priority. Overlapping regions are counted independently.</p>
      </section>

      <section className="panel">
        <div className="panel-header"><h2>Prototype decision rules</h2><span className="status-pill muted">simulation only</span></div>
        <div className="function-list">
          <article className="function-item"><div><strong>Crossing occupied</strong><p>Keep the simulated pedestrian phase active while detected people remain in a crossing zone.</p></div><span className="status-pill">active</span></article>
          <article className="function-item"><div><strong>Pedestrian waiting</strong><p>When the crossing is clear and a person is in a waiting zone, prepare the simulated pedestrian phase.</p></div><span className="status-pill">active</span></article>
          <article className="function-item"><div><strong>Vehicle queue</strong><p>When pedestrian zones are clear and four or more vehicles are queued, recommend a bounded vehicle-green extension.</p></div><span className="status-pill">active</span></article>
          <article className="function-item"><div><strong>Counting region</strong><p>Count vehicle and pedestrian occupancy for analytics without influencing any simulated signal decision.</p></div><span className="status-pill">analytics only</span></article>
        </div>
        <p className="small-note">These are human-supervised prototype recommendations. They are not connected to real traffic signals or public-road infrastructure.</p>
      </section>
      <FunctionChecklist area="Traffic logic" />
    </div>
  );
}
