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
  frame_size: "QVGA",
  jpeg_quality: 24,
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


export type CameraDeviceCapability = {
  direction: "input" | "output";
  support: "implemented" | "simulation-only" | "unavailable";
  available: boolean;
};

export type CameraDeviceHealth = {
  state: "not_connected" | "unreachable" | "connected" | "reconnecting" |
    "waiting_for_frame" | "streaming" | "stale" | "paused" | "error" |
    "simulated" | "idle";
  control_connected: boolean | null;
  reachable: boolean | null;
  streaming: boolean;
  transport_connected: boolean;
  frame_fresh: boolean;
  frame_age_ms: number | null;
  last_error: string | null;
};

export type CameraDeviceContract = {
  schema_version: 1;
  source_id: string;
  device_type: "esp32_camera" | "simulation_camera";
  control_owner: "pc_studio";
  capabilities: {
    camera_input: CameraDeviceCapability;
    lighting_output: CameraDeviceCapability;
    speaker_output: CameraDeviceCapability;
  };
  health: CameraDeviceHealth;
  physical_output_allowed: false;
};

export type RemoteCameraProfile = {
  source_id: string;
  kind: "esp32" | "simulation";
  device_contract?: CameraDeviceContract;
  host: string;
  target_fps: number;
  settings: RemoteCameraSettings;
  last_used_ms: number;
  selected: boolean;
  connected: boolean;
  device_reachable: boolean;
  streaming: boolean;
  stream_connected: boolean;
  paused_for_simulation: boolean;
  measured_fps: number;
  last_success_at_ms: number | null;
  frame_age_ms?: number | null;
  frame_stale?: boolean;
  last_frame_interval_ms?: number | null;
  source_sequence_gaps?: number;
  repeated_source_frames?: number;
  source_sequence_resets?: number;
  stream_reconnects?: number;
  session_recoveries?: number;
  last_error: string | null;
};

export type RemoteCameraStatus = {
  active_source_id: string | null;
  device_contract?: CameraDeviceContract | null;
  camera_count: number;
  cameras: RemoteCameraProfile[];
  registry_warning: string | null;
  multi_camera: boolean;
  max_saved_cameras: number;
  configured: boolean;
  device_reachable: boolean;
  worker_running: boolean;
  streaming: boolean;
  stream_connected: boolean;
  paused_for_simulation: boolean;
  transport: "idle" | "tcp_jpeg";
  stream_protocol: "aitl-tcp-jpeg-v1" | null;
  host: string | null;
  source_id: string | null;
  status_url: string | null;
  capture_url: string | null;
  stream_url: string | null;
  target_fps: number;
  fetch_interval_ms: number;
  measured_fps: number;
  frame_age_ms?: number | null;
  frame_stale?: boolean;
  repeated_source_frames?: number;
  source_sequence_resets?: number;
  last_frame_interval_ms: number | null;
  stream_reconnects: number;
  session_recoveries: number;
  consecutive_failures: number;
  reconnect_backoff_ms: number;
  stream_bytes_received: number;
  dropped_stale_frames: number;
  source_sequence_gaps: number;
  last_remote_sequence: number | null;
  last_source_uptime_ms: number | null;
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

export type SimulationScene = {
  source_id: string;
  frame_number: number;
  received_at_ms: number;
  width: number;
  height: number;
  simulation_time_seconds: number;
  paused: boolean;
  density: "light" | "normal" | "busy";
  signal: {
    phase: string;
    vehicle_go: boolean;
    pedestrian_walk: boolean;
    seconds_remaining: number;
  };
  vehicles: Array<{
    id: string;
    x: number;
    y: number;
    width: number;
    direction: number;
    vehicle_type: string;
    color: string;
  }>;
  pedestrians: Array<{
    id: string;
    x: number;
    y: number;
    direction: number;
    color: string;
  }>;
};

export async function fetchSimulationScene(sourceId: string): Promise<SimulationScene> {
  return requestJsonStrict<SimulationScene>(`${API_BASE}/api/camera/simulation/scene?source_id=${encodeURIComponent(sourceId)}`);
}

export async function fetchRemoteCameraStatus(): Promise<RemoteCameraStatus> {
  return requestJsonStrict<RemoteCameraStatus>(`${API_BASE}/api/camera/remote/status`);
}

export async function saveRemoteCamera(input: {
  host: string;
  source_id: string;
  target_fps: number;
  settings: RemoteCameraSettings;
}): Promise<RemoteCameraStatus> {
  return requestJsonStrict<RemoteCameraStatus>(`${API_BASE}/api/camera/remote/cameras`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function saveSimulationCamera(pair: 1 | 2 = 1): Promise<RemoteCameraStatus> {
  return requestJsonStrict<RemoteCameraStatus>(`${API_BASE}/api/camera/remote/simulation?pair=${pair}`, { method: "POST" });
}

export async function selectRemoteCamera(source_id: string): Promise<RemoteCameraStatus> {
  return requestJsonStrict<RemoteCameraStatus>(`${API_BASE}/api/camera/remote/select`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_id }),
  });
}

export async function deleteRemoteCamera(source_id: string): Promise<RemoteCameraStatus> {
  return requestJsonStrict<RemoteCameraStatus>(`${API_BASE}/api/camera/remote/cameras/${encodeURIComponent(source_id)}`, {
    method: "DELETE",
  });
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

export type NativeProjectionScene = {
  schema_version: 1;
  provenance: "synthetic_sumo_projection";
  generation: number;
  seed: number;
  tick: number;
  time_s: number;
  pixels_per_m?: number;
  paused?: boolean;
  received_at_ms?: number;
  width: 1280;
  height: 720;
  lanes: Array<{id: string; kind: "road" | "walk" | "crossing"; points: [number, number][]; width_px: number}>;
  agents: Array<{id: string; kind: "vehicle" | "pedestrian"; x: number; y: number; road_id: string; speed_m_s: number}>;
};
export type NativeProjectionResponse = {
  status: "disabled" | "idle" | "starting" | "running" | "busy" | "unavailable";
  provenance: "synthetic_sumo_projection";
  generation?: number;
  snapshot: NativeProjectionScene | null;
};
export function fetchNativeProjection(signal: AbortSignal): Promise<NativeProjectionResponse> {
  return requestJsonStrict<NativeProjectionResponse>(
    `${API_BASE}/api/camera/simulation/native-projection?format=scene`, { signal, cache: "no-store" },
  );
}

export type NativeEvaluationState = NativeProjectionResponse & {epoch:string;generation:number;mode:"fixed"|"adaptive"|null;density:"light"|"normal"|"busy"|null;max_ticks:number;native_only:true;physical_output_allowed:false};
const nativeEvaluationBase = `${API_BASE}/api/camera/simulation/native-evaluation`;
export function fetchNativeEvaluation(signal:AbortSignal):Promise<NativeEvaluationState>{
  return requestJsonStrict<NativeEvaluationState>(nativeEvaluationBase,{signal,cache:"no-store"});
}
export function nativeEvaluationCommand(action:"start"|"step"|"pause"|"stop",body:Record<string,unknown>,signal:AbortSignal):Promise<NativeEvaluationState>{
  return requestJsonStrict<NativeEvaluationState>(`${nativeEvaluationBase}/${action}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body),signal});
}
export function nativeEvaluationCaptureUrl(state:NativeEvaluationState){
  return `${nativeEvaluationBase}/capture?${new URLSearchParams({epoch:state.epoch,generation:String(state.generation),tick:String(state.snapshot?.tick??-1)})}`;
}
