import type {
  BackendHealth,
  CameraStatus,
  CaptureQualityTag,
  CaptureRecord,
  DatasetStatus,
  DetectionFrame,
  RecentLog,
  SmokeStatus,
  TrafficState,
  TrainingConfig,
  TrainingStatus,
  Zone,
} from "./types";
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
  version: "0_1_2",
  mode: "frontend_fallback",
  safe_mode: true,
  message: "Backend is not connected. Frontend is using local fallback mock data.",
};

const fallbackSmokeStatus: SmokeStatus = {
  version: "0_1_2",
  mode: "frontend_fallback",
  ready_for: ["frontend_layout_test", "mock_gui_review"],
  not_ready_for: ["real_camera_capture", "YOLO inference", "unlabeled_dataset_training", "physical_traffic_light_control"],
  checks: [
    {
      id: "frontend.fallback",
      label: "Frontend fallback data",
      status: "warn",
      detail: "The backend did not respond, but the GUI can still render mock data.",
    },
  ],
  endpoints: ["/health", "/api/smoke/status", "/api/mock/frame", "/api/mock/zones", "/api/traffic/state"],
  summary: {
    mock_frame_id: mockFrame.frame_id,
    mock_detection_count: mockFrame.detections.length,
    mock_zone_count: mockZones.length,
    mock_traffic_phase: mockTrafficState.phase,
  },
};

const fallbackCameraStatus: CameraStatus = {
  mode: "receiver",
  simulation_enabled: false,
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
  const data = await requestJson<ZonesResponse>(`${API_BASE}/api/mock/zones`, {
    zones: mockZones,
  });
  return data.zones;
}

export async function fetchTrafficState(): Promise<TrafficState> {
  return requestJson<TrafficState>(`${API_BASE}/api/traffic/state`, mockTrafficState);
}

export async function fetchRecentLogs(): Promise<RecentLog[]> {
  const data = await requestJson<LogsResponse>(`${API_BASE}/api/logs/recent`, {
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
