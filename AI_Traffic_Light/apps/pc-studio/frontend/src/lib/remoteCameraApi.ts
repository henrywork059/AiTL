import { API_BASE, fetchCameraStatus } from "../api";
import { requestJsonStrict } from "./apiClient";
import type { CameraStatus } from "../types";

export type RemoteCameraStatus = {
  configured: boolean;
  worker_running: boolean;
  connected: boolean;
  paused_for_simulation: boolean;
  host: string | null;
  source_id: string | null;
  capture_url: string | null;
  stream_url: string | null;
  fetch_interval_ms: number;
  started_at_ms: number | null;
  last_attempt_at_ms: number | null;
  last_success_at_ms: number | null;
  success_age_ms: number | null;
  last_http_status: number | null;
  last_frame_number: number | null;
  last_frame_bytes: number;
  successful_fetches: number;
  failed_fetches: number;
  last_error: string | null;
  prototype_only: boolean;
};

export async function fetchRemoteCameraStatus(): Promise<RemoteCameraStatus> {
  return requestJsonStrict<RemoteCameraStatus>(`${API_BASE}/api/camera/remote/status`);
}

export async function connectRemoteCamera(input: {
  host: string;
  source_id: string;
  fetch_interval_ms?: number;
}): Promise<RemoteCameraStatus> {
  return requestJsonStrict<RemoteCameraStatus>(`${API_BASE}/api/camera/remote/connect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function disconnectRemoteCamera(): Promise<RemoteCameraStatus> {
  return requestJsonStrict<RemoteCameraStatus>(`${API_BASE}/api/camera/remote/disconnect`, {
    method: "POST",
  });
}

export async function refreshCameraAfterRemoteChange(): Promise<CameraStatus> {
  return fetchCameraStatus();
}
