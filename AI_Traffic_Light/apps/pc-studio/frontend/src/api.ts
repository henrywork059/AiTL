import type {
  BackendHealth,
  CameraStatus,
  CaptureDeleteResult,
  CaptureLabelDocument,
  CaptureQualityTag,
  CaptureRecord,
  DatasetCaptureList,
  DatasetLabelBox,
  DatasetStatus,
  DetectionFrame,
  InferenceStatus,
  ModelRegistryStatus,
  RecentLog,
  RuntimeSettings,
  SimulationDensity,
  SmokeStatus,
  TrafficHistory,
  TrafficHistoryClearResult,
  TrafficState,
  TrainingConfig,
  TrainingDatasetStatus,
  TrainingStatus,
  Zone,
  ZoneStatus,
} from "./types";
import { PROJECT_VERSION } from "./constants/projectVersion";
import { mockFrame, mockTrafficState, mockZones } from "./mockData";
import { requestJson, requestJsonStrict } from "./lib/apiClient";

const configuredApiBase = import.meta.env.VITE_API_BASE_URL;
export const API_BASE = typeof configuredApiBase === "string" && configuredApiBase.length > 0
  ? configuredApiBase
  : "http://127.0.0.1:8000";

type ZonesResponse = {
  zones: Zone[];
};

type LogsResponse = {
  logs: RecentLog[];
};

const fallbackHealth: BackendHealth = {
  status: "fallback",
  app: "pc-studio-backend",
  version: PROJECT_VERSION,
  mode: "frontend_fallback",
  safe_mode: true,
  message: "Backend is not connected. Frontend is using local fallback data.",
};

const fallbackSmokeStatus: SmokeStatus = {
  version: PROJECT_VERSION,
  mode: "frontend_fallback",
  ready_for: ["frontend_layout_test"],
  not_ready_for: ["backend_features", "physical_traffic_light_control"],
  checks: [
    {
      id: "frontend.fallback",
      label: "Frontend fallback data",
      status: "warn",
      detail: "The backend did not respond, so only local fallback data is available.",
    },
  ],
  endpoints: ["/health", "/api/smoke/status", "/api/zones/active", "/api/traffic/state"],
  summary: {
    mock_frame_id: mockFrame.frame_id,
    mock_detection_count: mockFrame.detections.length,
    mock_zone_count: mockZones.length,
    mock_traffic_phase: mockTrafficState.phase,
  },
};


const fallbackTrafficHistory: TrafficHistory = {
  recording: false,
  sample_interval_ms: 1000,
  max_samples: 0,
  stored_samples: 0,
  history_path: "outputs/traffic_history/history.jsonl",
  oldest_recorded_at_ms: null,
  newest_recorded_at_ms: null,
  scope: { region_id: null, label: "Whole frame", type: "whole_frame" },
  minutes: 15,
  regions: [],
  points: [],
  summary: {
    sample_count: 0,
    average_pedestrians: 0,
    average_vehicles: 0,
    peak_pedestrians: { count: 0, recorded_at_ms: null },
    peak_vehicles: { count: 0, recorded_at_ms: null },
    phase_change_count: 0,
    latest_phase_change: null,
    busiest_region: null,
  },
};

const fallbackCameraStatus: CameraStatus = {
  mode: "receiver",
  simulation_enabled: false,
  simulation_paused: false,
  simulation_density: "normal",
  frame_available: false,
  streaming: false,
  active_source_id: null,
  resolution: null,
  content_type: null,
  received_at_ms: null,
  age_ms: null,
  frame_number: 0,
  size_bytes: 0,
  origin: null,
  stale: false,
  frame_url: null,
  upload_endpoint: "/api/camera/frame?source_id=<camera_id>",
};

const fallbackDatasetStatus: DatasetStatus = {
  active_dataset_id: "captures",
  session_count: 0,
  frame_count: 0,
  metadata_count: 0,
  capture_enabled: false,
  status: "backend_offline",
  dataset_path: "datasets/captures",
  last_capture: null,
};

const fallbackCaptureList: DatasetCaptureList = {
  captures: [],
  total: 0,
  classes: [],
};

const fallbackTrainingDatasetStatus: TrainingDatasetStatus = {
  ready: false,
  stale: false,
  dataset_yaml: "yolo/data.yaml",
  labeled_frame_count: 0,
  eligible_frame_count: 0,
  excluded_bad_count: 0,
  label_box_count: 0,
  train_count: 0,
  val_count: 0,
  generated_at_ms: null,
  classes: [],
  message: "Backend is offline, so the managed training dataset cannot be checked.",
};

const fallbackTrainingStatus: TrainingStatus = {
  training_available: false,
  backend: "ultralytics_yolo_optional",
  active_run_id: null,
  progress: 0,
  status: "backend_offline",
  message: "Backend is offline, so training availability cannot be checked.",
  started_at_ms: null,
  finished_at_ms: null,
  config: null,
  output_path: null,
  best_model_path: null,
  error: null,
  dataset_root: "datasets",
  requires_labeled_dataset: true,
  install_command: "pip install -r requirements-training.txt",
  history: [],
  completed_epochs: 0,
  early_stopping: {
    enabled: true,
    patience: 5,
    epochs_without_improvement: 0,
    best_epoch: null,
    best_fitness: null,
    converged: false,
    stopped_early: false,
  },
};

const fallbackInferenceStatus: InferenceStatus = {
  model_loaded: false,
  active_model_id: null,
  active_model_path: null,
  loaded_at_ms: null,
  last_latency_ms: null,
  last_frame_number: null,
  error: null,
  backend: "ultralytics_yolo",
  backend_available: false,
  available_model_count: 0,
  latest_model_path: null,
  default_model_id: null,
  default_model_path: null,
  active_is_latest: false,
  confidence_floor: 0.01,
  default_confidence: 0.1,
  models: [],
};

const fallbackModelRegistryStatus: ModelRegistryStatus = {
  default_model_id: null,
  active_model_id: null,
  total: 0,
  models: [],
};

export const fallbackRuntimeSettings: RuntimeSettings = {
  default_confidence: 0.10,
  live_poll_interval_ms: 500,
  training_patience: 5,
  log_level: "INFO",
};

const fallbackZoneStatus: ZoneStatus = {
  zones: mockZones,
  editable: false,
  status: "backend_offline",
  source: "fallback",
  reference_resolution: { width: 1280, height: 720 },
  config_path: "config/zones.json",
};

export async function fetchHealth(): Promise<BackendHealth> {
  return requestJson<BackendHealth>(`${API_BASE}/health`, fallbackHealth);
}

export async function fetchSmokeStatus(): Promise<SmokeStatus> {
  return requestJson<SmokeStatus>(`${API_BASE}/api/smoke/status`, fallbackSmokeStatus);
}

export async function fetchMockFrame(): Promise<DetectionFrame> {
  return requestJson<DetectionFrame>(`${API_BASE}/api/mock/frame`, mockFrame);
}

export async function fetchMockZones(): Promise<Zone[]> {
  const data = await requestJson<ZonesResponse>(`${API_BASE}/api/mock/zones`, { zones: mockZones });
  return data.zones;
}

export async function fetchActiveZones(): Promise<ZoneStatus> {
  return requestJson<ZoneStatus>(`${API_BASE}/api/zones/active`, fallbackZoneStatus);
}

export async function saveActiveZones(zones: Zone[]): Promise<ZoneStatus> {
  return requestJsonStrict<ZoneStatus>(`${API_BASE}/api/zones/active`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ zones }),
  });
}

export async function resetActiveZones(): Promise<ZoneStatus> {
  return requestJsonStrict<ZoneStatus>(`${API_BASE}/api/zones/reset`, { method: "POST" });
}

export async function fetchTrafficState(): Promise<TrafficState> {
  return requestJson<TrafficState>(`${API_BASE}/api/traffic/state`, mockTrafficState);
}

export async function fetchTrafficHistory(minutes = 15, regionId: string | null = null): Promise<TrafficHistory> {
  const params = new URLSearchParams({ minutes: String(minutes), limit: "10000" });
  if (regionId) params.set("region_id", regionId);
  return requestJson<TrafficHistory>(`${API_BASE}/api/traffic/history?${params.toString()}`, {
    ...fallbackTrafficHistory,
    minutes,
    scope: regionId
      ? { region_id: regionId, label: regionId, type: "counting_region" }
      : fallbackTrafficHistory.scope,
  });
}

export async function clearTrafficHistory(): Promise<TrafficHistoryClearResult> {
  return requestJsonStrict<TrafficHistoryClearResult>(`${API_BASE}/api/traffic/history`, { method: "DELETE" });
}

export function trafficHistoryExportUrl(minutes = 15, regionId: string | null = null): string {
  const params = new URLSearchParams({ minutes: String(minutes), limit: "50000" });
  if (regionId) params.set("region_id", regionId);
  return `${API_BASE}/api/traffic/history/export.csv?${params.toString()}`;
}

export async function fetchRecentLogs(limit = 100): Promise<RecentLog[]> {
  const data = await requestJson<LogsResponse>(`${API_BASE}/api/logs/recent?limit=${limit}`, {
    logs: [
      {
        timestamp: "frontend",
        level: "warning",
        code: "ATL-FE-FALLBACK-001",
        scope: "api",
        message: "Backend logs unavailable. Frontend fallback log is shown.",
      },
    ],
  });
  return data.logs;
}

export async function fetchRuntimeSettings(): Promise<RuntimeSettings> {
  return requestJson<RuntimeSettings>(`${API_BASE}/api/settings/runtime`, fallbackRuntimeSettings);
}

export async function saveRuntimeSettings(settings: RuntimeSettings): Promise<RuntimeSettings> {
  return requestJsonStrict<RuntimeSettings>(`${API_BASE}/api/settings/runtime`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
}

export async function fetchCameraStatus(): Promise<CameraStatus> {
  return requestJson<CameraStatus>(`${API_BASE}/api/camera/status`, fallbackCameraStatus);
}

export async function setCameraSimulation(enabled: boolean): Promise<CameraStatus> {
  const action = enabled ? "start" : "stop";
  return requestJson<CameraStatus>(
    `${API_BASE}/api/camera/simulation/${action}`,
    fallbackCameraStatus,
    { method: "POST" },
  );
}

export async function setCameraSimulationSettings(input: {
  density?: SimulationDensity;
  paused?: boolean;
}): Promise<CameraStatus> {
  return requestJsonStrict<CameraStatus>(`${API_BASE}/api/camera/simulation/settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function fetchDatasetStatus(): Promise<DatasetStatus> {
  return requestJson<DatasetStatus>(`${API_BASE}/api/dataset/status`, fallbackDatasetStatus);
}

export async function captureLatestFrame(input: {
  session_id: string;
  quality_tag: CaptureQualityTag;
  note: string;
}): Promise<CaptureRecord> {
  return requestJsonStrict<CaptureRecord>(`${API_BASE}/api/dataset/captures`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function fetchDatasetCaptures(): Promise<DatasetCaptureList> {
  return requestJson<DatasetCaptureList>(`${API_BASE}/api/dataset/captures?limit=500`, fallbackCaptureList);
}

export async function deleteDatasetCapture(captureId: string): Promise<CaptureDeleteResult> {
  return requestJsonStrict<CaptureDeleteResult>(
    `${API_BASE}/api/dataset/captures/${encodeURIComponent(captureId)}`,
    { method: "DELETE" },
  );
}

export function captureImageUrl(captureId: string): string {
  return `${API_BASE}/api/dataset/captures/${encodeURIComponent(captureId)}/image`;
}

export async function fetchCaptureLabels(captureId: string): Promise<CaptureLabelDocument> {
  return requestJsonStrict<CaptureLabelDocument>(
    `${API_BASE}/api/dataset/captures/${encodeURIComponent(captureId)}/labels`,
  );
}

export async function saveCaptureLabels(captureId: string, labels: DatasetLabelBox[]): Promise<CaptureLabelDocument> {
  return requestJsonStrict<CaptureLabelDocument>(
    `${API_BASE}/api/dataset/captures/${encodeURIComponent(captureId)}/labels`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        labels: labels.map((label) => ({ class_id: label.class_id, box_xyxy: label.box_xyxy })),
      }),
    },
  );
}

export async function fetchTrainingDatasetStatus(): Promise<TrainingDatasetStatus> {
  return requestJson<TrainingDatasetStatus>(
    `${API_BASE}/api/dataset/training-dataset/status`,
    fallbackTrainingDatasetStatus,
  );
}

export async function buildTrainingDataset(validationFraction = 0.2): Promise<TrainingDatasetStatus> {
  return requestJsonStrict<TrainingDatasetStatus>(`${API_BASE}/api/dataset/training-dataset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ validation_fraction: validationFraction }),
  });
}

export async function fetchTrainingStatus(): Promise<TrainingStatus> {
  return requestJson<TrainingStatus>(`${API_BASE}/api/training/status`, fallbackTrainingStatus);
}

export async function startTraining(config: TrainingConfig): Promise<TrainingStatus> {
  return requestJsonStrict<TrainingStatus>(`${API_BASE}/api/training/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
}

export async function fetchInferenceStatus(): Promise<InferenceStatus> {
  return requestJson<InferenceStatus>(`${API_BASE}/api/inference/status`, fallbackInferenceStatus);
}

export async function loadLatestInferenceModel(): Promise<InferenceStatus> {
  return requestJsonStrict<InferenceStatus>(`${API_BASE}/api/inference/load-latest`, { method: "POST" });
}

export async function loadInferenceModel(modelId: string | null): Promise<InferenceStatus> {
  return requestJsonStrict<InferenceStatus>(`${API_BASE}/api/inference/load`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model_id: modelId }),
  });
}

export async function unloadInferenceModel(): Promise<InferenceStatus> {
  return requestJsonStrict<InferenceStatus>(`${API_BASE}/api/inference/unload`, { method: "POST" });
}

export async function fetchModelRegistry(): Promise<ModelRegistryStatus> {
  return requestJson<ModelRegistryStatus>(`${API_BASE}/api/models`, fallbackModelRegistryStatus);
}

export async function setDefaultModel(modelId: string): Promise<ModelRegistryStatus> {
  return requestJsonStrict<ModelRegistryStatus>(`${API_BASE}/api/models/default`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model_id: modelId }),
  });
}

export async function deleteModel(modelId: string): Promise<ModelRegistryStatus> {
  return requestJsonStrict<ModelRegistryStatus>(`${API_BASE}/api/models/${encodeURIComponent(modelId)}`, {
    method: "DELETE",
  });
}

export async function fetchLiveDetections(confidenceThreshold = 0.1): Promise<DetectionFrame> {
  const params = new URLSearchParams({ confidence: String(confidenceThreshold) });
  return requestJsonStrict<DetectionFrame>(`${API_BASE}/api/inference/detections?${params.toString()}`);
}

export function inferredFrameUrl(sourceId: string, frameNumber: number, timestampMs: number): string {
  const params = new URLSearchParams({
    source_id: sourceId,
    frame_number: String(frameNumber),
    t: String(timestampMs),
  });
  return `${API_BASE}/api/inference/frame?${params.toString()}`;
}
