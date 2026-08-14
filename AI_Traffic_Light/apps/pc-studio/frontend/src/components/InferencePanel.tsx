import type { InferenceStatus } from "../types";

type Props = {
  status: InferenceStatus | null;
  selectedModelId: string | null;
  onSelectedModelChange: (value: string) => void;
  confidenceThreshold: number;
  onConfidenceChange: (value: number) => void;
  onLoadSelected: () => void;
  onLoadLatest: () => void;
  onSetDefault: () => void;
  onDeleteSelected: () => void;
  onUnload: () => void;
  loadingModel: boolean;
  deletingModel: boolean;
  error: string | null;
};

function formatSize(sizeBytes: number | undefined): string {
  if (!sizeBytes || sizeBytes < 1024) return `${sizeBytes ?? 0} B`;
  if (sizeBytes < 1024 * 1024) return `${(sizeBytes / 1024).toFixed(1)} KB`;
  return `${(sizeBytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function InferencePanel({
  status,
  selectedModelId,
  onSelectedModelChange,
  confidenceThreshold,
  onConfidenceChange,
  onLoadSelected,
  onLoadLatest,
  onSetDefault,
  onDeleteSelected,
  onUnload,
  loadingModel,
  deletingModel,
  error,
}: Props) {
  const modelLoaded = status?.model_loaded ?? false;
  const available = status?.available_model_count ?? 0;
  const models = status?.models ?? [];
  const selected = models.find((item) => item.model_id === selectedModelId) ?? models[0] ?? null;

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
        <div><span>Default run</span><strong>{status?.default_model_id ?? "none"}</strong></div>
        <div><span>Latency</span><strong>{status?.last_latency_ms != null ? `${status.last_latency_ms.toFixed(1)} ms` : "n/a"}</strong></div>
      </div>

      <label className="control-label inference-threshold">
        Choose model
        <select
          value={selectedModelId ?? selected?.model_id ?? ""}
          onChange={(event) => onSelectedModelChange(event.target.value)}
          disabled={available === 0}
        >
          {models.map((model) => (
            <option key={model.model_id} value={model.model_id}>
              {model.model_id}
              {model.is_default ? " [default]" : ""}
              {model.is_latest ? " [latest]" : ""}
            </option>
          ))}
        </select>
      </label>

      {selected && (
        <div className="selected-model-details small-note">
          <div><strong>Path:</strong> <code>{selected.model_path}</code></div>
          <div><strong>Run folder:</strong> <code>{selected.run_path}</code></div>
          <div><strong>Size:</strong> {formatSize(selected.size_bytes)}</div>
          <div><strong>Updated:</strong> {new Date(selected.modified_at_ms).toLocaleString()}</div>
        </div>
      )}

      <div className="button-row inference-button-row wrap-row">
        <button onClick={onLoadSelected} disabled={loadingModel || available === 0 || !status?.backend_available || !selected}>
          {loadingModel ? "Loading..." : "Load selected model"}
        </button>
        <button onClick={onLoadLatest} disabled={loadingModel || available === 0 || !status?.backend_available}>
          Load latest
        </button>
      </div>
      <div className="button-row inference-button-row wrap-row">
        <button onClick={onSetDefault} disabled={loadingModel || available === 0 || !selected || status?.default_model_id === selected?.model_id}>
          Set as default
        </button>
        <button onClick={onDeleteSelected} disabled={deletingModel || available === 0 || !selected}>
          {deletingModel ? "Deleting..." : "Delete selected"}
        </button>
        <button onClick={onUnload} disabled={loadingModel || !modelLoaded}>Unload</button>
      </div>

      <label className="control-label inference-threshold">
        Detection confidence: {(confidenceThreshold * 100).toFixed(0)}%
        <input
          type="range"
          min={status?.confidence_floor ?? 0.01}
          max="1"
          step="0.01"
          value={Math.max(confidenceThreshold, status?.confidence_floor ?? 0.01)}
          onChange={(event) => onConfidenceChange(Number(event.target.value))}
        />
      </label>

      {!status?.backend_available && (
        <code className="endpoint-code">pip install -r requirements-training.txt</code>
      )}
      <p className="small-note">
        Live inference can use a selected model, the newest model, or the configured default model. The backend now accepts lower diagnostic confidence down to 1%.
      </p>
      {error && <p className="error-message">{error}</p>}
      {status?.error && <p className="error-message">Backend: {status.error}</p>}
    </section>
  );
}
