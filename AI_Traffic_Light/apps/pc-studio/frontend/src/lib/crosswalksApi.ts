import { API_BASE } from "../api";
import { requestJsonStrict } from "./apiClient";
import type { CrosswalkConfig } from "../types/crosswalks";

export function fetchCrosswalks(): Promise<CrosswalkConfig> {
  return requestJsonStrict<CrosswalkConfig>(API_BASE + "/api/crosswalks");
}

export function saveCrosswalks(config: CrosswalkConfig): Promise<CrosswalkConfig> {
  return requestJsonStrict<CrosswalkConfig>(API_BASE + "/api/crosswalks", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config }),
  });
}
