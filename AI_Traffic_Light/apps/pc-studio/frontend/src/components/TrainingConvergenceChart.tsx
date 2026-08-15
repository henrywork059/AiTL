import type { EarlyStoppingState, TrainingMetricPoint } from "../types";
import "./trainingConvergence.css";

type Props = {
  history: TrainingMetricPoint[];
  earlyStopping: EarlyStoppingState | null;
  requestedEpochs: number;
};

type SeriesKey = "fitness" | "map50_95";

function pathFor(history: TrainingMetricPoint[], key: SeriesKey, maxEpoch: number): string {
  const points = history
    .map((item) => ({ epoch: item.epoch, value: item[key] }))
    .filter((item): item is { epoch: number; value: number } => typeof item.value === "number");
  return points.map((point, index) => {
    const x = 54 + (point.epoch / Math.max(1, maxEpoch)) * 596;
    const y = 20 + (1 - Math.max(0, Math.min(1, point.value))) * 220;
    return `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");
}

function formatMetric(value: number | null | undefined): string {
  return typeof value === "number" ? value.toFixed(4) : "n/a";
}

export function TrainingConvergenceChart({ history, earlyStopping, requestedEpochs }: Props) {
  const maxEpoch = Math.max(requestedEpochs, history.length > 0 ? history[history.length - 1].epoch : 1);
  const latest = history.length > 0 ? history[history.length - 1] : undefined;
  const noImprovement = earlyStopping?.epochs_without_improvement ?? 0;
  const patience = earlyStopping?.patience ?? 0;
  const stateLabel = earlyStopping?.stopped_early
    ? "stopped early"
    : earlyStopping?.converged
      ? "converged"
      : noImprovement > 0
        ? "monitoring plateau"
        : "improving / collecting";

  return (
    <section className="panel convergence-panel">
      <div className="panel-header">
        <div>
          <h2>Training convergence</h2>
          <p className="placeholder-copy">Validation fitness and mAP50-95 by epoch. Early stopping uses the configured patience window.</p>
        </div>
        <span className={`status-pill ${earlyStopping?.converged ? "status-planned" : "status-implemented"}`}>{stateLabel}</span>
      </div>

      {history.length === 0 ? (
        <div className="convergence-empty">Metric points appear after the first train + validation epoch.</div>
      ) : (
        <div className="convergence-chart-wrap">
          <svg className="convergence-chart" viewBox="0 0 680 285" role="img" aria-label="Training fitness and mAP50-95 convergence by epoch">
            {[0, 0.25, 0.5, 0.75, 1].map((tick) => {
              const y = 20 + (1 - tick) * 220;
              return (
                <g key={tick}>
                  <line x1="54" y1={y} x2="650" y2={y} className="convergence-grid-line" />
                  <text x="46" y={y + 4} textAnchor="end" className="convergence-axis-label">{tick.toFixed(2)}</text>
                </g>
              );
            })}
            <line x1="54" y1="240" x2="650" y2="240" className="convergence-axis" />
            <line x1="54" y1="20" x2="54" y2="240" className="convergence-axis" />
            <path d={pathFor(history, "fitness", maxEpoch)} className="convergence-line convergence-fitness" />
            <path d={pathFor(history, "map50_95", maxEpoch)} className="convergence-line convergence-map" />
            {history.map((point) => {
              if (typeof point.fitness !== "number") return null;
              const x = 54 + (point.epoch / maxEpoch) * 596;
              const y = 20 + (1 - Math.max(0, Math.min(1, point.fitness))) * 220;
              return <circle key={`fit-${point.epoch}`} cx={x} cy={y} r="3" className="convergence-dot convergence-fitness-dot" />;
            })}
            <text x="352" y="272" textAnchor="middle" className="convergence-axis-label">Epoch</text>
          </svg>
          <div className="convergence-legend">
            <span><i className="legend-line legend-fitness" /> Fitness</span>
            <span><i className="legend-line legend-map" /> mAP50-95</span>
          </div>
        </div>
      )}

      <div className="metric-grid convergence-metrics">
        <div className="metric-card"><span>Latest fitness</span><strong>{formatMetric(latest?.fitness)}</strong></div>
        <div className="metric-card"><span>Best fitness</span><strong>{formatMetric(earlyStopping?.best_fitness)}</strong></div>
        <div className="metric-card"><span>Best epoch</span><strong>{earlyStopping?.best_epoch ?? "n/a"}</strong></div>
        <div className="metric-card"><span>No improvement</span><strong>{noImprovement} / {patience || "-"}</strong></div>
      </div>
      <p className="small-note">
        The plot is diagnostic. Automatic stopping is performed by the local Ultralytics trainer when validation fitness fails to improve for the configured patience window.
      </p>
    </section>
  );
}
