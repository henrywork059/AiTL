import type { DetectionFrame, TrafficState, Zone } from "./types";
import { mockFrame, mockTrafficState, mockZones } from "./mockData";

const API_BASE = "http://127.0.0.1:8000";

export async function fetchMockFrame(): Promise<DetectionFrame> {
  try {
    const res = await fetch(`${API_BASE}/api/mock/frame`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return mockFrame;
  }
}

export async function fetchMockZones(): Promise<Zone[]> {
  try {
    const res = await fetch(`${API_BASE}/api/mock/zones`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.zones;
  } catch {
    return mockZones;
  }
}

export async function fetchTrafficState(): Promise<TrafficState> {
  try {
    const res = await fetch(`${API_BASE}/api/traffic/state`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return mockTrafficState;
  }
}
