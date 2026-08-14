import { useEffect, useState } from "react";
import { fetchTrainingStatus, startTraining } from "../api";
import { FunctionChecklist } from "../components/FunctionChecklist";
import type { TrainingConfig, TrainingStatus } from "../types";

const DEFAULT_CONFIG: TrainingConfig = {
  dataset_yaml: "yolo/data.yaml",
  base_model: "yolo26n.pt",
  epochs: 10,
  image_size: 640,
  batch: 8,
  device: "cpu",
};

export function TrainExportPage() {
  const [status, setStatus] = useState<TrainingStatus | null>(null);
  const [config, setConfig] = useState<TrainingConfig>(DEFAULT_CONFIG);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshStatus() {
    setStatus(await fetchTrainingStatus());
  }

  useEffect(() => {
    void refreshStatus();
    const timerId = window.setInterval(() => void refreshStatus(), 1500);
    return () => window.clearInterval(timerId);
  }, []);

  async function launchTraining() {
    setStarting(true);
    setError(null);
    try {
      setStatus(await startTraining(config));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Training could not start.");
    } finally {
      setStarting(false);
    }
  }

  const running = status?.status === "running";

  return (
    <div className="page-stack">
      <div className="two-column-grid">
        <section className="panel training-form">
          <div className="panel-header">
            <div>
              <h2>YOLO training configuration</h2>
              <p className="placeholder-copy">Runs a real local Ultralytics job only with a labeled YOLO dataset.</p>
            </div>
            <span className={`status-pill ${status?.training_available ? "" : "status-planned"}`}>
              {status?.training_available ? "runner available" : "optional dependency missing"}
            </span>
          </div>
          <div className="form-grid">
            <label className="full-span">Dataset YAML inside datasets/
              <input value={config.dataset_yaml} onChange={(event) => setConfig({ ...config, dataset_yaml: event.target.value })} />
            </label>
            <label>Base model
              <input value={config.base_model} onChange={(event) => setConfig({ ...config, base_model: event.target.value })} />
            </label>
            <label>Device
              <input value={config.device} onChange={(event) => setConfig({ ...config, device: event.target.value })} />
            </label>
            <label>Epochs
              <input type="number" min={1} max={300} value={config.epochs} onChange={(event) => setConfig({ ...config, epochs: Number(event.target.value) })} />
            </label>
            <label>Image size
              <input type="number" min={64} max={2048} value={config.image_size} onChange={(event) => setConfig({ ...config, image_size: Number(event.target.value) })} />
            </label>
            <label>Batch
              <input type="number" min={1} max={128} value={config.batch} onChange={(event) => setConfig({ ...config, batch: Number(event.target.value) })} />
            </label>
          </div>
          <button onClick={() => void launchTraining()} disabled={starting || running || !status?.training_available}>
            {running ? "Training running..." : starting ? "Starting..." : "Start real training"}
          </button>
          {!status?.training_available && (
            <code className="endpoint-code">cd apps\pc-studio\backend<br />pip install -r requirements-training.txt</code>
          )}
          {error && <p className="error-message">{error}</p>}
        </section>

        <aside className="panel">
          <div className="panel-header"><h2>Run status</h2><span className="status-pill">{status?.status ?? "checking"}</span></div>
          <div className="progress-track"><div style={{ width: `${status?.progress ?? 0}%` }} /></div>
          <p className="placeholder-copy">{status?.message ?? "Checking backend training availability..."}</p>
          <div className="camera-status-list training-status-list">
            <div><span>Progress</span><strong>{status?.progress ?? 0}%</strong></div>
            <div><span>Run ID</span><strong>{status?.active_run_id ?? "none"}</strong></div>
            <div><span>Output</span><strong>{status?.output_path ?? "none"}</strong></div>
            <div><span>Best model</span><strong>{status?.best_model_path ?? "not produced"}</strong></div>
          </div>
          <p className="small-note">Raw captured images are not labels. Add YOLO bounding-box labels and a dataset YAML before training.</p>
          {status?.error && <p className="error-message">{status.error}</p>}
        </aside>
      </div>
      <FunctionChecklist area="Training" />
    </div>
  );
}
