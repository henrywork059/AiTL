import { useEffect, useMemo, useState } from "react";
import { cameraPreviewUrl, fetchCameraInference, fetchInferenceStatus, inferredFrameUrl } from "../api";
import { CameraDetectionView } from "../components/CameraDetectionView";
import { DetectionTable } from "../components/DetectionTable";
import { fetchCrosswalks } from "../lib/crosswalksApi";
import { cameraRegions, regionClassCounts } from "../lib/regionCounts";
import { fetchRemoteCameraStatus } from "../lib/remoteCameraApi";
import { useSerialPolling } from "../lib/useSerialPolling";
import type { CameraStatus, DetectionFrame, InferenceStatus, Zone } from "../types";
import type { CrosswalkConfig } from "../types/crosswalks";
import type { RemoteCameraStatus } from "../lib/remoteCameraApi";
import "./liveInference.css";

type Props = {
  zones: Zone[]; // Kept for existing App composition; crossing regions are sourced independently.
  cameraStatus: CameraStatus | null;
  onRefresh: () => void;
  refreshing: boolean;
  onDetectionCountChange: (count: number) => void;
};

const errorMessage = (error: unknown): string => error instanceof Error ? error.message : "Camera AI request failed.";

export function LiveAiPage({ cameraStatus, onRefresh, refreshing, onDetectionCountChange }: Props) {
  const [cameras, setCameras] = useState<RemoteCameraStatus | null>(null);
  const [crosswalks, setCrosswalks] = useState<CrosswalkConfig | null>(null);
  const [model, setModel] = useState<InferenceStatus | null>(null);
  const [sourceId, setSourceId] = useState("");
  const [frame, setFrame] = useState<DetectionFrame | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showBoxes, setShowBoxes] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [showRegions, setShowRegions] = useState(true);
  const [imageTick, setImageTick] = useState(0);

  useSerialPolling(async () => {
    const [nextCameras, nextModel, nextCrosswalks] = await Promise.all([
      fetchRemoteCameraStatus(), fetchInferenceStatus(), fetchCrosswalks(),
    ]);
    setCameras(nextCameras);
    setModel(nextModel);
    setCrosswalks(nextCrosswalks);
    setSourceId((current) => nextCameras.cameras.some((camera) => camera.source_id === current)
      ? current : nextCameras.active_source_id ?? nextCameras.cameras[0]?.source_id ?? "");
  }, 2000, { onError: (reason) => setError(errorMessage(reason)) });

  useEffect(() => {
    setFrame(null);
    setImageTick(0);
    setError(null);
  }, [sourceId, model?.active_model_id]);

  useSerialPolling(async () => {
    if (!sourceId) return;
    const next = await fetchCameraInference(sourceId);
    if (next.source_id !== sourceId) return;
    setFrame(next.frame);
    setError(next.error);
    setImageTick(Date.now());
  }, 500, { enabled: sourceId.length > 0, restartKey: sourceId,
    onError: (reason) => { setFrame(null); setError(errorMessage(reason)); } });

  const camera = cameras?.cameras.find((item) => item.source_id === sourceId);
  const hasFeed = Boolean(camera?.stream_connected) || Boolean(
    cameraStatus?.active_source_id === sourceId && cameraStatus.frame_available && !cameraStatus.stale,
  );
  const displayedFrame = model?.model_loaded && frame?.source_id === sourceId && hasFeed ? frame : null;
  const detections = useMemo(() => displayedFrame?.detections ?? [], [displayedFrame]);
  const regions = useMemo(() => cameraRegions(crosswalks, sourceId), [crosswalks, sourceId]);
  const counts = useMemo(() => displayedFrame
    ? regionClassCounts(regions, detections, displayedFrame.image_width, displayedFrame.image_height)
    : regionClassCounts(regions, [], 1280, 720), [regions, detections, displayedFrame]);
  const labels = useMemo(() => Array.from(new Set(detections.map((item) => item.class_name))).sort(), [detections]);

  useEffect(() => onDetectionCountChange(detections.length), [detections.length, onDetectionCountChange]);

  const imageUrl = displayedFrame?.source_frame_number
    ? inferredFrameUrl(sourceId, displayedFrame.source_frame_number, displayedFrame.timestamp_ms)
    : cameraPreviewUrl(sourceId, imageTick);

  return (
    <div className="live-layout">
      <section className="panel live-panel">
        <div className="panel-header">
          <div>
            <h2>Camera AI Preview</h2>
            <p className="placeholder-copy">Monitor any saved camera without changing global inference or camera selection.</p>
          </div>
          <button className="primary" onClick={onRefresh} disabled={refreshing}>{refreshing ? "Refreshing..." : "Refresh context"}</button>
        </div>
        <div className="form-grid">
          <label>Preview camera
            <select value={sourceId} onChange={(event) => setSourceId(event.target.value)}>
              {cameras?.cameras.length ? cameras.cameras.map((item) => (
                <option key={item.source_id} value={item.source_id}>{item.source_id} ({item.kind})</option>
              )) : <option value="">No registered cameras</option>}
            </select>
          </label>
        </div>
        <div className="live-canvas-shell">
          {sourceId && hasFeed ? (
            <CameraDetectionView
              cameraStatus={cameraStatus}
              frame={displayedFrame}
              detections={detections}
              zones={regions}
              showBoxes={showBoxes}
              showLabels={showLabels}
              showZones={showRegions}
              imageUrlOverride={imageUrl}
              isAvailable={true}
            />
          ) : (
            <div className="live-camera-empty">
              <strong>No current camera feed</strong>
              <span>Connect or start the selected camera in Camera Settings.</span>
            </div>
          )}
        </div>
        <div className="live-inference-meta wrap-row">
          <span>Camera <strong>{sourceId || "none"}</strong></span>
          <span>Status <strong>{hasFeed ? "Connected" : "Unavailable"}</strong></span>
          <span>Model <strong>{model?.active_model_id ?? "Not loaded"}</strong></span>
          <span>Frame <strong>{displayedFrame?.source_frame_number ?? "—"}</strong></span>
          <span>Objects <strong>{detections.length}</strong></span>
        </div>
        <div className="live-visibility-tools">
          <div className="button-row wrap-row">
            <label className="inline-toggle"><input type="checkbox" checked={showBoxes} onChange={(event) => setShowBoxes(event.target.checked)} /> Boxes</label>
            <label className="inline-toggle"><input type="checkbox" checked={showLabels} onChange={(event) => setShowLabels(event.target.checked)} /> Labels</label>
            <label className="inline-toggle"><input type="checkbox" checked={showRegions} onChange={(event) => setShowRegions(event.target.checked)} /> Regions</label>
          </div>
        </div>
        {error && <p className="error-message" role="alert">{error}</p>}
      </section>
      <aside className="side-column">
        <section className="panel compact-panel inference-panel">
          <div className="panel-header"><h2>AI status</h2></div>
          <div className="camera-status-list inference-status-list">
            <div><span>Running model</span><strong>{model?.active_model_id ?? "None"}</strong></div>
            <div><span>Inference</span><strong>{model?.backend_available ? "Available" : "Unavailable"}</strong></div>
            <div><span>Last latency</span><strong>{model?.last_latency_ms == null ? "n/a" : `${model.last_latency_ms.toFixed(1)} ms`}</strong></div>
          </div>
          <p className="small-note">Model selection, detection confidence and inference interval are configured only in AI Models.</p>
        </section>
        <section className="panel compact-panel inference-panel">
          <div className="panel-header"><h2>Region object counts</h2></div>
          <p className="small-note">Current objects per class in this camera's regions, using each detection box's bottom-center. Overlapping regions count each object once.</p>
          <div className="table-scroll">
            <table className="data-table">
              <thead><tr><th>Region</th>{labels.map((label) => <th key={label}>{label}</th>)}</tr></thead>
              <tbody>{regions.map((region) => (
                <tr key={region.id}><td>{region.label}</td>
                  {labels.map((label) => <td key={label}>{counts[region.id]?.[label] ?? 0}</td>)}
                </tr>
              ))}</tbody>
            </table>
          </div>
          {regions.length === 0 && <p className="small-note">No regions assigned to this camera.</p>}
          {regions.length > 0 && labels.length === 0 && <p className="small-note">No current detections.</p>}
        </section>
      </aside>
      <section className="panel bottom-panel full-span">
        <div className="panel-header"><h2>Detected objects</h2></div>
        <DetectionTable detections={detections} />
      </section>
    </div>
  );
}
