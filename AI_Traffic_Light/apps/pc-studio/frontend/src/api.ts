import type { BackendHealth, DetectionFrame, RecentLog, SmokeStatus, TrafficState, Zone } from "./types";
import { mockFrame, mockTrafficState, mockZones } from "./mockData";
import { requestJson } from "./lib/apiClient";

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
  version: "0_1_0",
  mode: "frontend_fallback",
  safe_mode: true,
  message: "Backend is not connected. Frontend is using local fallback mock data.",
};

const fallbackSmokeStatus: SmokeStatus = {
  version: "0_1_0",
  mode: "frontend_fallback",
  ready_for: ["frontend_layout_test", "mock_gui_review"],
  not_ready_for: ["real_camera_capture", "YOLO inference", "training", "physical_traffic_light_control"],
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
