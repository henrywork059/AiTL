import { API_BASE, fetchCameraStatus } from "../api";
import { requestJsonStrict } from "./apiClient";
import type { CameraStatus } from "../types";

export type RemoteFrameSize = "QQVGA" | "HQVGA" | "QVGA" | "CIF" | "VGA" | "SVGA" | "XGA" | "SXGA" | "UXGA";

export type RemoteCameraSettings = {
  frame_size: RemoteFrameSize;
  jpeg_quality: number;
  brightness: number;
  contrast: number;
  saturation: number;
  special_effect: number;
  awb: boolean;
  awb_gain: boolean;
  wb_mode: number;
  aec: boolean;
  aec2: boolean;
  ae_level: number;
  aec_value: number;
  agc: boolean;
  agc_gain: number;
  gainceiling: number;
  bpc: boolean;
  wpc: boolean;
  raw_gma: boolean;
  lenc: boolean;
  hmirror: boolean;
  vflip: boolean;
  dcw: boolean;
  colorbar: boolean;
};

export const DEFAULT_REMOTE_CAMERA_SETTINGS: RemoteCameraSettings = {
  frame_size: "VGA",
  jpeg_quality: 12,
  brightness: 0,
  contrast: 0,
  saturation: 0,
  special_effect: 0,
  awb: true,
  awb_gain: true,
  wb_mode: 0,
  aec: true,
  aec2: false,
  ae_level: 0,
  aec_value: 300,
  agc: true,
  agc_gain: 0,
  gainceiling: 0,
  bpc: false,
  wpc: true,
  raw_gma: true,
  lenc: true,
  hmirror: false,
  vflip: false,
  dcw: true,
  colorbar: false,
};

export type RemoteCameraStatus = {
  configured: boolean;
  device_reachable: boolean;
  worker_running: boolean;
  streaming: boolean;
  stream_connected: boolean;
  paused_for_simulation: boolean;
  transport: "idle" | "mjpeg";
  host: string | null;
  source_id: string | null;
  status_url: string | null;
  capture_url: string | null;
  stream_url: string | null;
  target_fps: number;
  fetch_interval_ms: number;
  measured_fps: number;
  last_frame_interval_ms: number | null;
  stream_reconnects: number;
  session_recoveries: number;
  consecutive_failures: number;
  reconnect_backoff_ms: number;
  stream_bytes_received: number;
  dropped_stale_frames: number;
  connected_at_ms: number | null;
  stream_started_at_ms: number | null;
  last_stream_connected_at_ms: number | null;
  last_recovery_at_ms: number | null;
  last_probe_at_ms: number | null;
  last_attempt_at_ms: number | null;
  last_success_at_ms: number | null;
  last_http_status: number | null;
  last_frame_number: number | null;
  last_frame_bytes: number;
  successful_fetches: number;
  failed_fetches: number;
  last_error: string | null;
  settings: RemoteCameraSettings | null;
  device: Record<string, unknown>;
  control_sequence: string[];
  prototype_only: boolean;
};

export function liveCameraMjpegUrl(): string {
  return `${API_BASE}/api/camera/live.mjpeg`;
}

export async function fetchRemoteCameraStatus(): Promise<RemoteCameraStatus> {
  return requestJsonStrict<RemoteCameraStatus>(`${API_BASE}/api/camera/remote/status`);
}

export async function connectRemoteCamera(input: {
  host: string;
  source_id: string;
}): Promise<RemoteCameraStatus> {
  return requestJsonStrict<RemoteCameraStatus>(`${API_BASE}/api/camera/remote/connect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function startRemoteCamera(input: {
  target_fps: number;
  settings: RemoteCameraSettings;
}): Promise<RemoteCameraStatus> {
  return requestJsonStrict<RemoteCameraStatus>(`${API_BASE}/api/camera/remote/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function stopRemoteCamera(): Promise<RemoteCameraStatus> {
  return requestJsonStrict<RemoteCameraStatus>(`${API_BASE}/api/camera/remote/stop`, { method: "POST" });
}

export async function disconnectRemoteCamera(): Promise<RemoteCameraStatus> {
  return requestJsonStrict<RemoteCameraStatus>(`${API_BASE}/api/camera/remote/disconnect`, { method: "POST" });
}

export async function refreshCameraAfterRemoteChange(): Promise<CameraStatus> {
  return fetchCameraStatus();
}
