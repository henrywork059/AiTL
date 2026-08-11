export type Detection = {
  id: string;
  class_id: number;
  class_name: string;
  confidence: number;
  box_xyxy: [number, number, number, number];
};

export type DetectionFrame = {
  frame_id: string;
  source_id: string;
  image_width: number;
  image_height: number;
  timestamp_ms: number;
  detections: Detection[];
};

export type Zone = {
  id: string;
  type: "pedestrian_waiting" | "crossing" | "vehicle_queue" | "ignore" | string;
  label: string;
  polygon: [number, number][];
};

export type TrafficState = {
  phase:
    | "vehicle_green"
    | "vehicle_yellow"
    | "pedestrian_green"
    | "pedestrian_flashing"
    | "all_red";
  pedestrians_waiting: number;
  pedestrians_crossing: number;
  vehicles_waiting: number;
  decision: string;
  decision_reason: string;
  extension_seconds: number;
};

export type BackendHealth = {
  status: string;
  app: string;
  version: string;
  mode: string;
  safe_mode: boolean;
  message: string;
};

export type SmokeCheckStatus = "pass" | "warn" | "fail";

export type SmokeCheck = {
  id: string;
  label: string;
  status: SmokeCheckStatus;
  detail: string;
};

export type SmokeStatus = {
  version: string;
  mode: string;
  ready_for: string[];
  not_ready_for: string[];
  checks: SmokeCheck[];
  endpoints: string[];
  summary: {
    mock_frame_id: string;
    mock_detection_count: number;
    mock_zone_count: number;
    mock_traffic_phase: string;
  };
};

export type RecentLog = {
  timestamp?: string;
  level: "debug" | "info" | "warning" | "error" | string;
  code: string;
  scope?: string;
  message: string;
};

export type ApiConnectionState = {
  status: "checking" | "connected" | "fallback" | "failed";
  message: string;
  checkedAt?: string;
};
