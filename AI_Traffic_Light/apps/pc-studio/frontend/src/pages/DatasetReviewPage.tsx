import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import {
  buildTrainingDataset,
  captureImageUrl,
  deleteDatasetCapture,
  fetchCaptureLabels,
  fetchDatasetCapturesStrict,
  fetchTrainingDatasetStatusStrict,
  saveCaptureLabels,
} from "../api";
import { FunctionChecklist } from "../components/FunctionChecklist";
import { LabelingCanvas } from "../components/LabelingCanvas";
import { createPollingScope } from "../lib/pollingScope";
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
  const [refreshing, setRefreshing] = useState(false);
  const [labelLoading, setLabelLoading] = useState(false);
  const [labelRevision, setLabelRevision] = useState(0);
  const [decodedImage, setDecodedImage] = useState<{captureId: string; revision: number; url: string} | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);
  const [listAvailable, setListAvailable] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedCapture = useMemo(
    () => captures.find((capture) => capture.capture_id === selectedCaptureId) ?? null,
    [captures, selectedCaptureId],
  );

  const busy = loading || refreshing || saving || deleting || building;
  const currentDocument = selectedCapture && labelDocument?.capture_id === selectedCapture.capture_id && labelDocument.width === selectedCapture.width && labelDocument.height === selectedCapture.height ? labelDocument : null;

  const imageReady = Boolean(selectedCapture && decodedImage?.captureId === selectedCapture.capture_id && decodedImage.revision === labelRevision);

  async function refreshCaptures(preferredCaptureId?: string | null) {
    const data = await fetchDatasetCapturesStrict();
    setListAvailable(true);
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
    try { setTrainingDataset(await fetchTrainingDatasetStatusStrict()); }
    catch (reason) { setTrainingDataset(null); throw reason; }
  }

  async function refreshCaptureList() {
    if (busy || dirty) return;
    setRefreshing(true);
    try {
      await refreshCaptures(selectedCaptureId);
      await refreshTrainingDataset();
      setDecodedImage(null);
      setLabelRevision(value => value + 1);
      setError(null);
    } catch (nextError) {
      setListAvailable(false);
      setError(nextError instanceof Error ? nextError.message : "Capture list could not be refreshed.");
    } finally { setRefreshing(false); }
  }

  useEffect(() => {
    async function initialLoad() {
      setLoading(true);
      try {
        await Promise.all([refreshCaptures(null), refreshTrainingDataset()]);
      } catch (nextError) {
        setError(nextError instanceof Error ? nextError.message : "Dataset review could not be loaded.");
      } finally {
        setLoading(false);
      }
    }
    void initialLoad();
  }, []);

  useEffect(() => {
    setLabelDocument(null);
    setLabels([]);
    setDirty(false);
    if (!selectedCaptureId) { setLabelLoading(false); return; }
    setLabelLoading(true);
    const scope = createPollingScope();
    setError(null);
    void fetchCaptureLabels(selectedCaptureId, scope.signal)
      .then((document) => {
        if (!scope.isCurrent()) return;
        if (document.capture_id !== selectedCaptureId) throw new Error("Label response capture identity mismatch.");
        setLabelDocument(document);
        setLabels(document.labels);
        setDirty(false);
      })
      .catch((nextError) => {
        if (!scope.isCurrent()) return;
        setError(nextError instanceof Error ? nextError.message : "Labels could not be loaded.");
      }).finally(() => { if (scope.isCurrent()) setLabelLoading(false); });
    return () => scope.retire();
  }, [selectedCaptureId, labelRevision]);

  useEffect(() => {
    setDecodedImage(null);
    setImageError(null);
    if (!selectedCaptureId || !selectedCapture || !currentDocument || !listAvailable) return;
    const scope = createPollingScope();
    let url: string | null = null;
    const captureId = selectedCaptureId;
    const width = selectedCapture.width, height = selectedCapture.height;
    async function loadImage() {
      try {
        const response = await fetch(captureImageUrl(captureId), { signal: scope.signal, cache: "no-store" });
        if (!response.ok) throw new Error("Captured image unavailable.");
        const blob = await response.blob();
        if (!/^image\/(jpeg|png|webp)$/.test(blob.type)) throw new Error("Captured image format unavailable.");
        if (!scope.isCurrent()) return;
        url = URL.createObjectURL(blob);
        const image = new Image();
        image.src = url;
        await image.decode();
        if (!scope.isCurrent()) return;
        if (image.naturalWidth !== width || image.naturalHeight !== height) throw new Error("Captured image dimensions differ from labels.");
        setDecodedImage({captureId, revision: labelRevision, url});
      } catch (reason) {
        if (scope.isCurrent()) setImageError(reason instanceof Error ? reason.message : "Captured image could not be decoded.");
        if (url) { URL.revokeObjectURL(url); url = null; }
      }
    }
    void loadImage();
    return () => { scope.retire(); if (url) URL.revokeObjectURL(url); };
  }, [selectedCaptureId, selectedCapture?.width, selectedCapture?.height, Boolean(currentDocument), listAvailable, labelRevision]);

  function updateLabels(nextLabels: DatasetLabelBox[]) {
    if (!currentDocument || !imageReady || busy || labelLoading) return;
    setLabels(nextLabels);
    setDirty(true);
    setMessage(null);
  }

  async function saveLabels() {
    if (!selectedCapture || !currentDocument || !imageReady || busy || labelLoading || !listAvailable) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const saved = await saveCaptureLabels(selectedCapture.capture_id, labels);
      if (saved.capture_id !== selectedCapture.capture_id || saved.width !== selectedCapture.width || saved.height !== selectedCapture.height) throw new Error("Saved label identity mismatch; reload before editing.");
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
    if (!selectedCapture || !currentDocument || busy || labelLoading || !listAvailable) return;
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
    if (busy || dirty || labelLoading || !listAvailable) return;
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
            <span className="status-pill muted">{listAvailable ? `${captures.length} saved` : "Unavailable"}</span>
          </div>
          <button onClick={() => void refreshCaptureList()} disabled={busy || dirty}>Refresh list</button>
          <div className="capture-browser-list">
            {captures.map((capture) => (
              <button
                key={capture.capture_id}
                className={`capture-browser-item ${capture.capture_id === selectedCaptureId ? "active" : ""}`}
                aria-pressed={capture.capture_id === selectedCaptureId}
                disabled={busy || !listAvailable}
                onClick={() => {
                  if (capture.capture_id === selectedCaptureId) return;
                  if (dirty && !window.confirm("Discard unsaved label changes and switch images?")) return;
                  setDecodedImage(null);
                  setLabelDocument(null);
                  setLabels([]);
                  setDirty(false);
                  setSelectedCaptureId(capture.capture_id);
                  setMessage(null);
                }}
              >
                <strong>{capture.session_id}</strong>
                <span>{capture.quality_tag} · {capture.origin}</span>
                <span>{capture.labeled ? `${capture.label_count} boxes · reviewed` : "not reviewed"}</span>
              </button>
            ))}
            {!loading && listAvailable && captures.length === 0 && (
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
            <span className={`status-pill ${currentDocument?.reviewed ? "status-implemented" : "status-planned"}`}>
              {currentDocument?.reviewed ? "reviewed" : "not reviewed"}
            </span>
          </div>

          {selectedCapture && currentDocument && !labelLoading && listAvailable ? (
            <>
              <div className="label-toolbar">
                <label>Class
                  <select value={selectedClassId} onChange={(event: ChangeEvent<HTMLSelectElement>) => setSelectedClassId(Number(event.target.value))}>
                    {classes.map((item) => <option key={item.id} value={item.id}>{item.id}: {item.name}</option>)}
                  </select>
                </label>
                <div className="label-toolbar-actions">
                  <button onClick={() => updateLabels([])} disabled={!imageReady || labels.length === 0 || busy}>Clear boxes</button>
                  <button className="primary" onClick={() => void saveLabels()} disabled={busy || !imageReady}>{saving ? "Saving..." : "Save review"}</button>
                  <button className="danger" onClick={() => void deleteSelectedCapture()} disabled={busy}>
                    {deleting ? "Deleting..." : "Delete capture"}
                  </button>
                </div>
              </div>
              {imageReady && decodedImage ? <LabelingCanvas
                key={selectedCapture.capture_id + ":" + labelRevision}
                imageUrl={decodedImage.url}
                width={selectedCapture.width}
                height={selectedCapture.height}
                classes={classes}
                selectedClassId={selectedClassId}
                labels={labels}
                onChange={updateLabels}
              /> : <div className="label-empty-state" role="status">{imageError ?? "Loading captured image..."}</div>}
              <p className="small-note">
                Saving zero boxes marks this as a reviewed negative example. Deleting a capture also removes its metadata and saved labels.
              </p>
              <div className="saved-label-list">
                {labels.map((label, index) => (
                  <div key={`${label.class_id}-${index}`}>
                    <span>{index + 1}. {label.class_name} · [{label.box_xyxy.map((value) => Math.round(value)).join(", ")}]</span>
                    <button disabled={busy || !imageReady} onClick={() => updateLabels(labels.filter((_, currentIndex) => currentIndex !== index))}>Remove</button>
                  </div>
                ))}
                {labels.length === 0 && <p className="small-note">No boxes on this image.</p>}
              </div>
            </>
          ) : (
            <div className="label-empty-state">{labelLoading ? "Loading labels..." : selectedCapture ? "Labels unavailable for this capture. Select another capture or refresh the list." : "Select a captured image to begin review."}</div>
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
            {!trainingDataset ? "unavailable" : trainingDataset.ready ? "ready" : trainingDataset.stale ? "rebuild required" : "not built"}
          </span>
        </div>
        <div className="managed-dataset-metrics">
          <div><span>Reviewed</span><strong>{trainingDataset?.labeled_frame_count ?? "—"}</strong></div>
          <div><span>Eligible</span><strong>{trainingDataset?.eligible_frame_count ?? "—"}</strong></div>
          <div><span>Boxes</span><strong>{trainingDataset?.label_box_count ?? "—"}</strong></div>
          <div><span>Train / Val</span><strong>{trainingDataset?.train_count ?? "—"} / {trainingDataset?.val_count ?? "—"}</strong></div>
        </div>
        <p className="small-note">{trainingDataset?.message ?? "Checking managed dataset status..."}</p>
        <button className="primary" onClick={() => void buildDataset()} disabled={busy || dirty || labelLoading || !listAvailable || (trainingDataset?.eligible_frame_count ?? 0) < 2}>
          {building ? "Building..." : trainingDataset?.ready ? "Rebuild managed dataset" : "Build managed dataset"}
        </button>
      </section>

      <FunctionChecklist area="Dataset" />
    </div>
  );
}
