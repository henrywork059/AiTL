export type JunctionLoadLevel = "unavailable" | "clear" | "light" | "moderate" | "heavy";
export type JunctionEventSeverity = "info" | "attention" | "critical";
export type JunctionWarningSeverity = "info" | "warning" | "critical";

export type JunctionPosition = {
  x: number;
  y: number;
};

export type JunctionConfig = {
  id: string;
  label: string;
  enabled: boolean;
  source_ids: string[];
  primary_source_id: string | null;
  zone_ids: string[];
  signal_profile: string;
  position: JunctionPosition;
};

export type JunctionLink = {
  id: string;
  enabled: boolean;
  source_intersection_id: string;
  destination_intersection_id: string;
  source_approach: string;
  destination_approach: string;
  travel_time_seconds: number;
};

export type JunctionNetworkConfig = {
  schema_version: 1;
  active_intersection_id: string;
  intersections: JunctionConfig[];
  links: JunctionLink[];
};

export type JunctionCameraView = {
  source_id: string;
  kind: "esp32_cam" | "simulation" | "other_source";
  saved: boolean;
  host: string | null;
  selected: boolean;
  connected: boolean;
  device_reachable: boolean;
  streaming: boolean;
  stream_connected: boolean;
  measured_fps: number;
  last_success_at_ms: number | null;
  last_error: string | null;
  state: "streaming" | "online" | "configured" | "offline" | "simulation";
};

export type JunctionEvent = {
  type: string;
  label: string;
  severity: JunctionEventSeverity;
  detail: string | null;
  provenance: string | null;
};

export type JunctionWarning = {
  code: string;
  message: string;
  severity: JunctionWarningSeverity;
  source_id: string | null;
};

export type JunctionLiveSummary = {
  available: boolean;
  pipeline_source_active: boolean;
  source_id: string | null;
  source_mapping_matched: boolean;
  observation_provenance: "ai_detection" | "simulation" | "manual_test" | "unavailable";
  phase: string | null;
  decision: string | null;
  decision_reason: string | null;
  evaluated_at_ms: number | null;
  source_timestamp_ms: number | null;
  vehicle: {
    total: number;
    waiting: number;
    load: JunctionLoadLevel;
  };
  pedestrian: {
    total: number;
    waiting: number;
    crossing: number;
    load: JunctionLoadLevel;
  };
  decision_context: Record<string, unknown> | null;
};

export type JunctionOverviewNode = {
  id: string;
  label: string;
  enabled: boolean;
  active_intersection: boolean;
  position: JunctionPosition;
  source_ids: string[];
  primary_source_id: string | null;
  signal_profile: string;
  cameras: JunctionCameraView[];
  camera_count: number;
  reachable_camera_count: number;
  streaming_camera_count: number;
  live: JunctionLiveSummary;
  events: JunctionEvent[];
  warnings: JunctionWarning[];
  warning_count: number;
  event_count: number;
};

export type JunctionNetworkOverview = {
  schema_version: 1;
  generated_at_ms: number;
  network: JunctionNetworkConfig;
  available_cameras: JunctionCameraView[];
  active_source_id: string | null;
  current_frame_source_id: string | null;
  observation_intersection_id: string;
  observation_provenance: "ai_detection" | "simulation" | "manual_test" | "unavailable";
  source_mapping_matched: boolean;
  simulation_enabled: boolean;
  junctions: JunctionOverviewNode[];
  links: JunctionLink[];
  warnings: JunctionWarning[];
  summary: {
    junction_count: number;
    enabled_junction_count: number;
    link_count: number;
    saved_esp_camera_count: number;
    assigned_esp_camera_count: number;
    reachable_esp_camera_count: number;
    streaming_esp_camera_count: number;
    warning_junction_count: number;
    event_count: number;
    heavy_vehicle_junction_count: number;
    heavy_pedestrian_junction_count: number;
  };
  multi_camera_assignment: boolean;
  simultaneous_multi_junction_inference: boolean;
  prototype_only: boolean;
  scope_note: string;
};
