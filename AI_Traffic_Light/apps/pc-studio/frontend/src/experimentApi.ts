import { API_BASE } from "./api";
import { requestJsonStrict } from "./lib/apiClient";
import type { SimulationExperiment, SimulationExperimentList } from "./types/experiments";

export type SimulationExperimentInput = {
  duration_seconds: number;
  density: "light" | "normal" | "busy";
  seed: number;
  sample_interval_seconds: number;
  profile: string | null;
  label: string;
};

export async function runSimulationExperiment(input: SimulationExperimentInput): Promise<SimulationExperiment> {
  return requestJsonStrict<SimulationExperiment>(`${API_BASE}/api/traffic/experiments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function fetchSimulationExperiments(limit = 50): Promise<SimulationExperimentList> {
  return requestJsonStrict<SimulationExperimentList>(`${API_BASE}/api/traffic/experiments?limit=${limit}`);
}

export async function fetchSimulationExperiment(runId: string): Promise<SimulationExperiment> {
  return requestJsonStrict<SimulationExperiment>(`${API_BASE}/api/traffic/experiments/${encodeURIComponent(runId)}`);
}

export async function deleteSimulationExperiment(runId: string): Promise<{ deleted: boolean; run_id: string }> {
  return requestJsonStrict<{ deleted: boolean; run_id: string }>(`${API_BASE}/api/traffic/experiments/${encodeURIComponent(runId)}`, { method: "DELETE" });
}

export function simulationExperimentExportUrl(runId: string): string {
  return `${API_BASE}/api/traffic/experiments/${encodeURIComponent(runId)}/export.csv`;
}
