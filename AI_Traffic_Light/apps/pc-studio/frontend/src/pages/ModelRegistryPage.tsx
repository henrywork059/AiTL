import { useCallback, useEffect, useState } from "react";
import { deleteModel, fetchInferenceStatusStrict, fetchModelRegistryStrict, loadInferenceModel, saveRuntimeSettings, uploadInferenceModel, setDefaultModel, unloadInferenceModel } from "../api";
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
  const [inferenceInterval, setInferenceInterval] = useState(runtimeSettings.inference_interval_ms);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadId, setUploadId] = useState("");
  const [uploading, setUploading] = useState(false);
  const [modelFilter, setModelFilter] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const visibleModels = (registry?.models ?? []).filter(model => model.model_id.toLowerCase().includes(modelFilter.trim().toLowerCase())).sort((a,b) => Number(b.is_active)-Number(a.is_active) || Number(b.is_default)-Number(a.is_default) || a.model_id.localeCompare(b.model_id));

  useEffect(() => setDefaultConfidence(runtimeSettings.default_confidence), [runtimeSettings.default_confidence]);
  useEffect(() => setInferenceInterval(runtimeSettings.inference_interval_ms), [runtimeSettings.inference_interval_ms]);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const [nextRegistry, nextInference] = await Promise.all([fetchModelRegistryStrict(), fetchInferenceStatusStrict()]);
      setRegistry(nextRegistry);
      setInferenceStatus(nextInference);
      setError(null);
    } catch (reason) {
      setRegistry(null);
      setInferenceStatus(null);
      throw reason;
    } finally { setRefreshing(false); }
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

  async function handleUpload() {
    if (!uploadFile || !uploadFile.name.toLowerCase().endsWith(".pt") || !/^[A-Za-z0-9_-]{1,64}$/.test(uploadId)) {
      setError("Select a .pt file and enter a model ID containing letters, numbers, - or _.");
      return;
    }
    setUploading(true);
    setError(null);
    setNotice(null);
    try {
      await uploadInferenceModel(uploadId, uploadFile);
      await refresh();
      setUploadFile(null);
      setUploadId("");
      setNotice("Model uploaded. Select Load model to activate it.");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setUploading(false);
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
      const saved = await saveRuntimeSettings({
        ...runtimeSettings, default_confidence: defaultConfidence,
        inference_interval_ms: inferenceInterval,
      });
      onSettingsChange(saved);
      setNotice("Global AI settings saved for all cameras.");
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
            <h2>Inference status</h2>
            <p className="placeholder-copy">Manage saved AI models and choose one running model shared by all registered cameras.</p>
          </div>
          <button className="primary" disabled={refreshing || busyModelId !== null || uploading} onClick={() => void refresh().catch((reason) => setError(errorMessage(reason)))}>{refreshing ? "Refreshing..." : "Refresh"}</button>
        </div>
        <div className="camera-status-list inference-status-list">
          <div><span>Saved models</span><strong>{registry?.total ?? "—"}</strong></div>
          <div><span>Loaded for inference</span><strong>{inferenceStatus ? inferenceStatus.active_model_id ?? "none" : "unavailable"}</strong></div>
          <div><span>Default on startup</span><strong>{registry ? registry.default_model_id ?? "none" : "unavailable"}</strong></div>
          <div><span>Inference dependency</span><strong>{!inferenceStatus ? "unavailable" : inferenceStatus.backend_available ? "available" : "not installed"}</strong></div>
        </div>
        <div className="button-row">
          <button type="button" disabled={refreshing || uploading || !inferenceStatus?.model_loaded || busyModelId !== null} onClick={() => void handleUnload()}>
            {busyModelId === "__unload__" ? "Unloading..." : "Unload active model"}
          </button>
        </div>
        {notice && <p className="success-message" role="status">{notice}</p>}
        {error && <p className="error-message" role="alert">{error}</p>}
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Installed AI models</h2>
            <p className="placeholder-copy">Activate one global model. Deleting a run permanently removes its local files.</p>
          </div>
          <span className="status-pill muted">{registry ? `${registry.total} models` : "Unavailable"}</span>
        </div>
        <label className="workspace-model-filter">Find model <input type="search" value={modelFilter} onChange={event => setModelFilter(event.target.value)} placeholder="Model ID" /></label>
        {registry && registry.models.length > 0 && !visibleModels.length && <p role="status">No matching models.</p>}
        <div className="model-list-grid">
          {visibleModels.map((model) => (
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
                <button className="primary" disabled={refreshing || uploading || busyModelId !== null || model.is_active} onClick={() => void handleLoad(model.model_id)}>Load model</button>
                <button disabled={refreshing || uploading || busyModelId !== null || model.is_default} onClick={() => void handleDefault(model.model_id)}>Set default</button>
                <button className="danger" disabled={refreshing || uploading || busyModelId !== null || model.is_active} onClick={() => void handleDelete(model.model_id)}>Delete run</button>
              </div>
            </article>
          ))}
          {!registry && <p>Model registry unavailable or loading.</p>}
          {registry && registry.models.length === 0 && <p>No trained models were found under <code>outputs/training</code>.</p>}
        </div>
      </section>

      <div className="workspace-split">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Upload AI model</h2>
            <p className="placeholder-copy">Import an Ultralytics-compatible .pt model (maximum 200 MiB). Existing runs cannot be overwritten.</p>
          </div>
        </div>
        <div className="form-grid">
          <label>New model ID
            <input value={uploadId} maxLength={64} placeholder="custom_model_1" onChange={(event) => setUploadId(event.target.value)} />
          </label>
          <label>Weights file (.pt)
            <input type="file" accept=".pt" onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)} />
          </label>
        </div>
        <div className="button-row">
          <button className="primary" type="button" disabled={refreshing || uploading || busyModelId !== null || !uploadFile}
            onClick={() => void handleUpload()}>{uploading ? "Uploading..." : "Upload model"}</button>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Global AI settings</h2>
            <p className="placeholder-copy">Both settings apply to inference for every camera, including cameras not currently previewed.</p>
          </div>
        </div>
        <div className="form-grid">
          <label>Detection confidence — {Math.round(defaultConfidence * 100)}%
            <input type="range" min={0.01} max={1} step={0.01}
              value={defaultConfidence}
              onChange={(event) => setDefaultConfidence(Number(event.target.value))} />
          </label>
          <label>Model inference interval — {inferenceInterval} ms
            <input type="range" min={100} max={2000} step={50}
              value={inferenceInterval}
              onChange={(event) => setInferenceInterval(Number(event.target.value))} />
          </label>
        </div>
        <div className="button-row">
          <button className="primary" type="button"
            disabled={savingConfidence || (defaultConfidence === runtimeSettings.default_confidence && inferenceInterval === runtimeSettings.inference_interval_ms)
              || !Number.isFinite(defaultConfidence) || defaultConfidence < 0.01 || defaultConfidence > 1}
            onClick={() => void handleSaveConfidence()}>
            {savingConfidence ? "Saving..." : "Save AI settings"}
          </button>
        </div>
      </section>
      </div>
    </div>
  );
}
