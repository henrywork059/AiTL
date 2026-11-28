import { API_BASE } from "../api";
import { requestJsonStrict } from "./apiClient";

export const DEMO_SCENARIOS = ["nominal", "missing_ack", "rejected_ack", "wrong_ack", "late_ack", "disconnect", "manual_stop"] as const;
export type DemoScenario = typeof DEMO_SCENARIOS[number];
type FakeOutputState = { connected: boolean; armed: boolean; active: boolean; reason: string; physical_output_allowed: false };
export type FakeDemoReport = {
  schema_version: 1; scenario: DemoScenario; authorization_requested: boolean;
  provenance: "illustrative/synthetic"; time_basis: "virtual_ms"; lease_ms: number;
  prototype_only: true; physical_output_allowed: false; audio_playback: false;
  trace: Array<{ time_ms: number; event: string; lighting: FakeOutputState; speaker: FakeOutputState;
    ack: { command_id: number; accepted: boolean; latency_ms: number } | null }>;
  checks: Record<string, boolean>;
};

export const DEMO_CHECKS = ["authorization_matches", "activation_matches_scenario", "denied_never_active",
  "acknowledgments_match", "expected_stop", "final_disconnected", "physical_and_audio_unavailable"] as const;

export async function runFakeJunctionDemo(scenario: DemoScenario, authorized: boolean, signal: AbortSignal): Promise<FakeDemoReport> {
  const report = await requestJsonStrict<FakeDemoReport>(`${API_BASE}/api/traffic/fake-junction-demo`, {
    method: "POST", headers: { "Content-Type": "application/json" }, signal,
    body: JSON.stringify({ scenario, authorized }),
  });
  if (!report || report.schema_version !== 1 || report.scenario !== scenario || report.authorization_requested !== authorized ||
      report.provenance !== "illustrative/synthetic" || report.time_basis !== "virtual_ms" || report.prototype_only !== true ||
      report.physical_output_allowed !== false || report.audio_playback !== false ||
      !Array.isArray(report.trace) || !report.trace.length || report.trace.some(row =>
        !Number.isFinite(row.time_ms) || typeof row.event !== "string" ||
        [row.lighting, row.speaker].some(s => !s || typeof s.active !== "boolean" || typeof s.armed !== "boolean" ||
          typeof s.connected !== "boolean" || s.physical_output_allowed !== false || typeof s.reason !== "string")) ||
      !report.checks || Object.keys(report.checks).length !== DEMO_CHECKS.length ||
      DEMO_CHECKS.some(key => typeof report.checks[key] !== "boolean")) {
    throw new Error("Unverified synthetic demonstration response.");
  }
  return report;
}
