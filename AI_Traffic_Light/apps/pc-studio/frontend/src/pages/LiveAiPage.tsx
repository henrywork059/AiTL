import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  fetchInferenceStatus,
  fetchLiveDetections,
  loadLatestInferenceModel,
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
  const autoLoadAttempted = useRef(false);

  const refreshInferenceStatus = useCallback(async () => {
    const nextStatus = await fetchInferenceStatus();
    setInferenceStatus(nextStatus);
    return nextStatus;
  }, []);

  const loadLatest = useCallback(async () => {
    setLoadingModel(true);
    setInferenceError(null);
    try {
      const nextStatus = await loadLatestInferenceModel();
      setInferenceStatus(nextStatus);
      setLiveFrame(null);
    } catch (error) {
      setInferenceError(errorMessage(error));
      await refreshInferenceStatus();
    } finally {
      setLoadingModel(false);
    }
  }, [refreshInferenceStatus]);

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
      if (
        !autoLoadAttempted.current
        && !status.model_loaded
        && status.backend_available
        && status.available_model_count > 0
      ) {
        autoLoadAttempted.current = true;
        setLoadingModel(true);
        try {
          const loaded = await loadLatestInferenceModel();
          if (!cancelled) setInferenceStatus(loaded);
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
        const nextFrame = await fetchLiveDetections();
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
  }, [inferenceStatus?.model_loaded, inferenceStatus?.active_model_id, cameraStatus?.frame_available]);

  const effectiveConfidenceThreshold = Math.max(confidenceThreshold, inferenceStatus?.confidence_floor ?? 0.1);
  const liveDetections = useMemo(
    () => liveFrame?.detections.filter((detection) => detection.confidence >= effectiveConfidenceThreshold) ?? [],
    [liveFrame, effectiveConfidenceThreshold],
  );
  const hasCameraFrame = Boolean(cameraStatus?.frame_available);
  const displayedDetections = hasCameraFrame ? liveDetections : mockDetections;

  useEffect(() => {
    onDetectionCountChange(displayedDetections.length);
  }, [displayedDetections.length, onDetectionCountChange]);

  const modeLabel = hasCameraFrame
    ? inferenceStatus?.model_loaded ? "trained model live" : "camera / model idle"
    : "mock fallback";

  return (
    <div className="live-layout">
      <section className="panel live-panel">
        <div className="panel-header">
          <div>
            <h2>Live detection canvas</h2>
            <p className="placeholder-copy">
              {hasCameraFrame
                ? "Current receiver/simulation frame with trained YOLO detections overlaid in original image coordinates."
                : "No camera frame is available, so the original mock scene remains visible as a fallback."}
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
          <CameraDetectionView cameraStatus={cameraStatus} frame={liveFrame} detections={liveDetections} />
        ) : mockFrame ? (
          <LiveView frame={mockFrame} detections={mockDetections} zones={zones} />
        ) : (
          <p>Loading view...</p>
        )}

        <div className="live-inference-meta">
          <span>Camera: <strong>{cameraStatus?.active_source_id ?? "none"}</strong></span>
          <span>Frame: <strong>{inferenceStatus?.last_frame_number ?? cameraStatus?.frame_number ?? 0}</strong></span>
          <span>Visible detections: <strong>{displayedDetections.length}</strong></span>
          <span>Model: <strong>{inferenceStatus?.active_model_id ?? "not loaded"}</strong></span>
        </div>
      </section>

      <aside className="side-column">
        <InferencePanel
          status={inferenceStatus}
          confidenceThreshold={confidenceThreshold}
          onConfidenceChange={onConfidenceChange}
          onLoadLatest={() => void loadLatest()}
          onUnload={() => void unload()}
          loadingModel={loadingModel}
          error={inferenceError}
        />
        {traffic && <TrafficLight traffic={traffic} />}
        {traffic && <StatusPanel traffic={traffic} />}
        <p className="small-note">Traffic-light decision cards remain mock simulation state in 0_1_4; live detections do not control physical signals.</p>
        <ZonePanel zones={zones} />
      </aside>

      <section className="panel bottom-panel full-span">
        <div className="panel-header">
          <h2>{hasCameraFrame ? "Live trained-model detections" : "Mock detection result table"}</h2>
          <span>{displayedDetections.length} visible</span>
        </div>
        <DetectionTable detections={displayedDetections} />
      </section>
    </div>
  );
}
