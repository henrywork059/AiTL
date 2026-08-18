import { useCallback, useEffect, useState } from "react";
import { deleteModel, fetchInferenceStatus, fetchModelRegistry, loadInferenceModel, setDefaultModel } from "../api";
import type { InferenceStatus, ModelRegistryStatus } from "../types";

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Model registry request failed.";
}

function formatSize(sizeBytes: number): string {
  if (sizeBytes < 1024) return `${sizeBytes} B`;
  if (sizeBytes < 1024 * 1024) return `${(sizeBytes / 1024).toFixed(1)} KB`;
  return `${(sizeBytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function ModelRegistryPage() {
  const [registry, setRegistry] = useState<ModelRegistryStatus | null>(null);
  const [inferenceStatus, setInferenceStatus] = useState<InferenceStatus | null>(null);
  const [busyModelId, setBusyModelId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [nextRegistry, nextInference] = await Promise.all([fetchModelRegistry(), fetchInferenceStatus()]);
    setRegistry(nextRegistry);
    setInferenceStatus(nextInference);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleLoad(modelId: string) {
    setBusyModelId(modelId);
    setError(null);
    try {
      setInferenceStatus(await loadInferenceModel(modelId));
      await refresh();
    } catch (nextError) {
      setError(errorMessage(nextError));
    } finally {
      setBusyModelId(null);
    }
  }

  async function handleDefault(modelId: string) {
    setBusyModelId(modelId);
    setError(null);
    try {
      setRegistry(await setDefaultModel(modelId));
      await refresh();
    } catch (nextError) {
      setError(errorMessage(nextError));
    } finally {
      setBusyModelId(null);
    }
  }

  async function handleDelete(modelId: string) {
    if (!window.confirm(`Permanently delete trained run ${modelId}? This removes its run directory under outputs/training and cannot be undone.`)) return;
    setBusyModelId(modelId);
    setError(null);
    try {
      setRegistry(await deleteModel(modelId));
      await refresh();
    } catch (nextError) {
      setError(errorMessage(nextError));
    } finally {
      setBusyModelId(null);
    }
  }

  return (
    <div className="page-stack">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Local model inventory</h2>
            <p className="placeholder-copy">Models are discovered from local training runs. Loading changes the current inference model; setting default controls which model PC Studio prefers after restart.</p>
          </div>
          <button className="primary" onClick={() => void refresh()}>Refresh</button>
        </div>
        <div className="camera-status-list inference-status-list">
          <div><span>Saved models</span><strong>{registry?.total ?? 0}</strong></div>
          <div><span>Loaded for inference</span><strong>{inferenceStatus?.active_model_id ?? "none"}</strong></div>
          <div><span>Default on startup</span><strong>{registry?.default_model_id ?? "none"}</strong></div>
          <div><span>Inference dependency</span><strong>{inferenceStatus?.backend_available ? "available" : "not installed"}</strong></div>
        </div>
        {error && <p className="error-message">{error}</p>}
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Training runs</h2>
            <p className="placeholder-copy">Choose one model at a time for live inference. Deleting a run removes its local files.</p>
          </div>
          <span className="status-pill muted">{registry?.total ?? 0} models</span>
        </div>
        <div className="model-list-grid">
          {(registry?.models ?? []).map((model) => (
            <article className="smoke-card" key={model.model_id}>
              <div className="panel-header compact-header">
                <strong>{model.model_id}</strong>
                <span className={`status-pill ${model.is_active ? "status-implemented" : model.is_default ? "status-info" : ""}`}>
                  {model.is_active ? "active" : model.is_default ? "default" : model.is_latest ? "latest" : "saved"}
                </span>
              </div>
              <p><code>{model.model_path}</code></p>
              <p>Updated {new Date(model.modified_at_ms).toLocaleString()}</p>
              <p>{formatSize(model.size_bytes)}</p>
              <div className="button-row wrap-row">
                <button className="primary" disabled={busyModelId === model.model_id || model.is_active} onClick={() => void handleLoad(model.model_id)}>Load model</button>
                <button disabled={busyModelId === model.model_id || model.is_default} onClick={() => void handleDefault(model.model_id)}>Set default</button>
                <button className="danger" disabled={busyModelId === model.model_id} onClick={() => void handleDelete(model.model_id)}>Delete run</button>
              </div>
            </article>
          ))}
          {(registry?.models.length ?? 0) === 0 && <p>No trained models were found under <code>outputs/training</code>.</p>}
        </div>
      </section>
    </div>
  );
}
