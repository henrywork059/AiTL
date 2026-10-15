import { useCallback, useEffect, useState } from "react";
import { deleteModel, fetchInferenceStatus, fetchModelRegistry, loadInferenceModel, saveRuntimeSettings, setDefaultModel, unloadInferenceModel } from "../api";
import type { InferenceStatus, ModelRegistryStatus, RuntimeSettings } from "../types";

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Model registry request failed.";
}

function formatSize(sizeBytes: number): string {
  if (sizeBytes < 1024) return `${sizeBytes} B`;
  if (sizeBytes < 1024 * 1024) return `${(sizeBytes / 1024).toFixed(1)} KB`;
  return `${(sizeBytes / (1024 * 1024)).toFixed(2)} MB`;
}

type Props = {
  runtimeSettings: RuntimeSettings;
  onSettingsChange: (value: RuntimeSettings) => void;
};

export function ModelRegistryPage({ runtimeSettings, onSettingsChange }: Props) {
  const [registry, setRegistry] = useState<ModelRegistryStatus | null>(null);
  const [inferenceStatus, setInferenceStatus] = useState<InferenceStatus | null>(null);
  const [busyModelId, setBusyModelId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [defaultConfidence, setDefaultConfidence] = useState(runtimeSettings.default_confidence);
  const [savingConfidence, setSavingConfidence] = useState(false);

  useEffect(() => setDefaultConfidence(runtimeSettings.default_confidence), [runtimeSettings.default_confidence]);

  const refresh = useCallback(async () => {
    const [nextRegistry, nextInference] = await Promise.all([fetchModelRegistry(), fetchInferenceStatus()]);
    setRegistry(nextRegistry);
    setInferenceStatus(nextInference);
  }, []);

  useEffect(() => {
    void refresh().catch((reason) => setError(errorMessage(reason)));
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

  async function handleSaveConfidence() {
    if (!Number.isFinite(defaultConfidence) || defaultConfidence < 0.01 || defaultConfidence > 1) {
      setError("Detection confidence must be between 0.01 and 1.");
      return;
    }
    setSavingConfidence(true);
    setError(null);
    setNotice(null);
    try {
      const saved = await saveRuntimeSettings({ ...runtimeSettings, default_confidence: defaultConfidence });
      onSettingsChange(saved);
      setNotice("Default AI confidence saved.");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setSavingConfidence(false);
    }
  }

  async function handleUnload() {
    setBusyModelId("__unload__");
    setError(null);
    try {
      setInferenceStatus(await unloadInferenceModel());
      await refresh();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusyModelId(null);
    }
  }

  return (
    <div className="page-stack">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>AI Models</h2>
            <p className="placeholder-copy">Models are discovered from local training runs. Loading changes the current inference model; setting default controls which model PC Studio prefers after restart.</p>
          </div>
          <button className="primary" onClick={() => void refresh().catch((reason) => setError(errorMessage(reason)))}>Refresh</button>
        </div>
        <div className="camera-status-list inference-status-list">
          <div><span>Saved models</span><strong>{registry?.total ?? 0}</strong></div>
          <div><span>Loaded for inference</span><strong>{inferenceStatus?.active_model_id ?? "none"}</strong></div>
          <div><span>Default on startup</span><strong>{registry?.default_model_id ?? "none"}</strong></div>
          <div><span>Inference dependency</span><strong>{inferenceStatus?.backend_available ? "available" : "not installed"}</strong></div>
        </div>
        <div className="button-row">
          <button type="button" disabled={!inferenceStatus?.model_loaded || busyModelId !== null} onClick={() => void handleUnload()}>
            {busyModelId === "__unload__" ? "Unloading..." : "Unload active model"}
          </button>
        </div>
        {notice && <p className="success-message" role="status">{notice}</p>}
        {error && <p className="error-message" role="alert">{error}</p>}
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>AI detection defaults</h2>
            <p className="placeholder-copy">Saved in the existing backend runtime settings. Affects the default confidence used by Camera AI Preview.</p>
          </div>
        </div>
        <div className="form-grid">
          <label>Default detection confidence (0.01–1.00)
            <input type="number" min={0.01} max={1} step={0.01}
              value={defaultConfidence}
              onChange={(event) => setDefaultConfidence(Number(event.target.value))} />
          </label>
        </div>
        <div className="button-row">
          <button className="primary" type="button"
            disabled={savingConfidence || defaultConfidence === runtimeSettings.default_confidence
              || !Number.isFinite(defaultConfidence) || defaultConfidence < 0.01 || defaultConfidence > 1}
            onClick={() => void handleSaveConfidence()}>
            {savingConfidence ? "Saving..." : "Save AI settings"}
          </button>
        </div>
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
