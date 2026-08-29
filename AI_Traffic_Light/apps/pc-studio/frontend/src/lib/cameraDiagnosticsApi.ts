import { API_BASE } from "../api";
import { requestJsonStrict } from "./apiClient";

export type CameraDiagnosticCheckStatus = "pass" | "warn" | "fail" | "skip";
export type CameraDiagnosticOverall = "healthy" | "warning" | "failed";
export type CameraDiagnosticConfidence = "high" | "medium" | "low";

export type CameraDiagnosticCheck = {
  id: string;
  label: string;
  status: CameraDiagnosticCheckStatus;
  detail: string;
  metrics: Record<string, unknown>;
};

export type CameraDiagnosticMetrics = {
  control_successes: number;
  control_failures: number;
  control_avg_ms: number | null;
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
  managed_failed_fetches: number;
  managed_reconnects: number;
  managed_session_recoveries: number;
  device_send_failures_delta: number;
  device_deadline_drops_delta: number;
  last_send_errno: number | null;
  last_send_accepted_bytes: number | null;
  last_frame_bytes: number | null;
  send_ewma_ms: number | null;
  wifi_disconnects: number | null;
  wifi_reconnects: number | null;
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
  device: Record<string, unknown>;
  state_restored: boolean;
  restore_error: string | null;
  diagnostic_target_fps: number;
  prototype_only: boolean;
};

export async function runCameraDiagnostics(): Promise<CameraDiagnosticReport> {
  return requestJsonStrict<CameraDiagnosticReport>(`${API_BASE}/api/camera/diagnostics/run`, {
    method: "POST",
  });
}
