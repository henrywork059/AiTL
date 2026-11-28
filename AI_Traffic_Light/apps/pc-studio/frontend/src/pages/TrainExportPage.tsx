import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { fetchRuntimeSettings, fetchTrainingDatasetStatusStrict, fetchTrainingStatusStrict, startTraining } from "../api";
import { FunctionChecklist } from "../components/FunctionChecklist";
import { TrainingConvergenceChart } from "../components/TrainingConvergenceChart";
import { useSerialPolling } from "../lib/useSerialPolling";
import { createPollingScope, type PollingContext } from "../lib/pollingScope";
import type { TrainingConfig, TrainingDatasetStatus, TrainingStatus } from "../types";

const DEFAULT_CONFIG: TrainingConfig = {
  dataset_yaml: "yolo/data.yaml",
  base_model: "yolo26n.pt",
  epochs: 10,
  image_size: 640,
  batch: 8,
  device: "cpu",
  patience: 5,
};

export function TrainExportPage({ onOpenModels, onOpenReview }: { onOpenModels?: () => void; onOpenReview?: () => void } = {}) {
  const [status, setStatus] = useState<TrainingStatus | null>(null);
  const [managedDataset, setManagedDataset] = useState<TrainingDatasetStatus | null>(null);
  const [config, setConfig] = useState<TrainingConfig>(DEFAULT_CONFIG);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const startRef = useRef(false);
  const scopeRef = useRef(createPollingScope());
  useLayoutEffect(() => {
    const scope = createPollingScope();
    scopeRef.current = scope;
    return () => scope.retire();
  }, []);

  async function refreshStatus({ signal, isCurrent }: PollingContext) {
    const [nextStatus, nextDataset] = await Promise.allSettled([
      fetchTrainingStatusStrict(signal),
      fetchTrainingDatasetStatusStrict(signal),
    ]);
    if (!isCurrent()) return;
    setStatus(nextStatus.status === "fulfilled" ? nextStatus.value : null);
    setManagedDataset(nextDataset.status === "fulfilled" ? nextDataset.value : null);
    const failures = [nextStatus, nextDataset].flatMap(result =>
      result.status === "rejected" ? [result.reason instanceof Error ? result.reason.message : "Training status could not be refreshed."] : []);
    setStatusError(failures.length ? failures.join(" · ") : null);
  }

  useEffect(() => {
    let cancelled = false;
    void fetchRuntimeSettings()
      .then((settings) => {
        if (!cancelled) setConfig((current) => ({ ...current, patience: settings.training_patience }));
      })
      .catch((nextError) => {
        if (!cancelled) setError(nextError instanceof Error ? nextError.message : "Runtime settings could not be loaded.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const { waitForIdle: waitForTrainingStatusIdle } = useSerialPolling(refreshStatus, 1200, {
    enabled: !starting,
    onError: (nextError) => {
      setStatus(null);
      setManagedDataset(null);
      setStatusError(nextError instanceof Error ? nextError.message : "Training status could not be refreshed.");
    },
  });

  async function launchTraining() {
    if (startRef.current || !status?.training_available || status.status === "running" ||
        (config.dataset_yaml.trim() === "yolo/data.yaml" && (!managedDataset?.ready || managedDataset.stale))) return;
    const scope = scopeRef.current;
    startRef.current = true;
    setStarting(true);
    setError(null);
    try {
      await waitForTrainingStatusIdle();
      if (!scope.isCurrent()) return;
      const [currentStatus, currentDataset] = await Promise.allSettled([
        fetchTrainingStatusStrict(), fetchTrainingDatasetStatusStrict(),
      ]);
      if (!scope.isCurrent()) return;
      const trainer = currentStatus.status === "fulfilled" ? currentStatus.value : null;
      const dataset = currentDataset.status === "fulfilled" ? currentDataset.value : null;
      setStatus(trainer);
      setManagedDataset(dataset);
      if (!trainer?.training_available || trainer.status === "running") {
        throw new Error("Training is unavailable or another run is active.");
      }
      if (config.dataset_yaml.trim() === "yolo/data.yaml" && (!dataset?.ready || dataset.stale)) {
        throw new Error(dataset?.message || "Managed dataset status unavailable; rebuild or refresh before training.");
      }
      // Only the acknowledged start response may report a new run.
      setStatus(null);
      const started = await startTraining(config);
      if (scope.isCurrent()) setStatus(started);
    } catch (nextError) {
      if (scope.isCurrent()) setError(nextError instanceof Error ? nextError.message : "Training could not start.");
    } finally {
      startRef.current = false;
      if (scope.isCurrent()) setStarting(false);
    }
  }

  const running = status?.status === "running";
  const usesManagedDataset = config.dataset_yaml.trim() === "yolo/data.yaml";
  const managedDatasetBlocked = usesManagedDataset && (!managedDataset?.ready || managedDataset.stale);
  const early = status?.early_stopping ?? null;

  return (
    <div className="page-stack">
      <div className="two-column-grid">
        <section className="panel training-form">
          <div className="panel-header">
            <div>
              <h2>Training settings</h2>
              <p className="placeholder-copy">Run local Ultralytics YOLO training and stop automatically when validation fitness stops improving.</p>
            </div>
            <span className={`status-pill ${status?.training_available ? "status-implemented" : "status-planned"}`}>
              {status?.training_available ? "training available" : status ? "dependency required" : "status unavailable"}
            </span>
          </div>
          <div className="form-grid">
            <label className="full-span">Dataset YAML under datasets/
              <input value={config.dataset_yaml} onChange={(event: ChangeEvent<HTMLInputElement>) => setConfig({ ...config, dataset_yaml: event.target.value })} />
            </label>
            <label>Base model
              <input value={config.base_model} onChange={(event: ChangeEvent<HTMLInputElement>) => setConfig({ ...config, base_model: event.target.value })} />
            </label>
            <label>Device
              <input value={config.device} onChange={(event: ChangeEvent<HTMLInputElement>) => setConfig({ ...config, device: event.target.value })} />
            </label>
            <label>Maximum epochs
              <input type="number" min={1} max={300} value={config.epochs} onChange={(event: ChangeEvent<HTMLInputElement>) => setConfig({ ...config, epochs: Number(event.target.value) })} />
            </label>
            <label>Early-stop patience
              <input type="number" min={1} max={100} value={config.patience} onChange={(event: ChangeEvent<HTMLInputElement>) => setConfig({ ...config, patience: Number(event.target.value) })} />
            </label>
            <label>Image size
              <input type="number" min={64} max={2048} value={config.image_size} onChange={(event: ChangeEvent<HTMLInputElement>) => setConfig({ ...config, image_size: Number(event.target.value) })} />
            </label>
            <label>Batch size
              <input type="number" min={1} max={128} value={config.batch} onChange={(event: ChangeEvent<HTMLInputElement>) => setConfig({ ...config, batch: Number(event.target.value) })} />
            </label>
          </div>
          <p className="small-note">Patience is the number of validation epochs allowed without a new best fitness score before the run stops early.</p>
          {usesManagedDataset && (
            <div className="camera-status-list training-status-list">
              <div><span>Eligible reviewed frames</span><strong>{managedDataset?.eligible_frame_count ?? "—"}</strong></div>
              <div><span>Train / validation split</span><strong>{managedDataset?.train_count ?? "—"} / {managedDataset?.val_count ?? "—"}</strong></div>
              <div><span>Managed dataset</span><strong>{!managedDataset ? "unavailable" : managedDataset.stale ? "rebuild required" : managedDataset.ready ? "ready" : "not built"}</strong></div>
            </div>
          )}
          <button
            className="primary"
            onClick={() => void launchTraining()}
            disabled={starting || running || !status?.training_available || managedDatasetBlocked}
          >
            {running ? "Training in progress..." : starting ? "Starting..." : "Start training"}
          </button>
          {status && !status.training_available && (
            <code className="endpoint-code">cd apps\pc-studio\backend<br />pip install -r requirements-training.txt</code>
          )}
          {managedDatasetBlocked && onOpenReview && <button type="button" onClick={onOpenReview}>Open Dataset Review</button>}
          {managedDatasetBlocked && (
            <p className="warning-box">{managedDataset?.message ?? "Build the managed dataset in Dataset Review before using yolo/data.yaml."}</p>
          )}
          {error && <p className="error-message" role="alert">{error}</p>}
          {statusError && <p className="error-message" role="alert">{statusError}</p>}
        </section>

        <aside className="panel">
          <div className="panel-header">
            <div><h2>Training run</h2><p className="placeholder-copy">{status?.message ?? "Checking training availability..."}</p></div>
            <span className={`status-pill ${running ? "status-secondary" : ""}`}>{status?.status ?? "checking"}</span>
          </div>
          <div className="progress-track"><div style={{ width: `${status?.progress ?? 0}%` }} /></div>
          <div className="camera-status-list training-status-list">
            <div><span>Progress</span><strong>{status ? `${status.progress}%` : "—"}</strong></div>
            <div><span>Epochs completed</span><strong>{status?.completed_epochs ?? 0} / {status?.config?.epochs ?? config.epochs}</strong></div>
            <div><span>Run ID</span><strong>{status?.active_run_id ?? "none"}</strong></div>
            {status?.dataset_integrity_sha256 && <div><span>Verified dataset</span><strong title={status.dataset_integrity_sha256}>{status.dataset_integrity_sha256.slice(0, 12)}</strong></div>}
            <div><span>Best epoch</span><strong>{early?.best_epoch ?? "n/a"}</strong></div>
            <div><span>Without improvement</span><strong>{early ? `${early.epochs_without_improvement} / ${early.patience}` : "n/a"}</strong></div>
            <div><span>Output directory</span><strong>{status?.output_path ?? "none"}</strong></div>
            <div><span>Best checkpoint</span><strong>{status?.best_model_path ?? "not produced"}</strong></div>
          </div>
          <p className="small-note">Early stopping keeps the best checkpoint produced by the run. Model runtime export is not implemented yet.</p>
          {status?.error && <p className="error-message">{status.error}</p>}
          {onOpenModels && status?.best_model_path && (status.status === "completed" || status.status === "early_stopped") && <button type="button" onClick={onOpenModels}>Review checkpoint in Models</button>}
        </aside>
      </div>

      <TrainingConvergenceChart
        history={status?.history ?? []}
        earlyStopping={early}
        requestedEpochs={status?.config?.epochs ?? config.epochs}
      />
      <FunctionChecklist area="Training" />
    </div>
  );
}
