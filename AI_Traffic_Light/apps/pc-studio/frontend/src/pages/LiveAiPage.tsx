import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchInferenceStatus, fetchLiveDetections } from "../api";
import { CameraDetectionView } from "../components/CameraDetectionView";
import { DetectionTable } from "../components/DetectionTable";
import { useSerialPolling } from "../lib/useSerialPolling";
import type {
  CameraStatus,
  DetectionFrame,
  InferenceStatus,
  Zone,
} from "../types";
import "./liveInference.css";

type Props = {
  zones: Zone[];
  cameraStatus: CameraStatus | null;
  confidenceThreshold: number;
  onConfidenceChange: (value: number) => void;
  onRefresh: () => void;
  refreshing: boolean;
  onDetectionCountChange: (count: number) => void;
};

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Live inference request failed.";
}

export function LiveAiPage({
  zones,
  cameraStatus,
  confidenceThreshold,
  onConfidenceChange,
  onRefresh,
  refreshing,
  onDetectionCountChange,
}: Props) {
  const [inferenceStatus, setInferenceStatus] = useState<InferenceStatus | null>(null);
  const [inferenceInitialized, setInferenceInitialized] = useState(false);
  const [liveFrame, setLiveFrame] = useState<DetectionFrame | null>(null);
  const [inferenceError, setInferenceError] = useState<string | null>(null);
  const [showBoxes, setShowBoxes] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [showZones, setShowZones] = useState(true);
  const [enabledClasses, setEnabledClasses] = useState<string[]>([]);

  const refreshInferenceStatus = useCallback(async () => {
    const nextStatus = await fetchInferenceStatus();
    setInferenceStatus(nextStatus);
    return nextStatus;
  }, []);

  useEffect(() => {
    let cancelled = false;
    void fetchInferenceStatus()
      .then((status) => {
        if (!cancelled) setInferenceStatus(status);
      })
      .catch((error) => {
        if (!cancelled) setInferenceError(errorMessage(error));
      })
      .finally(() => {
        if (!cancelled) setInferenceInitialized(true);
      });
    return () => { cancelled = true; };
  }, []);

  useSerialPolling(
    async () => {
      await refreshInferenceStatus();
    },
    2000,
    {
      enabled: inferenceInitialized,
      immediate: false,
      onError: (error) => setInferenceError(errorMessage(error)),
    },
  );

  useEffect(() => {
    if (!inferenceStatus?.model_loaded || !cameraStatus?.frame_available) {
      setLiveFrame(null);
    }
  }, [inferenceStatus?.model_loaded, cameraStatus?.frame_available]);

  useSerialPolling(
    async () => {
      const nextFrame = await fetchLiveDetections(confidenceThreshold);
      setLiveFrame(nextFrame);
      setInferenceError(null);
    },
    500,
    {
      enabled: Boolean(inferenceStatus?.model_loaded && cameraStatus?.frame_available),
      restartKey: [
        inferenceStatus?.active_model_id ?? "",
        cameraStatus?.frame_available ?? false,
        confidenceThreshold,
      ].join("|"),
      onError: (error) => setInferenceError(errorMessage(error)),
    },
  );

  const rawLiveDetections = liveFrame?.detections ?? [];
  const liveClassOptions = useMemo(
    () => Array.from(new Set(rawLiveDetections.map((detection) => detection.class_name))).sort(),
    [rawLiveDetections],
  );

  useEffect(() => {
    setEnabledClasses((current) => {
      const next = liveClassOptions.filter((className) => current.includes(className));
      return next.length > 0 || liveClassOptions.length === 0 ? next : liveClassOptions;
    });
  }, [liveClassOptions]);

  const effectiveClasses = enabledClasses.length > 0 ? enabledClasses : liveClassOptions;
  const liveDetections = useMemo(
    () => rawLiveDetections.filter((detection) => effectiveClasses.includes(detection.class_name)),
    [rawLiveDetections, effectiveClasses],
  );
  const hasCameraFrame = Boolean(cameraStatus?.frame_available);
  const displayedDetections = hasCameraFrame && inferenceStatus?.model_loaded ? liveDetections : [];

  useEffect(() => {
    onDetectionCountChange(displayedDetections.length);
  }, [displayedDetections.length, onDetectionCountChange]);

  const modeLabel = hasCameraFrame
    ? inferenceStatus?.model_loaded ? "model running" : "model idle"
    : "camera unavailable";

  function toggleClass(className: string) {
    setEnabledClasses((current) => current.includes(className)
      ? current.filter((item) => item !== className)
      : [...current, className]);
  }

  return (
    <div className="live-layout">
      <section className="panel live-panel">
        <div className="panel-header">
          <div>
            <h2>Camera AI Preview</h2>
            <p className="placeholder-copy">
              {hasCameraFrame
                ? "Runs the loaded local model on the current camera/simulation frame. Detections use original-image coordinates."
                : "Connect or select a camera in Camera Settings to preview real frames and AI detections."}
            </p>
          </div>
          <div className="button-row">
            <span className={`status-pill ${inferenceStatus?.model_loaded ? "status-implemented" : "status-planned"}`}>
              {modeLabel}
            </span>
            <button className="primary" onClick={onRefresh} disabled={refreshing}>{refreshing ? "Refreshing..." : "Refresh context"}</button>
          </div>
        </div>

        <div className="live-canvas-shell">
          {hasCameraFrame ? (
            <CameraDetectionView
              cameraStatus={cameraStatus}
              frame={liveFrame}
              detections={liveDetections}
              zones={zones}
              showBoxes={showBoxes}
              showLabels={showLabels}
              showZones={showZones}
            />
          ) : (
            <div className="live-camera-empty">
              <strong>No camera preview available</strong>
              <span>Connect a camera in Camera Settings. No synthetic detection results are shown.</span>
            </div>
          )}
        </div>

        <div className="live-inference-meta wrap-row">
          <span>Source <strong>{cameraStatus?.active_source_id ?? "none"}</strong></span>
          <span>Frame <strong>{inferenceStatus?.last_frame_number ?? cameraStatus?.frame_number ?? 0}</strong></span>
          <span>Detected <strong>{rawLiveDetections.length}</strong></span>
          <span>Visible <strong>{displayedDetections.length}</strong></span>
          <span>Model <strong>{inferenceStatus?.active_model_id ?? "not loaded"}</strong></span>
        </div>

        {hasCameraFrame && (
          <div className="live-visibility-tools">
            <div className="button-row wrap-row">
              <label className="inline-toggle"><input type="checkbox" checked={showBoxes} onChange={(event) => setShowBoxes(event.target.checked)} /> Boxes</label>
              <label className="inline-toggle"><input type="checkbox" checked={showLabels} onChange={(event) => setShowLabels(event.target.checked)} /> Labels</label>
              <label className="inline-toggle"><input type="checkbox" checked={showZones} onChange={(event) => setShowZones(event.target.checked)} /> Regions</label>
            </div>
            <div className="class-filter-group">
              <strong>Visible classes</strong>
              {liveClassOptions.length === 0 ? (
                <span className="small-note">No classes were returned for the current frame.</span>
              ) : (
                <div className="button-row wrap-row">
                  {liveClassOptions.map((className) => (
                    <label key={className} className="inline-toggle class-chip">
                      <input
                        type="checkbox"
                        checked={effectiveClasses.includes(className)}
                        onChange={() => toggleClass(className)}
                      />
                      {className}
                    </label>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </section>

      <aside className="side-column">
        <section className="panel compact-panel inference-panel">
          <div className="panel-header">
            <h2>Preview status</h2>
            <span className={`status-pill ${inferenceStatus?.model_loaded ? "status-implemented" : "muted"}`}>
              {inferenceStatus?.model_loaded ? "Model loaded" : "No model loaded"}
            </span>
          </div>
          <div className="camera-status-list inference-status-list">
            <div><span>Camera</span><strong>{cameraStatus?.active_source_id ?? "None"}</strong></div>
            <div><span>Model</span><strong>{inferenceStatus?.active_model_id ?? "None"}</strong></div>
            <div><span>Inference</span><strong>{inferenceStatus?.backend_available ? "Available" : "Unavailable"}</strong></div>
            <div><span>Latency</span><strong>{inferenceStatus?.last_latency_ms != null ? `${inferenceStatus.last_latency_ms.toFixed(1)} ms` : "n/a"}</strong></div>
          </div>
          <label className="control-label inference-threshold">
            Preview confidence: {(confidenceThreshold * 100).toFixed(0)}%
            <input type="range" min={inferenceStatus?.confidence_floor ?? 0.01} max="1" step="0.01"
              value={Math.max(confidenceThreshold, inferenceStatus?.confidence_floor ?? 0.01)}
              onChange={(event) => onConfidenceChange(Number(event.target.value))} />
          </label>
          <p className="small-note">Use AI → AI Models to load, unload or select models and save the default detection confidence. Preview confidence applies to this session.</p>
          {inferenceError && <p className="error-message" role="alert">{inferenceError}</p>}
          {inferenceStatus?.error && <p className="error-message">Backend: {inferenceStatus.error}</p>}
        </section>
      </aside>

      <section className="panel bottom-panel full-span">
        <div className="panel-header">
          <div>
            <h2>Detection results</h2>
            <p className="placeholder-copy">Results after the current confidence and class visibility filters.</p>
          </div>
          <span className="status-pill muted">{displayedDetections.length} visible</span>
        </div>
        <DetectionTable detections={displayedDetections} />
      </section>
    </div>
  );
}
