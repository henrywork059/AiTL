import type { DetectionFrame, TrafficState, Zone } from "./types";
import { mockFrame, mockTrafficState, mockZones } from "./mockData";
import { requestJson } from "./lib/apiClient";

const API_BASE = "http://127.0.0.1:8000";

type ZonesResponse = {
  zones: Zone[];
};

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
