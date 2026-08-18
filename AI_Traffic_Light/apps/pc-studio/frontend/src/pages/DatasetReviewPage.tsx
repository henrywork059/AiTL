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
        ? "Review saved as a negative example with zero objects."
        : `Saved ${saved.labels.length} bounding box${saved.labels.length === 1 ? "" : "es"}.`);
      await Promise.all([refreshCaptures(selectedCapture.capture_id), refreshTrainingDataset()]);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Labels could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function deleteSelectedCapture() {
    if (!selectedCapture) return;
    if (dirty && !window.confirm("This image has unsaved label changes. Delete the capture and discard those edits?")) return;
    if (!window.confirm(`Permanently delete capture ${selectedCapture.capture_id}? The image, metadata, and saved manual labels will be removed.`)) return;
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
        ? `Deleted ${result.capture_id}. Rebuild the managed YOLO dataset before the next training run.`
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
      setMessage(`Managed dataset ready: ${status.train_count} train / ${status.val_count} validation frames.`);
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
              <h2>Captured images</h2>
              <p className="placeholder-copy">Select an image to review or label.</p>
            </div>
            <span className="status-pill muted">{captures.length} saved</span>
          </div>
          <button onClick={() => void refreshCaptures(selectedCaptureId)} disabled={loading || deleting}>Refresh list</button>
          <div className="capture-browser-list">
            {captures.map((capture) => (
              <button
                key={capture.capture_id}
                className={`capture-browser-item ${capture.capture_id === selectedCaptureId ? "active" : ""}`}
                onClick={() => {
                  if (dirty && !window.confirm("Discard unsaved label changes and switch images?")) return;
                  setSelectedCaptureId(capture.capture_id);
                  setMessage(null);
                }}
              >
                <strong>{capture.session_id}</strong>
                <span>{capture.quality_tag} · {capture.origin}</span>
                <span>{capture.labeled ? `${capture.label_count} boxes · reviewed` : "not reviewed"}</span>
              </button>
            ))}
            {!loading && captures.length === 0 && (
              <p className="small-note">No captures yet. Save at least two usable frames before building a train/validation dataset.</p>
            )}
          </div>
        </aside>

        <main className="panel labeling-workspace">
          <div className="panel-header">
            <div>
              <h2>Annotation workspace</h2>
              <p className="placeholder-copy">Choose a class, then drag on the saved image to draw a bounding box.</p>
            </div>
            <span className={`status-pill ${labelDocument?.reviewed ? "status-implemented" : "status-planned"}`}>
              {labelDocument?.reviewed ? "reviewed" : "not reviewed"}
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
                  <button className="primary" onClick={() => void saveLabels()} disabled={saving || deleting}>{saving ? "Saving..." : "Save review"}</button>
                  <button className="danger" onClick={() => void deleteSelectedCapture()} disabled={saving || deleting}>
                    {deleting ? "Deleting..." : "Delete capture"}
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
                Saving zero boxes marks this as a reviewed negative example. Deleting a capture also removes its metadata and saved labels.
              </p>
              <div className="saved-label-list">
                {labels.map((label, index) => (
                  <div key={`${label.class_id}-${index}`}>
                    <span>{index + 1}. {label.class_name} · [{label.box_xyxy.map((value) => Math.round(value)).join(", ")}]</span>
                    <button onClick={() => updateLabels(labels.filter((_, currentIndex) => currentIndex !== index))}>Remove</button>
                  </div>
                ))}
                {labels.length === 0 && <p className="small-note">No boxes on this image.</p>}
              </div>
            </>
          ) : (
            <div className="label-empty-state">Select a captured image to begin review.</div>
          )}
          {dirty && <p className="warning-box">This image has unsaved label changes.</p>}
          {message && <p className="success-message">{message}</p>}
          {error && <p className="error-message">{error}</p>}
        </main>
      </div>

      <section className="panel managed-dataset-panel">
        <div className="panel-header">
          <div>
            <h2>Managed YOLO dataset</h2>
            <p className="placeholder-copy">Builds the default <code>datasets/yolo/data.yaml</code> used by the training page from reviewed, eligible captures.</p>
          </div>
          <span className={`status-pill ${trainingDataset?.ready ? "status-implemented" : trainingDataset?.stale ? "status-planned" : ""}`}>
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
        <button className="primary" onClick={() => void buildDataset()} disabled={building || (trainingDataset?.eligible_frame_count ?? 0) < 2}>
          {building ? "Building..." : trainingDataset?.ready ? "Rebuild managed dataset" : "Build managed dataset"}
        </button>
      </section>

      <FunctionChecklist area="Dataset" />
    </div>
  );
}
