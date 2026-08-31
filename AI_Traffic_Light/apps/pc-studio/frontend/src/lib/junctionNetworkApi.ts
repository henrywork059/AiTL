import { API_BASE } from "../api";
import type { JunctionNetworkConfig, JunctionNetworkOverview } from "../types/junctionNetwork";
import { requestJsonStrict } from "./apiClient";

export async function fetchJunctionNetworkOverview(): Promise<JunctionNetworkOverview> {
  return requestJsonStrict<JunctionNetworkOverview>(`${API_BASE}/api/traffic/network/overview`);
}

export async function saveJunctionNetwork(config: JunctionNetworkConfig): Promise<JunctionNetworkConfig> {
  return requestJsonStrict<JunctionNetworkConfig>(`${API_BASE}/api/traffic/network`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config }),
  });
}

export async function resetJunctionNetwork(): Promise<JunctionNetworkConfig> {
  return requestJsonStrict<JunctionNetworkConfig>(`${API_BASE}/api/traffic/network/reset`, { method: "POST" });
}
