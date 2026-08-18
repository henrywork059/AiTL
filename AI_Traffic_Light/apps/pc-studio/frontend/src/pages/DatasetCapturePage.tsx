import { useEffect, useState } from "react";
import { API_BASE, captureLatestFrame, deleteDatasetCapture, fetchDatasetStatus } from "../api";
import { FunctionChecklist } from "../components/FunctionChecklist";
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

  async function refreshStatus() {
    const nextStatus = await fetchDatasetStatus();
    setDatasetStatus(nextStatus);
    setLastCapture(nextStatus.last_capture);
  }

  useEffect(() => {
    void refreshStatus();
    const timerId = window.setInterval(() => void refreshStatus(), 3000);
    return () => window.clearInterval(timerId);
  }, []);

  async function saveCurrentFrame() {
    setSaving(true);
    setMessage(null);
    try {
      const record = await captureLatestFrame({ session_id: sessionId, quality_tag: qualityTag, note });
      setLastCapture(record);
      setMessage(`Captured ${record.image_path}`);
      await refreshStatus();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Capture failed.");
    } finally {
      setSaving(false);
    }
  }

  async function deleteLastCapture() {
    if (!lastCapture) return;
    if (!window.confirm(`Permanently delete capture ${lastCapture.capture_id}? Its metadata and saved manual labels will also be removed.`)) return;
    setDeleting(true);
    setMessage(null);
    try {
      const result = await deleteDatasetCapture(lastCapture.capture_id);
      setLastCapture(null);
      setMessage(`Deleted ${result.capture_id}.`);
      await refreshStatus();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Capture could not be deleted.");
    } finally {
      setDeleting(false);
    }
  }

  const previewUrl = cameraStatus?.frame_available
    ? `${API_BASE}/api/camera/frame?v=${cameraStatus.frame_number}`
    : null;

  return (
    <div className="page-stack">
      <div className="capture-layout">
        <section className="panel camera-preview-panel">
          <div className="panel-header">
            <div>
              <h2>Frame preview</h2>
              <p className="placeholder-copy">Capture saves the exact receiver or simulation frame currently shown here.</p>
            </div>
            <span className="status-pill muted">{cameraStatus?.origin ?? "no frame"}</span>
          </div>
          <div className="camera-frame-wrapper">
            {previewUrl ? (
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
            <button className="primary" onClick={() => void saveCurrentFrame()} disabled={saving || deleting || !cameraStatus?.frame_available || !sessionId}>
              {saving ? "Saving..." : "Capture frame"}
            </button>
            {message && <p className={message.startsWith("Captured") || message.startsWith("Deleted") ? "success-message" : "error-message"}>{message}</p>}
          </section>

          <section className="panel compact-panel">
            <div className="panel-header"><h2>Dataset storage</h2></div>
            <div className="camera-status-list">
              <div><span>Images</span><strong>{datasetStatus?.frame_count ?? 0}</strong></div>
              <div><span>Metadata files</span><strong>{datasetStatus?.metadata_count ?? 0}</strong></div>
              <div><span>Sessions</span><strong>{datasetStatus?.session_count ?? 0}</strong></div>
              <div><span>Location</span><strong>{datasetStatus?.dataset_path ?? "datasets/captures"}</strong></div>
            </div>
            {lastCapture && (
              <>
                <p className="small-note">Most recent capture</p>
                <code className="endpoint-code">{lastCapture.image_path}</code>
                <button className="danger" type="button" onClick={() => void deleteLastCapture()} disabled={deleting || saving}>
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
