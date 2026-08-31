import { API_BASE } from "../api";
import { requestJsonStrict } from "./apiClient";

export type CameraDiagnosticCheckStatus = "pass" | "warn" | "fail" | "skip";
export type CameraDiagnosticOverall = "healthy" | "warning" | "failed";
export type CameraDiagnosticConfidence = "high" | "medium" | "low";
export type CameraDiagnosticFindingSeverity = "critical" | "warning" | "info";

export type CameraDiagnosticCheck = {
  id: string;
  category: "functionality" | "stability" | "bottleneck" | string;
  label: string;
  status: CameraDiagnosticCheckStatus;
  detail: string;
  metrics: Record<string, unknown>;
};

export type CameraLoadPhase = {
  target_fps: number;
  duration_seconds?: number | null;
  frames: number;
  bytes_received?: number;
  throughput_mbps?: number;
  measured_fps: number;
  fps_ratio?: number;
  connections?: number;
  disconnects: number;
  sequence_gaps?: number;
  bad_frames: number;
  payload_avg_bytes?: number;
  payload_min_bytes?: number;
  payload_max_bytes?: number;
  interval_avg_ms?: number | null;
  interval_p50_ms?: number | null;
  interval_p95_ms?: number | null;
  interval_max_ms?: number | null;
  jitter_ms?: number | null;
  stall_intervals?: number;
  status_poll_successes?: number;
  status_poll_failures?: number;
  status_poll_avg_ms?: number | null;
  unexpected_send_failures?: number;
  deadline_drops?: number;
  slow_frames?: number;
  rssi_avg?: number | null;
  rssi_min?: number | null;
  rssi_max?: number | null;
  device_send_ewma_ms?: number | null;
  device_last_capture_ms?: number | null;
  phase_boundary_send_resets?: number;
  errors?: string[];
};

export type CameraManagedPhase = {
  target_fps: number;
  duration_seconds?: number;
  frames: number;
  failed_fetches: number;
  reconnects: number;
  session_recoveries: number;
  measured_fps: number;
  throughput_mbps?: number;
  fps_ratio?: number;
  error?: string | null;
};

export type CameraBottleneckFinding = {
  id: string;
  layer: string;
  severity: CameraDiagnosticFindingSeverity;
  title: string;
  evidence: string;
  impact: string;
  recommendation: string;
};

export type CameraBottleneckAnalysis = {
  primary_bottleneck: string;
  findings: CameraBottleneckFinding[];
  estimated_sustainable_target_fps: number;
  peak_measured_fps: number;
  peak_throughput_mbps: number;
  stability_grade: "stable" | "degraded" | "unstable" | string;
  stability_score: number;
  saved_target_fps: number;
};

export type CameraDiagnosticMetrics = {
  control_successes: number;
  control_failures: number;
  control_avg_ms: number | null;
  control_p50_ms: number | null;
  control_p95_ms: number | null;
  control_max_ms: number | null;
  control_jitter_ms: number | null;
  rssi_avg: number | null;
  rssi_min: number | null;
  rssi_max: number | null;
  wifi_bssid: string | null;
  wifi_channel: number | null;
  direct_clean_frames: number;
  direct_clean_fps: number;
  direct_clean_disconnects: number;
  direct_clean_bad_frames: number;
  direct_polled_frames: number;
  direct_polled_fps: number;
  direct_polled_disconnects: number;
  direct_polled_bad_frames: number;
  status_poll_failures: number;
  managed_frames: number;
  managed_fps: number;
  managed_failed_fetches: number;
  managed_reconnects: number;
  managed_session_recoveries: number;
  device_send_failures_delta: number;
  device_deadline_drops_delta: number;
  phase_boundary_send_resets: number;
  last_send_errno: number | null;
  last_send_accepted_bytes: number | null;
  last_frame_bytes: number | null;
  send_ewma_ms: number | null;
  wifi_disconnects: number | null;
  wifi_reconnects: number | null;
  functionality_score: number;
  stability_score: number;
  stability_grade: string;
  peak_measured_fps: number;
  peak_throughput_mbps: number;
  estimated_sustainable_target_fps: number;
  stability_target_fps: number;
  stability_measured_fps: number;
  stability_interval_p95_ms: number | null;
  stability_interval_max_ms: number | null;
  stability_jitter_ms: number | null;
  stability_stall_intervals: number;
  stability_disconnects: number;
  stability_sequence_gaps: number;
  stability_bad_frames: number;
};

export type CameraCandidateFinding = { code: string; layer: string; confidence: string; evidence: string; action: string };
export type CameraCandidateIsolation = { supported: boolean; primary_candidate: string; findings: CameraCandidateFinding[]; ruled_out: string[]; matrix: Record<string, boolean> };

export type CameraTransportBenchmarkResult = {
  key: string;
  name: string;
  transport: string;
  status: "PASS" | "FAIL" | "SKIP" | string;
  requested_frames: number;
  frames: number;
  bytes_received: number;
  elapsed_ms: number | null;
  measured_fps: number | null;
  completion_ratio: number;
  packet_loss?: number | null;
  detail: string;
  production_candidate: boolean;
  telemetry?: Record<string, unknown>;
};

export type CameraTimingStats = {
  count: number;
  avg: number | null;
  p95: number | null;
  max: number | null;
};

export type CameraPipelineTimingRow = {
  key: string;
  status: string;
  measured_fps: number;
  target_fps: number;
  target_period_ms: number;
  observed_interval_ms: number | null;
  capture_ms: CameraTimingStats;
  send_ms: CameraTimingStats;
  accounted_ms: number;
  unexplained_ms: number;
  accounted_ratio: number | null;
  sample_count: number;
};

export type CameraCaptureTimingProbe = {
  attempts: number;
  successes: number;
  failures: number;
  request_ms: CameraTimingStats;
  esp_capture_ms: CameraTimingStats;
  request_minus_capture_ms: CameraTimingStats;
  records: Array<Record<string, unknown>>;
  errors: string[];
};

export type CameraPipelineTimingAnalysis = {
  candidate_key: string;
  dominant_remaining_stage: string;
  confidence: string;
  target_fps: number;
  target_period_ms: number;
  candidate: CameraPipelineTimingRow;
  direct_plain_send: CameraPipelineTimingRow | null;
  dram_copy_send: CameraPipelineTimingRow | null;
  synthetic_send: CameraPipelineTimingRow | null;
  capture_probe: CameraCaptureTimingProbe;
  accounted_ms: number;
  unexplained_ms: number;
  unexplained_ratio: number | null;
  conclusions: string[];
  next_action: string;
  followup_duration_ms?: number;
};

export type CameraArchitectureMethod = {
  method: string;
  tested: boolean;
  purpose: string;
};

export type CameraArchitectureAnalysis = {
  classification: string;
  confidence: "high" | "medium" | "low" | string;
  target_fps: number;
  manual_mjpeg_fps: number;
  httpd_direct_mjpeg_fps: number;
  cached_mjpeg_fps: number;
  httpd_bulk_mbps: number;
  raw_bulk_nodelay_mbps: number;
  raw_bulk_nagle_mbps: number;
  best_camera_fps: number;
  best_bulk_mbps: number;
  bulk_headroom: string;
  httpd_vs_manual_ratio: number | null;
  cached_vs_direct_ratio: number | null;
  nagle_sensitivity_ratio: number | null;
  reset_reason: string;
  power_evidence: string;
  rssi: number;
  recommended_key: string;
  findings: string[];
  likely_layers: string[];
  methods_assessed: CameraArchitectureMethod[];
  next_action: string;
};

export type CameraTransportBenchmarkReport = {
  schema_version: number;
  benchmark_revision: string;
  firmware: string | null;
  host: string;
  environment_label: string;
  settings: Record<string, unknown>;
  diagnosis: {
    diagnosis_code: string;
    likely_bottleneck: string;
    recommended_key: string | null;
    recommendation: string;
    ranking: Array<{ key: string; name: string; score: number; status: string }>;
  };
  analysis_evidence: {
    hypothesis_ranking?: Array<{ hypothesis: string; confidence: string; evidence: string[] }>;
    comparative_pairs?: Record<string, unknown>;
    architecture_analysis?: CameraArchitectureAnalysis;
  };
  results: CameraTransportBenchmarkResult[];
  pipeline_timing_analysis?: CameraPipelineTimingAnalysis;
  architecture_analysis?: CameraArchitectureAnalysis;
};

export type CameraDiagnosticProgress = {
  status: "idle" | "running" | "completed" | "failed" | string;
  engine: "probing" | "standard" | "transport_benchmark" | "architecture_benchmark" | null | string;
  stage: string;
  current_test: string | null;
  test_index: number | null;
  frame_current: number | null;
  frame_total: number | null;
  detail: string | null;
  last_line: string | null;
  started_at_ms: number | null;
  elapsed_ms: number;
  error: string | null;
  log_tail: string[];
};

export type CameraDiagnosticReport = {
  run_id: string;
  started_at_ms: number;
  duration_ms: number;
  source_id: string;
  host: string;
  overall: CameraDiagnosticOverall;
  diagnosis_code: string;
  title: string;
  summary: string;
  confidence: CameraDiagnosticConfidence;
  likely_causes: string[];
  recommendations: string[];
  checks: CameraDiagnosticCheck[];
  metrics: CameraDiagnosticMetrics;
  functionality: {
    score: number;
    passed: number;
    total: number;
    config_roundtrip: boolean;
    session_lifecycle: boolean;
  };
  stability: {
    grade: string;
    score: number;
    phase: CameraLoadPhase;
  };
  bottleneck_analysis: CameraBottleneckAnalysis;
  candidate_isolation: CameraCandidateIsolation;
  candidate_phases: Record<string, unknown>;
  load_ladder: CameraLoadPhase[];
  contention_phase: CameraLoadPhase;
  managed_phase: CameraManagedPhase;
  device: Record<string, unknown>;
  state_restored: boolean;
  restore_error: string | null;
  diagnostic_target_fps: number;
  diagnostic_load_targets: number[];
  prototype_only: boolean;
  pipeline_timing?: CameraPipelineTimingAnalysis | null;
  architecture_analysis?: CameraArchitectureAnalysis;
  transport_benchmark?: CameraTransportBenchmarkReport;
};

export async function runCameraDiagnostics(): Promise<CameraDiagnosticReport> {
  return requestJsonStrict<CameraDiagnosticReport>(`${API_BASE}/api/camera/diagnostics/run`, {
    method: "POST",
  });
}

export async function fetchCameraDiagnosticProgress(): Promise<CameraDiagnosticProgress> {
  return requestJsonStrict<CameraDiagnosticProgress>(`${API_BASE}/api/camera/diagnostics/progress`);
}
