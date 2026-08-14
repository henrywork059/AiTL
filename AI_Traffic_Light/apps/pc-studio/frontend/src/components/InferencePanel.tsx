import type { InferenceStatus } from "../types";

type Props = {
  status: InferenceStatus | null;
  confidenceThreshold: number;
  onConfidenceChange: (value: number) => void;
  onLoadLatest: () => void;
  onUnload: () => void;
  loadingModel: boolean;
  error: string | null;
};

export function InferencePanel({
  status,
  confidenceThreshold,
  onConfidenceChange,
  onLoadLatest,
  onUnload,
  loadingModel,
  error,
}: Props) {
  const modelLoaded = status?.model_loaded ?? false;
  const available = status?.available_model_count ?? 0;

  return (
    <section className="panel compact-panel inference-panel">
      <div className="panel-header">
        <h2>Trained model</h2>
        <span className={`status-pill ${modelLoaded ? "status-implemented" : "status-planned"}`}>
          {modelLoaded ? "loaded" : "not loaded"}
        </span>
      </div>

      <div className="camera-status-list inference-status-list">
        <div><span>Available best.pt</span><strong>{available}</strong></div>
        <div><span>Active run</span><strong>{status?.active_model_id ?? "none"}</strong></div>
        <div><span>Latest model</span><strong>{status?.latest_model_path ?? "not found"}</strong></div>
        <div><span>Latency</span><strong>{status?.last_latency_ms != null ? `${status.last_latency_ms.toFixed(1)} ms` : "n/a"}</strong></div>
      </div>

      <div className="button-row inference-button-row">
        <button onClick={onLoadLatest} disabled={loadingModel || available === 0 || !status?.backend_available}>
          {loadingModel ? "Loading..." : modelLoaded ? "Reload latest model" : "Load latest trained model"}
        </button>
        <button onClick={onUnload} disabled={loadingModel || !modelLoaded}>Unload</button>
      </div>

      <label className="control-label inference-threshold">
        Display confidence: {(confidenceThreshold * 100).toFixed(0)}%
        <input
          type="range"
          min={status?.confidence_floor ?? 0.1}
          max="1"
          step="0.01"
          value={Math.max(confidenceThreshold, status?.confidence_floor ?? 0.1)}
          onChange={(event) => onConfidenceChange(Number(event.target.value))}
        />
      </label>

      {!status?.backend_available && (
        <code className="endpoint-code">pip install -r requirements-training.txt</code>
      )}
      <p className="small-note">
        Live inference uses the newest local <code>outputs/training/*/weights/best.pt</code>. The slider filters boxes already returned by the backend.
      </p>
      {error && <p className="error-message">{error}</p>}
      {status?.error && <p className="error-message">Backend: {status.error}</p>}
    </section>
  );
}
