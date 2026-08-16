export type Detection = {
  id: string;
  class_id: number;
  class_name: string;
  confidence: number;
  box_xyxy: [number, number, number, number];
  track_id?: string;
  track_age_frames?: number;
};

export type TrackingTrack = {
  track_id: string;
  class_id: number;
  class_name: string;
  box_xyxy: [number, number, number, number];
  center_xy: [number, number];
  first_seen_ms: number;
  last_seen_ms: number;
  age_frames: number;
  missed_frames: number;
  inside_regions: string[];
};

export type TrackingStatus = {
  session_id: string;
  active_track_count: number;
  active_vehicle_tracks: number;
  active_pedestrian_tracks: number;
  total_tracks_created: number;
  events_recorded: number;
  last_source_id: string | null;
  last_frame_number: number | null;
  tracks: TrackingTrack[];
  prototype_tracker: string;
};

export type DetectionFrame = {
  frame_id: string;
  source_id: string;
  image_width: number;
  image_height: number;
  timestamp_ms: number;
  source_frame_number?: number;
  detections: Detection[];
  tracking?: TrackingStatus;
};

export type ZoneType = "pedestrian_waiting" | "crossing" | "vehicle_queue" | "counting_region" | "counting_line" | "ignore";

export type Zone = {
  id: string;
  type: ZoneType;
  label: string;
  polygon: [number, number][];
};

export type ZoneStatus = {
  zones: Zone[];
  editable: boolean;
  status: string;
  source: "defaults" | "persisted" | string;
  reference_resolution: { width: number; height: number };
  config_path: string;
};

export type RegionCount = {
  pedestrians: number;
  vehicles: number;
  total: number;
};

export type SignalPhaseKey =
  | "vehicle_green"
  | "vehicle_yellow"
  | "all_red_to_pedestrian"
  | "pedestrian_green"
  | "pedestrian_flashing"
  | "all_red_to_vehicle";

export type SignalPhaseTiming = {
  base_seconds: number;
  min_seconds: number;
  max_seconds: number;
};

export type SignalRule = {
  label: string;
  enabled: boolean;
  trigger: string;
  threshold: number;
  persistence_seconds: number;
  action: "extend_current_phase" | "reduce_current_phase" | "hold_current_phase" | "request_next_phase" | "incident_hold";
  adjustment_seconds: number;
  target_phases: SignalPhaseKey[];
  priority: number;
  cooldown_seconds: number;
};

export type SignalProfile = {
  description: string;
  phases: Record<SignalPhaseKey, SignalPhaseTiming>;
  max_cycle_seconds: number;
  stale_data_seconds: number;
  demand_memory_seconds: number;
  rules: Record<string, SignalRule>;
};

export type SignalRulesConfig = {
  schema_version: number;
  mode: "fixed" | "adaptive" | "test";
  dry_run: boolean;
  active_profile: string;
  profiles: Record<string, SignalProfile>;
};

export type SignalRuleStatus = {
  rule_id: string;
  label: string;
  state: "active" | "inactive" | "suppressed" | "unavailable" | string;
  reason: string;
  priority: number;
  trigger: string;
  threshold: number;
  stable_for_seconds: number;
};

export type SignalTestInputs = {
  pedestrians_waiting: number;
  pedestrians_crossing: number;
  vehicles_waiting: number;
  mobility_assistance: boolean;
  incident_person_fallen: boolean;
};

export type SignalStatus = {
  phase_key: string;
  phase: "vehicle_green" | "vehicle_yellow" | "pedestrian_green" | "pedestrian_flashing" | "all_red";
  base_duration_seconds: number;
  effective_duration_seconds: number;
  elapsed_seconds: number;
  seconds_remaining: number;
  next_phase_key: string;
  next_phase: string;
  vehicle_go: boolean;
  pedestrian_walk: boolean;
  pedestrian_clear: boolean;
  mode: "fixed" | "adaptive" | "test";
  dry_run: boolean;
  active_profile: string;
  base_cycle_seconds: number;
  max_cycle_seconds: number;
  data_fresh: boolean;
  fallback_reason: string | null;
  pending_request: string | null;
  incident_hold: boolean;
  active_rules: string[];
  rule_status: SignalRuleStatus[];
  observations: Record<string, unknown>;
  test_inputs: SignalTestInputs;
  prototype_only: boolean;
};

export type SignalRulesPreview = {
  phase_key: SignalPhaseKey;
  phase: string;
  base_duration_seconds: number;
  effective_duration_seconds: number;
  rules: { rule_id: string; label: string; state: string; reason: string }[];
  would_enter_incident_hold: boolean;
  prototype_only: boolean;
};

export type SignalDecisionEvent = {
  timestamp_ms: number;
  event_type: string;
  details: Record<string, unknown>;
};

export type SignalDecisionHistory = {
  events: SignalDecisionEvent[];
  count: number;
  history_path: string;
  prototype_only: boolean;
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
  pedestrians_total?: number;
  vehicles_total?: number;
  decision: string;
  decision_reason: string;
  recommended_phase?: TrafficState["phase"];
  recommended_decision?: string;
  recommended_decision_reason?: string;
  extension_seconds: number;
  data_source?: string;
  evaluated_at_ms?: number | null;
  source_timestamp_ms?: number | null;
  evaluated_frame_number?: number | null;
  zone_counts?: Record<string, number>;
  region_counts?: Record<string, RegionCount>;
  tracking?: TrackingStatus;
  signal_policy?: SignalStatus;
  prototype_only?: boolean;
};

export type TrafficHistoryPoint = {
  recorded_at_ms: number;
  source_timestamp_ms: number;
  source_frame_number: number;
  pedestrians: number;
  vehicles: number;
  phase: string;
  decision: string;
};

export type TrafficRegionSummary = { id: string; label: string; type: ZoneType | string };
export type TrafficPeak = { count: number; recorded_at_ms: number | null };
export type TrafficPhaseChange = { recorded_at_ms: number; from: string; to: string };
export type TrafficBusiestRegion = { id: string; label: string; type: string; average_total: number };

export type TrafficHistorySummary = {
  sample_count: number;
  average_pedestrians: number;
  average_vehicles: number;
  peak_pedestrians: TrafficPeak;
  peak_vehicles: TrafficPeak;
  phase_change_count: number;
  latest_phase_change: TrafficPhaseChange | null;
  busiest_region: TrafficBusiestRegion | null;
};

export type TrafficHistory = {
  recording: boolean;
  sample_interval_ms: number;
  max_samples: number;
  stored_samples: number;
  history_path: string;
  oldest_recorded_at_ms: number | null;
  newest_recorded_at_ms: number | null;
  scope: { region_id: string | null; label: string; type: string };
  minutes: number;
  regions: TrafficRegionSummary[];
  points: TrafficHistoryPoint[];
  summary: TrafficHistorySummary;
};

export type TrafficHistoryClearResult = {
  cleared: boolean;
  removed_samples: number;
  recording: boolean;
  sample_interval_ms: number;
  max_samples: number;
  stored_samples: number;
  history_path: string;
  oldest_recorded_at_ms: number | null;
  newest_recorded_at_ms: number | null;
};

export type TrafficFlowEvent = {
  event_id: string;
  event_type: "line_crossing" | "region_entry" | "region_exit" | string;
  timestamp_ms: number;
  source_frame_number: number;
  track_id: string;
  class_id: number;
  class_name: string;
  line_id?: string;
  line_label?: string;
  region_id?: string;
  region_label?: string;
  region_type?: string;
  direction?: "left_to_right" | "right_to_left" | "top_to_bottom" | "bottom_to_top" | string;
  dwell_ms?: number;
  x: number;
  y: number;
};

export type TrafficFlowBucket = {
  bucket_start_ms: number;
  line_crossings: number;
  vehicles: number;
  pedestrians: number;
  region_entries: number;
  region_exits: number;
};

export type TrafficFlowSummary = {
  unique_passages: number;
  unique_vehicle_passages: number;
  unique_pedestrian_passages: number;
  region_entries: number;
  region_exits: number;
  average_dwell_ms: number;
  average_pedestrian_wait_ms: number;
  direction_counts: Record<string, number>;
  line_counts: Record<string, number>;
  region_average_dwell_ms: Record<string, number>;
  unique_event_tracks: number;
};

export type TrafficFlow = {
  recording: boolean;
  max_events: number;
  stored_events: number;
  flow_path: string;
  oldest_event_at_ms: number | null;
  newest_event_at_ms: number | null;
  minutes: number;
  filters: { line_id: string | null; region_id: string | null; class_name: string | null };
  lines: { id: string; label: string }[];
  regions: { id: string; label: string; type: string }[];
  events: TrafficFlowEvent[];
  buckets: TrafficFlowBucket[];
  summary: TrafficFlowSummary;
};

export type TrafficFlowClearResult = {
  cleared: boolean;
  removed_events: number;
  recording: boolean;
  max_events: number;
  stored_events: number;
  flow_path: string;
  oldest_event_at_ms: number | null;
  newest_event_at_ms: number | null;
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
export type SmokeCheck = { id: string; label: string; status: SmokeCheckStatus; detail: string };
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
  request_id?: string | null;
};

export type ApiConnectionState = {
  status: "checking" | "connected" | "fallback" | "failed";
  message: string;
  checkedAt?: string;
};

export type SimulationDensity = "light" | "normal" | "busy";

export type CameraStatus = {
  mode: "receiver" | "simulation";
  simulation_enabled: boolean;
  simulation_paused: boolean;
  simulation_density: SimulationDensity;
  simulation_signal_phase?: string | null;
  simulation_signal_seconds_remaining?: number | null;
  simulation_signal_cycle_seconds?: number | null;
  simulation_signal_vehicle_go?: boolean;
  simulation_signal_pedestrian_walk?: boolean;
  simulation_signal_mode?: string | null;
  simulation_signal_profile?: string | null;
  simulation_signal_active_rules?: string[];
  frame_available: boolean;
  streaming: boolean;
  active_source_id: string | null;
  resolution: { width: number; height: number } | null;
  content_type: string | null;
  received_at_ms: number | null;
  age_ms: number | null;
  frame_number: number;
  size_bytes: number;
  origin: "upload" | "simulation" | null;
  stale: boolean;
  frame_url: string | null;
  upload_endpoint: string;
};

export type CaptureQualityTag = "unreviewed" | "useful" | "bad";
export type CaptureRecord = {
  capture_id: string;
  session_id: string;
  source_id: string;
  origin: "upload" | "simulation";
  content_type: string;
  width: number;
  height: number;
  source_frame_number: number;
  source_received_at_ms: number;
  captured_at_ms: number;
  size_bytes: number;
  quality_tag: CaptureQualityTag;
  note: string;
  image_path: string;
  metadata_path: string;
};

export type DatasetStatus = {
  active_dataset_id: string;
  session_count: number;
  frame_count: number;
  metadata_count: number;
  capture_enabled: boolean;
  status: "ready" | string;
  dataset_path: string;
  last_capture: CaptureRecord | null;
};

export type LabelClass = { id: number; name: string; category: string };
export type DatasetLabelBox = { class_id: number; class_name: string; box_xyxy: [number, number, number, number] };
export type CaptureSummary = CaptureRecord & { labeled: boolean; label_count: number; image_url: string };
export type DatasetCaptureList = { captures: CaptureSummary[]; total: number; classes: LabelClass[] };
export type CaptureDeleteResult = {
  capture_id: string;
  session_id: string;
  deleted: boolean;
  deleted_paths: string[];
  cleanup_pending: boolean;
  training_dataset: TrainingDatasetStatus;
};
export type CaptureLabelDocument = {
  capture_id: string;
  session_id: string;
  image_path: string;
  width: number;
  height: number;
  reviewed: boolean;
  updated_at_ms: number | null;
  labels: DatasetLabelBox[];
};

export type TrainingDatasetStatus = {
  ready: boolean;
  stale: boolean;
  dataset_yaml: string;
  labeled_frame_count: number;
  eligible_frame_count: number;
  excluded_bad_count: number;
  label_box_count: number;
  train_count: number;
  val_count: number;
  generated_at_ms: number | null;
  classes: LabelClass[];
  message: string;
};

export type TrainingConfig = {
  dataset_yaml: string;
  base_model: string;
  epochs: number;
  image_size: number;
  batch: number;
  device: string;
  patience: number;
};

export type TrainingMetricPoint = {
  epoch: number;
  fitness: number | null;
  best_fitness: number | null;
  map50_95: number | null;
  map50: number | null;
  train_loss: number | null;
  val_loss: number | null;
};

export type EarlyStoppingState = {
  enabled: boolean;
  patience: number;
  epochs_without_improvement: number;
  best_epoch: number | null;
  best_fitness: number | null;
  converged: boolean;
  stopped_early: boolean;
};

export type TrainingStatus = {
  training_available: boolean;
  backend: string;
  active_run_id: string | null;
  progress: number;
  status: "idle" | "running" | "completed" | "early_stopped" | "failed" | string;
  message: string;
  started_at_ms: number | null;
  finished_at_ms: number | null;
  config: TrainingConfig | null;
  output_path: string | null;
  best_model_path: string | null;
  error: string | null;
  dataset_root: string;
  requires_labeled_dataset: boolean;
  install_command: string;
  history: TrainingMetricPoint[];
  completed_epochs: number;
  early_stopping: EarlyStoppingState;
};

export type RuntimeSettings = {
  default_confidence: number;
  live_poll_interval_ms: number;
  training_patience: number;
  log_level: "DEBUG" | "INFO" | "WARNING" | "ERROR";
};

export type InferenceModelSummary = {
  model_id: string;
  model_path: string;
  modified_at_ms: number;
  size_bytes: number;
  run_path: string;
  is_latest: boolean;
  is_default: boolean;
  is_active: boolean;
};

export type ModelRegistryStatus = {
  default_model_id: string | null;
  active_model_id: string | null;
  total: number;
  models: InferenceModelSummary[];
};

export type InferenceStatus = {
  model_loaded: boolean;
  active_model_id: string | null;
  active_model_path: string | null;
  loaded_at_ms: number | null;
  last_latency_ms: number | null;
  last_frame_number: number | null;
  error: string | null;
  backend: string;
  backend_available: boolean;
  available_model_count: number;
  latest_model_path: string | null;
  default_model_id: string | null;
  default_model_path: string | null;
  active_is_latest: boolean;
  confidence_floor: number;
  default_confidence: number;
  models: InferenceModelSummary[];
};
