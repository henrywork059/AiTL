import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  deleteModel,
  fetchInferenceStatus,
  fetchLiveDetections,
  loadInferenceModel,
  loadLatestInferenceModel,
  setDefaultModel,
  unloadInferenceModel,
} from "../api";
import { CameraDetectionView } from "../components/CameraDetectionView";
import { DetectionTable } from "../components/DetectionTable";
import { InferencePanel } from "../components/InferencePanel";
import { LiveView } from "../components/LiveView";
import { StatusPanel } from "../components/StatusPanel";
import { TrafficLight } from "../components/TrafficLight";
import { ZonePanel } from "../components/ZonePanel";
import type {
  CameraStatus,
  Detection,
  DetectionFrame,
  InferenceStatus,
  TrafficState,
  Zone,
} from "../types";
import "./liveInference.css";

type Props = {
  mockFrame: DetectionFrame | null;
  zones: Zone[];
  traffic: TrafficState | null;
  mockDetections: Detection[];
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
  mockFrame,
  zones,
  traffic,
  mockDetections,
  cameraStatus,
  confidenceThreshold,
  onConfidenceChange,
  onRefresh,
  refreshing,
  onDetectionCountChange,
}: Props) {
  const [inferenceStatus, setInferenceStatus] = useState<InferenceStatus | null>(null);
  const [liveFrame, setLiveFrame] = useState<DetectionFrame | null>(null);
  const [inferenceError, setInferenceError] = useState<string | null>(null);
  const [loadingModel, setLoadingModel] = useState(false);
  const [deletingModel, setDeletingModel] = useState(false);
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  const [showBoxes, setShowBoxes] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [enabledClasses, setEnabledClasses] = useState<string[]>([]);
  const autoLoadAttempted = useRef(false);

  const refreshInferenceStatus = useCallback(async () => {
    const nextStatus = await fetchInferenceStatus();
    setInferenceStatus(nextStatus);
    setSelectedModelId((current) => current ?? nextStatus.active_model_id ?? nextStatus.default_model_id ?? nextStatus.models[0]?.model_id ?? null);
    return nextStatus;
  }, []);

  const loadLatest = useCallback(async () => {
    setLoadingModel(true);
    setInferenceError(null);
    try {
      const nextStatus = await loadLatestInferenceModel();
      setInferenceStatus(nextStatus);
      setSelectedModelId(nextStatus.active_model_id ?? nextStatus.default_model_id ?? nextStatus.models[0]?.model_id ?? null);
      setLiveFrame(null);
    } catch (error) {
      setInferenceError(errorMessage(error));
      await refreshInferenceStatus();
    } finally {
      setLoadingModel(false);
    }
  }, [refreshInferenceStatus]);

  const loadSelected = useCallback(async () => {
    setLoadingModel(true);
    setInferenceError(null);
    try {
      const nextStatus = await loadInferenceModel(selectedModelId);
      setInferenceStatus(nextStatus);
      setSelectedModelId(nextStatus.active_model_id ?? selectedModelId);
      setLiveFrame(null);
    } catch (error) {
      setInferenceError(errorMessage(error));
      await refreshInferenceStatus();
    } finally {
      setLoadingModel(false);
    }
  }, [refreshInferenceStatus, selectedModelId]);

  const setDefault = useCallback(async () => {
    if (!selectedModelId) return;
    setInferenceError(null);
    try {
      await setDefaultModel(selectedModelId);
      await refreshInferenceStatus();
    } catch (error) {
      setInferenceError(errorMessage(error));
    }
  }, [refreshInferenceStatus, selectedModelId]);

  const deleteSelected = useCallback(async () => {
    if (!selectedModelId) return;
    if (!window.confirm(`Delete trained model ${selectedModelId}? This removes the whole run folder under outputs/training.`)) {
      return;
    }
    setDeletingModel(true);
    setInferenceError(null);
    try {
      const registry = await deleteModel(selectedModelId);
      const nextSelection = registry.default_model_id ?? registry.active_model_id ?? registry.models[0]?.model_id ?? null;
      setSelectedModelId(nextSelection);
      const nextStatus = await fetchInferenceStatus();
      setInferenceStatus(nextStatus);
      setLiveFrame(null);
    } catch (error) {
      setInferenceError(errorMessage(error));
    } finally {
      setDeletingModel(false);
    }
  }, [selectedModelId]);

  const unload = useCallback(async () => {
    setLoadingModel(true);
    setInferenceError(null);
    try {
      setInferenceStatus(await unloadInferenceModel());
      setLiveFrame(null);
    } catch (error) {
      setInferenceError(errorMessage(error));
    } finally {
      setLoadingModel(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function initializeInference() {
      const status = await fetchInferenceStatus();
      if (cancelled) return;
      setInferenceStatus(status);
      setSelectedModelId(status.active_model_id ?? status.default_model_id ?? status.models[0]?.model_id ?? null);
      if (
        !autoLoadAttempted.current
        && !status.model_loaded
        && status.backend_available
        && status.available_model_count > 0
      ) {
        autoLoadAttempted.current = true;
        setLoadingModel(true);
        try {
          const loaded = await loadInferenceModel(status.default_model_id ?? status.models[0]?.model_id ?? null);
          if (!cancelled) {
            setInferenceStatus(loaded);
            setSelectedModelId(loaded.active_model_id ?? status.default_model_id ?? status.models[0]?.model_id ?? null);
          }
        } catch (error) {
          if (!cancelled) setInferenceError(errorMessage(error));
        } finally {
          if (!cancelled) setLoadingModel(false);
        }
      }
    }

    void initializeInference();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const timerId = window.setInterval(() => void refreshInferenceStatus(), 2000);
    return () => window.clearInterval(timerId);
  }, [refreshInferenceStatus]);

  useEffect(() => {
    if (!inferenceStatus?.model_loaded || !cameraStatus?.frame_available) {
      setLiveFrame(null);
      return undefined;
    }

    let cancelled = false;
    let timerId: number | undefined;

    async function pollDetections() {
      try {
        const nextFrame = await fetchLiveDetections(confidenceThreshold);
        if (!cancelled) {
          setLiveFrame(nextFrame);
          setInferenceError(null);
        }
      } catch (error) {
        if (!cancelled) setInferenceError(errorMessage(error));
      } finally {
        if (!cancelled) timerId = window.setTimeout(() => void pollDetections(), 500);
      }
    }

    void pollDetections();
    return () => {
      cancelled = true;
      if (timerId !== undefined) window.clearTimeout(timerId);
    };
  }, [inferenceStatus?.model_loaded, inferenceStatus?.active_model_id, cameraStatus?.frame_available, confidenceThreshold]);

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
  const displayedDetections = hasCameraFrame ? liveDetections : mockDetections;

  useEffect(() => {
    onDetectionCountChange(displayedDetections.length);
  }, [displayedDetections.length, onDetectionCountChange]);

  const modeLabel = hasCameraFrame
    ? inferenceStatus?.model_loaded ? "trained model live" : "camera / model idle"
    : "fallback scene";

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
            <h2>Live detection canvas</h2>
            <p className="placeholder-copy">
              {hasCameraFrame
                ? "Current receiver/simulation frame with trained YOLO detections overlaid in original image coordinates."
                : "No camera frame is available, so the local fallback scene remains visible."}
            </p>
          </div>
          <div className="button-row">
            <span className={`status-pill ${inferenceStatus?.model_loaded ? "status-implemented" : "status-planned"}`}>
              {modeLabel}
            </span>
            <button onClick={onRefresh} disabled={refreshing}>{refreshing ? "Refreshing..." : "Refresh"}</button>
          </div>
        </div>

        {hasCameraFrame ? (
          <CameraDetectionView
            cameraStatus={cameraStatus}
            frame={liveFrame}
            detections={liveDetections}
            showBoxes={showBoxes}
            showLabels={showLabels}
          />
        ) : mockFrame ? (
          <LiveView frame={mockFrame} detections={mockDetections} zones={zones} />
        ) : (
          <p>Loading view...</p>
        )}

        <div className="live-inference-meta wrap-row">
          <span>Camera: <strong>{cameraStatus?.active_source_id ?? "none"}</strong></span>
          <span>Frame: <strong>{inferenceStatus?.last_frame_number ?? cameraStatus?.frame_number ?? 0}</strong></span>
          <span>Raw detections: <strong>{rawLiveDetections.length}</strong></span>
          <span>Visible detections: <strong>{displayedDetections.length}</strong></span>
          <span>Model: <strong>{inferenceStatus?.active_model_id ?? "not loaded"}</strong></span>
        </div>

        {hasCameraFrame && (
          <div className="live-visibility-tools">
            <div className="button-row wrap-row">
              <label className="inline-toggle"><input type="checkbox" checked={showBoxes} onChange={(event) => setShowBoxes(event.target.checked)} /> Show boxes</label>
              <label className="inline-toggle"><input type="checkbox" checked={showLabels} onChange={(event) => setShowLabels(event.target.checked)} /> Show labels</label>
            </div>
            <div className="class-filter-group">
              <strong>Visible classes</strong>
              {liveClassOptions.length === 0 ? (
                <span className="small-note">No returned classes for the current frame.</span>
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
        <InferencePanel
          status={inferenceStatus}
          selectedModelId={selectedModelId}
          onSelectedModelChange={setSelectedModelId}
          confidenceThreshold={confidenceThreshold}
          onConfidenceChange={onConfidenceChange}
          onLoadSelected={() => void loadSelected()}
          onLoadLatest={() => void loadLatest()}
          onSetDefault={() => void setDefault()}
          onDeleteSelected={() => void deleteSelected()}
          onUnload={() => void unload()}
          loadingModel={loadingModel}
          deletingModel={deletingModel}
          error={inferenceError}
        />
        {traffic && <TrafficLight traffic={traffic} />}
        {traffic && <StatusPanel traffic={traffic} />}
        <p className="small-note">Traffic decision cards now use zone-aware simulation state in 0_1_7; they remain disconnected from physical traffic signals.</p>
        <ZonePanel zones={zones} />
      </aside>

      <section className="panel bottom-panel full-span">
        <div className="panel-header">
          <h2>{hasCameraFrame ? "Live trained-model detections" : "Fallback detection result table"}</h2>
          <span>{displayedDetections.length} visible</span>
        </div>
        <DetectionTable detections={displayedDetections} />
      </section>
    </div>
  );
}
