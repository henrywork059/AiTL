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
    if (!window.confirm(`Delete trained model ${modelId}?`)) return;
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
            <h2>Model registry</h2>
            <p className="placeholder-copy">Review local trained models, choose which one to run, set a default auto-load model, or delete outdated runs.</p>
          </div>
          <button onClick={() => void refresh()}>Refresh</button>
        </div>
        <div className="camera-status-list inference-status-list">
          <div><span>Total models</span><strong>{registry?.total ?? 0}</strong></div>
          <div><span>Active model</span><strong>{inferenceStatus?.active_model_id ?? "none"}</strong></div>
          <div><span>Default model</span><strong>{registry?.default_model_id ?? "none"}</strong></div>
          <div><span>Backend</span><strong>{inferenceStatus?.backend_available ? "ready" : "missing dependency"}</strong></div>
        </div>
        {error && <p className="error-message">{error}</p>}
      </section>

      <section className="panel">
        <div className="model-list-grid">
          {(registry?.models ?? []).map((model) => (
            <article className="smoke-card" key={model.model_id}>
              <div className="panel-header compact-header">
                <strong>{model.model_id}</strong>
                <span className={`status-pill ${model.is_active ? "status-implemented" : "status-planned"}`}>
                  {model.is_active ? "active" : model.is_default ? "default" : model.is_latest ? "latest" : "saved"}
                </span>
              </div>
              <p><code>{model.model_path}</code></p>
              <p>Updated: {new Date(model.modified_at_ms).toLocaleString()}</p>
              <p>Size: {formatSize(model.size_bytes)}</p>
              <div className="button-row wrap-row">
                <button disabled={busyModelId === model.model_id} onClick={() => void handleLoad(model.model_id)}>Load</button>
                <button disabled={busyModelId === model.model_id || model.is_default} onClick={() => void handleDefault(model.model_id)}>Set default</button>
                <button disabled={busyModelId === model.model_id} onClick={() => void handleDelete(model.model_id)}>Delete</button>
              </div>
            </article>
          ))}
          {(registry?.models.length ?? 0) === 0 && <p>No trained models were found under <code>outputs/training</code>.</p>}
        </div>
      </section>
    </div>
  );
}
