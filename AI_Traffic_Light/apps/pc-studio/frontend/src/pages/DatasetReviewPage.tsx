import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import {
  buildTrainingDataset,
  captureImageUrl,
  deleteDatasetCapture,
  fetchCaptureLabels,
  fetchDatasetCaptures,
  fetchTrainingDatasetStatus,
  saveCaptureLabels,
} from "../api";
import { FunctionChecklist } from "../components/FunctionChecklist";
import { LabelingCanvas } from "../components/LabelingCanvas";
import type {
  CaptureLabelDocument,
  CaptureSummary,
  DatasetLabelBox,
  LabelClass,
  TrainingDatasetStatus,
} from "../types";
import "./datasetReview.css";

export function DatasetReviewPage() {
  const [captures, setCaptures] = useState<CaptureSummary[]>([]);
  const [classes, setClasses] = useState<LabelClass[]>([]);
  const [selectedCaptureId, setSelectedCaptureId] = useState<string | null>(null);
  const [labelDocument, setLabelDocument] = useState<CaptureLabelDocument | null>(null);
  const [labels, setLabels] = useState<DatasetLabelBox[]>([]);
  const [selectedClassId, setSelectedClassId] = useState(0);
  const [trainingDataset, setTrainingDataset] = useState<TrainingDatasetStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [building, setBuilding] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedCapture = useMemo(
    () => captures.find((capture) => capture.capture_id === selectedCaptureId) ?? null,
    [captures, selectedCaptureId],
  );

  async function refreshCaptures(preferredCaptureId?: string | null) {
    const data = await fetchDatasetCaptures();
    setCaptures(data.captures);
    setClasses(data.classes);
    setSelectedClassId((current) => data.classes.some((item) => item.id === current) ? current : (data.classes[0]?.id ?? 0));
    const preferred = preferredCaptureId ?? selectedCaptureId;
    const nextId = data.captures.some((item) => item.capture_id === preferred)
      ? preferred
      : (data.captures[0]?.capture_id ?? null);
    setSelectedCaptureId(nextId);
  }

  async function refreshTrainingDataset() {
    setTrainingDataset(await fetchTrainingDatasetStatus());
  }

  useEffect(() => {
    async function initialLoad() {
      setLoading(true);
      try {
        await Promise.all([refreshCaptures(null), refreshTrainingDataset()]);
      } finally {
        setLoading(false);
      }
    }
    void initialLoad();
  }, []);

  useEffect(() => {
    if (!selectedCaptureId) {
      setLabelDocument(null);
      setLabels([]);
      return;
    }
    let active = true;
    setError(null);
    void fetchCaptureLabels(selectedCaptureId)
      .then((document) => {
        if (!active) return;
        setLabelDocument(document);
        setLabels(document.labels);
        setDirty(false);
      })
      .catch((nextError) => {
        if (!active) return;
        setError(nextError instanceof Error ? nextError.message : "Labels could not be loaded.");
      });
    return () => { active = false; };
  }, [selectedCaptureId]);

  function updateLabels(nextLabels: DatasetLabelBox[]) {
    setLabels(nextLabels);
    setDirty(true);
    setMessage(null);
  }

  async function saveLabels() {
    if (!selectedCapture) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const saved = await saveCaptureLabels(selectedCapture.capture_id, labels);
      setLabelDocument(saved);
      setLabels(saved.labels);
      setDirty(false);
      setMessage(saved.labels.length === 0
        ? "Reviewed negative saved: this frame is labeled with zero objects."
        : `Saved ${saved.labels.length} bounding-box label${saved.labels.length === 1 ? "" : "s"}.`);
      await Promise.all([refreshCaptures(selectedCapture.capture_id), refreshTrainingDataset()]);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Labels could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function deleteSelectedCapture() {
    if (!selectedCapture) return;
    if (dirty && !window.confirm("This frame has unsaved label changes. Delete the captured image and discard those changes?")) return;
    if (!window.confirm(`Delete captured image ${selectedCapture.capture_id}? The image, metadata, and saved manual labels will be permanently removed.`)) return;
    setDeleting(true);
    setError(null);
    setMessage(null);
    try {
      const result = await deleteDatasetCapture(selectedCapture.capture_id);
      setLabelDocument(null);
      setLabels([]);
      setDirty(false);
      setTrainingDataset(result.training_dataset);
      await refreshCaptures(null);
      setMessage(result.training_dataset.stale
        ? `Deleted ${result.capture_id}. The managed YOLO dataset is now stale and should be rebuilt.`
        : `Deleted ${result.capture_id}.`);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Captured image could not be deleted.");
    } finally {
      setDeleting(false);
    }
  }

  async function buildDataset() {
    setBuilding(true);
    setError(null);
    setMessage(null);
    try {
      const status = await buildTrainingDataset(0.2);
      setTrainingDataset(status);
      setMessage(`Built ${status.train_count} training and ${status.val_count} validation frames at ${status.dataset_yaml}.`);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Training dataset could not be built.");
    } finally {
      setBuilding(false);
    }
  }

  return (
    <div className="page-stack">
      <div className="dataset-review-layout">
        <aside className="panel capture-browser-panel">
          <div className="panel-header">
            <div>
              <h2>Captured frames</h2>
              <p className="placeholder-copy">{captures.length} saved frame{captures.length === 1 ? "" : "s"}</p>
            </div>
            <button onClick={() => void refreshCaptures(selectedCaptureId)} disabled={loading || deleting}>Refresh</button>
          </div>
          <div className="capture-browser-list">
            {captures.map((capture) => (
              <button
                key={capture.capture_id}
                className={`capture-browser-item ${capture.capture_id === selectedCaptureId ? "active" : ""}`}
                onClick={() => {
                  if (dirty && !window.confirm("Discard unsaved label changes and switch frames?")) return;
                  setSelectedCaptureId(capture.capture_id);
                  setMessage(null);
                }}
              >
                <strong>{capture.session_id}</strong>
                <span>{capture.quality_tag} · {capture.origin}</span>
                <span>{capture.labeled ? `${capture.label_count} boxes · reviewed` : "unreviewed"}</span>
              </button>
            ))}
            {!loading && captures.length === 0 && (
              <p className="small-note">No captures yet. Save at least two frames in Dataset Capture before labeling.</p>
            )}
          </div>
        </aside>

        <main className="panel labeling-workspace">
          <div className="panel-header">
            <div>
              <h2>Manual bounding-box labels</h2>
              <p className="placeholder-copy">Drag on the saved image to add a box for the selected class.</p>
            </div>
            <span className={`status-pill ${labelDocument?.reviewed ? "" : "status-planned"}`}>
              {labelDocument?.reviewed ? "reviewed" : "unreviewed"}
            </span>
          </div>

          {selectedCapture && labelDocument ? (
            <>
              <div className="label-toolbar">
                <label>Class
                  <select value={selectedClassId} onChange={(event: ChangeEvent<HTMLSelectElement>) => setSelectedClassId(Number(event.target.value))}>
                    {classes.map((item) => <option key={item.id} value={item.id}>{item.id}: {item.name}</option>)}
                  </select>
                </label>
                <div className="label-toolbar-actions">
                  <button onClick={() => updateLabels([])} disabled={labels.length === 0 || deleting}>Clear boxes</button>
                  <button onClick={() => void saveLabels()} disabled={saving || deleting}>{saving ? "Saving..." : "Save labels"}</button>
                  <button onClick={() => void deleteSelectedCapture()} disabled={saving || deleting}>
                    {deleting ? "Deleting..." : "Delete captured image"}
                  </button>
                </div>
              </div>
              <LabelingCanvas
                imageUrl={captureImageUrl(selectedCapture.capture_id)}
                width={selectedCapture.width}
                height={selectedCapture.height}
                classes={classes}
                selectedClassId={selectedClassId}
                labels={labels}
                onChange={updateLabels}
              />
              <p className="small-note">
                Deleting a capture also removes its metadata and saved manual labels. If that capture was included in the managed YOLO build, the dataset becomes stale until rebuilt.
              </p>
              <div className="saved-label-list">
                {labels.map((label, index) => (
                  <div key={`${label.class_id}-${index}`}>
                    <span>{index + 1}. {label.class_name} · [{label.box_xyxy.map((value) => Math.round(value)).join(", ")}]</span>
                    <button onClick={() => updateLabels(labels.filter((_, currentIndex) => currentIndex !== index))}>Remove</button>
                  </div>
                ))}
                {labels.length === 0 && <p className="small-note">No boxes on this frame.</p>}
              </div>
            </>
          ) : (
            <div className="label-empty-state">Select or capture a frame to start manual labeling.</div>
          )}
          {dirty && <p className="small-note">Unsaved label changes.</p>}
          {message && <p className="success-message">{message}</p>}
          {error && <p className="error-message">{error}</p>}
        </main>
      </div>

      <section className="panel managed-dataset-panel">
        <div className="panel-header">
          <div>
            <h2>Managed YOLO training dataset</h2>
            <p className="placeholder-copy">Builds the default <code>datasets/yolo/data.yaml</code> used by Train / Export.</p>
          </div>
          <span className={`status-pill ${trainingDataset?.ready ? "" : "status-planned"}`}>
            {trainingDataset?.ready ? "ready" : trainingDataset?.stale ? "rebuild required" : "not built"}
          </span>
        </div>
        <div className="managed-dataset-metrics">
          <div><span>Reviewed</span><strong>{trainingDataset?.labeled_frame_count ?? 0}</strong></div>
          <div><span>Eligible</span><strong>{trainingDataset?.eligible_frame_count ?? 0}</strong></div>
          <div><span>Boxes</span><strong>{trainingDataset?.label_box_count ?? 0}</strong></div>
          <div><span>Train / Val</span><strong>{trainingDataset?.train_count ?? 0} / {trainingDataset?.val_count ?? 0}</strong></div>
        </div>
        <p className="small-note">{trainingDataset?.message ?? "Checking managed dataset status..."}</p>
        <button onClick={() => void buildDataset()} disabled={building || (trainingDataset?.eligible_frame_count ?? 0) < 2}>
          {building ? "Building..." : trainingDataset?.ready ? "Rebuild training dataset" : "Build training dataset"}
        </button>
      </section>

      <FunctionChecklist area="Dataset" />
    </div>
  );
}
