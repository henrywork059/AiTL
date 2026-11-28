import { useLayoutEffect, useRef, useState } from "react";
import { API_BASE, captureLatestFrame, deleteDatasetCapture, fetchDatasetStatusStrict } from "../api";
import { FunctionChecklist } from "../components/FunctionChecklist";
import { SimulationCamera3D } from "../components/SimulationCamera3D";
import { useSerialPolling } from "../lib/useSerialPolling";
import { createPollingScope, type PollingContext } from "../lib/pollingScope";
import { matchesSelectedCameraFrame } from "../lib/cameraPreviewState";
import type { CameraStatus, CaptureQualityTag, CaptureRecord, DatasetStatus } from "../types";

type Props = {
  cameraStatus: CameraStatus | null;
};

export function DatasetCapturePage({ cameraStatus }: Props) {
  const [datasetStatus, setDatasetStatus] = useState<DatasetStatus | null>(null);
  const [sessionId, setSessionId] = useState("default");
  const [qualityTag, setQualityTag] = useState<CaptureQualityTag>("unreviewed");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [lastCapture, setLastCapture] = useState<CaptureRecord | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const mutationRef = useRef(false);
  const scopeRef = useRef(createPollingScope());
  useLayoutEffect(() => {
    const scope = createPollingScope();
    scopeRef.current = scope;
    return () => scope.retire();
  }, []);

  async function refreshStatus(context?: PollingContext) {
    const nextStatus = await fetchDatasetStatusStrict(context?.signal);
    if (context && !context.isCurrent()) return;
    setDatasetStatus(nextStatus);
    setLastCapture(nextStatus.last_capture);
    setStatusError(null);
  }

  const { runNow: refreshDatasetStatus, waitForIdle: waitForDatasetStatusIdle } = useSerialPolling(refreshStatus, 3000, {
    enabled: !saving && !deleting,
    onError: (error) => {
      setDatasetStatus(null);
      setLastCapture(null);
      setStatusError(error instanceof Error ? error.message : "Dataset status could not be refreshed.");
    },
  });

  const captureReady = Boolean(cameraStatus?.active_source_id && matchesSelectedCameraFrame(
    cameraStatus, cameraStatus.active_source_id, cameraStatus.simulation_enabled ? "simulation" : "esp32",
  ));

  async function saveCurrentFrame() {
    if (mutationRef.current || !captureReady || !cameraStatus?.active_source_id || !cameraStatus.origin ||
        !datasetStatus?.capture_enabled || !sessionId.trim()) return;
    const expectedSource = cameraStatus.active_source_id;
    const expectedOrigin = cameraStatus.origin;
    const scope = scopeRef.current;
    mutationRef.current = true;
    setSaving(true);
    setMessage(null);
    try {
      await waitForDatasetStatusIdle();
      if (!scope.isCurrent()) return;
      const record = await captureLatestFrame({
        session_id: sessionId, quality_tag: qualityTag, note,
        expected_source_id: expectedSource, expected_origin: expectedOrigin,
      });
      if (!scope.isCurrent()) return;
      if (record.source_id !== expectedSource || record.origin !== expectedOrigin || !record.capture_id) {
        throw new Error("Captured frame identity differs from the selected preview; inspect the saved capture.");
      }
      setLastCapture(record);
      setMessage(`Captured ${record.image_path}`);
      // The poll has separate error state. An acknowledged write remains acknowledged.
      await refreshDatasetStatus();
    } catch (error) {
      if (!scope.isCurrent()) return;
      setDatasetStatus(null);
      setLastCapture(null);
      setMessage(error instanceof Error ? error.message : "Capture failed; refresh dataset status before retrying.");
    } finally {
      mutationRef.current = false;
      if (scope.isCurrent()) setSaving(false);
    }
  }

  async function deleteLastCapture() {
    if (mutationRef.current || !lastCapture || !datasetStatus) return;
    const id = lastCapture.capture_id;
    if (!window.confirm(`Permanently delete capture ${id}? Its metadata and saved manual labels will also be removed.`)) return;
    const scope = scopeRef.current;
    mutationRef.current = true;
    setDeleting(true);
    setMessage(null);
    setLastCapture(null);
    try {
      await waitForDatasetStatusIdle();
      if (!scope.isCurrent()) return;
      const result = await deleteDatasetCapture(id);
      if (!scope.isCurrent()) return;
      if (result.capture_id !== id || result.deleted !== true) {
        throw new Error("Deletion was not confirmed for the selected capture; refresh dataset status.");
      }
      setMessage(`Deleted ${result.capture_id}.${result.cleanup_pending ? " File cleanup pending." : ""}`);
      await refreshDatasetStatus();
    } catch (error) {
      if (!scope.isCurrent()) return;
      setDatasetStatus(null);
      setLastCapture(null);
      setMessage(error instanceof Error ? error.message : "Capture deletion could not be confirmed.");
    } finally {
      mutationRef.current = false;
      if (scope.isCurrent()) setDeleting(false);
    }
  }

  const previewUrl = captureReady
    ? `${API_BASE}/api/camera/frame?v=${cameraStatus?.frame_number ?? 0}`
    : null;

  return (
    <div className="page-stack">
      <div className="capture-layout">
        <section className="panel camera-preview-panel">
          <div className="panel-header">
            <div>
              <h2>Frame preview</h2>
              <p className="placeholder-copy">{cameraStatus?.simulation_enabled ? "Preview the live 3D simulation. Capture saves its original 2D synthetic image for AI training and labels." : "Capture saves the receiver image currently shown here."}</p>
            </div>
            <span className="status-pill muted">{cameraStatus?.origin ?? "no frame"}</span>
          </div>
          <div className="camera-frame-wrapper">
            {cameraStatus?.simulation_enabled && previewUrl ? (
              <SimulationCamera3D key={cameraStatus.active_source_id ?? "simulation_camera"} sourceId={cameraStatus.active_source_id?.startsWith("simulation_camera") ? cameraStatus.active_source_id : "simulation_camera"} />
            ) : previewUrl ? (
              <img className="camera-frame" src={previewUrl} alt="Current frame ready for dataset capture" />
            ) : (
              <div className="camera-empty-state">
                <strong>No frame available</strong>
                <p>Start Camera Sources simulation or provide a device frame before capturing data.</p>
              </div>
            )}
          </div>
        </section>

        <aside className="side-column">
          <section className="panel compact-panel capture-form">
            <div className="panel-header"><h2>Capture details</h2><span className="status-pill muted">saved with image</span></div>
            <label>
              Session ID
              <input value={sessionId} maxLength={64} onChange={(event) => setSessionId(event.target.value)} />
            </label>
            <label>
              Quality
              <select value={qualityTag} onChange={(event) => setQualityTag(event.target.value as CaptureQualityTag)}>
                <option value="unreviewed">Unreviewed</option>
                <option value="useful">Useful</option>
                <option value="bad">Bad / exclude from training</option>
              </select>
            </label>
            <label>
              Note
              <textarea value={note} maxLength={500} rows={4} placeholder="Optional context for later review" onChange={(event) => setNote(event.target.value)} />
            </label>
            <button className="primary" onClick={() => void saveCurrentFrame()} disabled={saving || deleting || !captureReady || !sessionId.trim() || !datasetStatus?.capture_enabled}>
              {saving ? "Saving..." : "Capture frame"}
            </button>
            {message && <p role="status" className={message.startsWith("Captured") || message.startsWith("Deleted") ? "success-message" : "error-message"}>{message}</p>}
            {statusError && <p role="alert" className="error-message">Dataset status: {statusError}</p>}
          </section>

          <section className="panel compact-panel">
            <div className="panel-header"><h2>Dataset storage</h2></div>
            <div className="camera-status-list">
              <div><span>Images</span><strong>{datasetStatus?.frame_count ?? "—"}</strong></div>
              <div><span>Metadata files</span><strong>{datasetStatus?.metadata_count ?? "—"}</strong></div>
              <div><span>Sessions</span><strong>{datasetStatus?.session_count ?? "—"}</strong></div>
              <div><span>Location</span><strong>{datasetStatus?.dataset_path ?? "datasets/captures"}</strong></div>
            </div>
            {lastCapture && (
              <>
                <p className="small-note">Most recent capture</p>
                <code className="endpoint-code">{lastCapture.image_path}</code>
                <button className="danger" type="button" onClick={() => void deleteLastCapture()} disabled={deleting || saving || !datasetStatus}>
                  {deleting ? "Deleting..." : "Delete last capture"}
                </button>
              </>
            )}
          </section>
        </aside>
      </div>
      <FunctionChecklist area="Dataset" />
    </div>
  );
}
