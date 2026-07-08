import type { TrafficState } from "../types";

type Props = {
  traffic: TrafficState;
};

export function StatusPanel({ traffic }: Props) {
  return (
    <section className="panel compact-panel">
      <div className="panel-header">
        <h2>Traffic state</h2>
      </div>
      <div className="metric-grid">
        <div className="metric-card">
          <span>Pedestrians waiting</span>
          <strong>{traffic.pedestrians_waiting}</strong>
        </div>
        <div className="metric-card">
          <span>Pedestrians crossing</span>
          <strong>{traffic.pedestrians_crossing}</strong>
        </div>
        <div className="metric-card">
          <span>Vehicles waiting</span>
          <strong>{traffic.vehicles_waiting}</strong>
        </div>
        <div className="metric-card">
          <span>Extension</span>
          <strong>{traffic.extension_seconds}s</strong>
        </div>
      </div>
      <p className="reason-text">{traffic.decision_reason}</p>
    </section>
  );
}
