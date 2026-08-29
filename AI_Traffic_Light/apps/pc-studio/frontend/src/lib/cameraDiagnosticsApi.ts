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
  duration_seconds?: number;
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
  load_ladder: CameraLoadPhase[];
  contention_phase: CameraLoadPhase;
  managed_phase: CameraManagedPhase;
  device: Record<string, unknown>;
  state_restored: boolean;
  restore_error: string | null;
  diagnostic_target_fps: number;
  diagnostic_load_targets: number[];
  prototype_only: boolean;
};

export async function runCameraDiagnostics(): Promise<CameraDiagnosticReport> {
  return requestJsonStrict<CameraDiagnosticReport>(`${API_BASE}/api/camera/diagnostics/run`, {
    method: "POST",
  });
}
