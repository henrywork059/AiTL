import { useEffect, useState } from "react";
import {
  fetchActiveZones, fetchCrosswalkSignalNetwork, fetchSignalRules, fetchSignalStatus, saveSignalRules,
} from "../api";
import type { CrosswalkSignalNetwork } from "../api";
import { fetchCrosswalks } from "../lib/crosswalksApi";
import { useSerialPolling } from "../lib/useSerialPolling";
type RegionChoice = { id: string; label: string };
import type { ScenarioCondition, ScenarioSignalRulesConfig, SignalScenario, ScenarioSignalStatus } from "../types/signalScenarios";
import "./signalRules.css";

type Preset = {
  id: string; title: string; description: string; rank: number;
  metric?: "pedestrians_waiting" | "vehicles_waiting" | "pedestrians_crossing";
  className?: string; threshold: number; seconds: number;
  action: SignalScenario["action"]["type"]; phases: string[]; service: "pedestrian" | "vehicle" | null;
};
const PRESETS: Preset[] = [
  { id: "aitl_emergency_request", title: "Emergency vehicle priority", description: "Request the next protected vehicle phase after required pedestrian clearance. No flashing green.", rank: 12, className: "ambulance", threshold: 1, seconds: 0, action: "request_next_phase", phases: ["pedestrian_green"], service: "vehicle" },
  { id: "aitl_emergency_extend", title: "Emergency vehicle green extension", description: "If the vehicle phase is already green, extend it within its configured maximum.", rank: 13, className: "ambulance", threshold: 1, seconds: 8, action: "extend_current_phase", phases: ["vehicle_green"], service: "vehicle" },
  { id: "aitl_slow_clearance", title: "Slow pedestrian clearance", description: "When a pedestrian remains in the crossing and clearance is nearing its end, keep the specified time available.", rank: 15, metric: "pedestrians_crossing", threshold: 1, seconds: 5, action: "hold_current_phase", phases: ["pedestrian_flashing"], service: null },
  { id: "aitl_accessibility", title: "Accessibility extension", description: "Extend pedestrian walk when the active detector supports and observes the wheelchair class.", rank: 25, className: "wheelchair", threshold: 1, seconds: 8, action: "extend_current_phase", phases: ["pedestrian_green"], service: "pedestrian" },
  { id: "aitl_pedestrian_crowd", title: "Pedestrian crowd adjustment", description: "Extend pedestrian walk when the pedestrian waiting count reaches the threshold.", rank: 80, metric: "pedestrians_waiting", threshold: 8, seconds: 5, action: "extend_current_phase", phases: ["pedestrian_green"], service: "pedestrian" },
  { id: "aitl_vehicle_queue", title: "Vehicle queue adjustment", description: "Extend vehicle green when the waiting vehicle count reaches the threshold.", rank: 90, metric: "vehicles_waiting", threshold: 12, seconds: 8, action: "extend_current_phase", phases: ["vehicle_green"], service: "vehicle" },
];

function newScenario(preset: Preset, zoneId: string): SignalScenario {
  const condition: ScenarioCondition = preset.metric
    ? { source: "metric", metric: preset.metric, operator: "gte", threshold: preset.threshold }
    : { source: "zone_class_count", zone_id: zoneId, class_name: preset.className ?? "*", operator: "gte", threshold: preset.threshold };
  return {
    id: preset.id, label: preset.title, enabled: false, rank: preset.rank, match: "all",
    conditions: preset.id === "aitl_slow_clearance"
      ? [condition, { source: "metric", metric: "phase_remaining_seconds", operator: "lte", threshold: 3 }]
      : [condition], persistence_seconds: preset.className ? 1 : 0,
    cooldown_seconds: preset.className ? 10 : 5,
    action: { type: preset.action, adjustment_seconds: preset.seconds,
      target_phases: preset.phases, request_service: preset.service },
  };
}
function withPresets(config: ScenarioSignalRulesConfig, zones: RegionChoice[]): ScenarioSignalRulesConfig {
  const next = structuredClone(config);
  const profile = next.profiles[next.active_profile];
  const existing = new Set(profile.scenarios.map((scenario) => scenario.id));
  const ranks = new Set(profile.scenarios.map((scenario) => scenario.rank));
  for (const preset of PRESETS) {
    if (existing.has(preset.id)) continue;
    const scenario = newScenario(preset, zones[0]?.id ?? "unassigned");
    while (ranks.has(scenario.rank)) scenario.rank += 1;
    ranks.add(scenario.rank);
    profile.scenarios.push(scenario);
  }
  return next;
}

export function LiveSignalAdjustmentsPage() {
  const [saved, setSaved] = useState<ScenarioSignalRulesConfig | null>(null);
  const [draft, setDraft] = useState<ScenarioSignalRulesConfig | null>(null);
  const [zones, setZones] = useState<RegionChoice[]>([]);
  const [crosswalkSignals, setCrosswalkSignals] = useState<CrosswalkSignalNetwork | null>(null);
  const [status, setStatus] = useState<ScenarioSignalStatus | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function load() {
    const [raw, active, crosswalks] = await Promise.all([fetchSignalRules(), fetchActiveZones(), fetchCrosswalks()]);
    const config = raw as unknown as ScenarioSignalRulesConfig;
    setSaved(config);
    const physicalRegions = crosswalks.crosswalks.flatMap((crosswalk) =>
      crosswalk.regions.map((region) => ({
        id: crosswalk.id + ":" + region.id,
        label: crosswalk.label + " / " + region.label,
      })));
    const legacyZones = active.zones.filter((item) =>
      item.type !== "ignore" && item.type !== "counting_line");
    const choices = [...physicalRegions, ...legacyZones];
    setZones(choices);
    setDraft(withPresets(config, choices));
    setError(null);
  }
  useEffect(() => { void load().catch((reason) => setError(String(reason))); }, []);
  useSerialPolling(async () => {
    const [global, crossings] = await Promise.all([fetchSignalStatus(), fetchCrosswalkSignalNetwork()]);
    setStatus(global as ScenarioSignalStatus);
    setCrosswalkSignals(crossings);
  }, 1000, {
    onError: (reason) => setError(reason instanceof Error ? reason.message : "Signal status unavailable"),
  });

  const scenarios = draft?.profiles[draft.active_profile].scenarios ?? [];
  const savedScenarios = saved?.profiles[saved.active_profile].scenarios ?? [];
  const changed = Boolean(saved && draft && JSON.stringify(scenarios) !== JSON.stringify(savedScenarios));

  function update(id: string, edit: (scenario: SignalScenario) => void) {
    setDraft((current) => {
      if (!current) return current;
      const next = structuredClone(current);
      const scenario = next.profiles[next.active_profile].scenarios.find((item) => item.id === id);
      if (scenario) edit(scenario);
      return next;
    });
    setNotice(null);
  }
  async function save() {
    if (!saved || !draft) return;
    setSaving(true);
    setError(null);
    try {
      const latest = await fetchSignalRules() as unknown as ScenarioSignalRulesConfig;
      if (latest.active_profile !== saved.active_profile ||
        JSON.stringify(latest.profiles[latest.active_profile].scenarios) !== JSON.stringify(savedScenarios)) {
        throw new Error("Live rules were changed elsewhere. Reload before saving.");
      }
      if (PRESETS.some((preset) => {
        const scenario = scenarios.find((item) => item.id === preset.id);
        return Boolean(scenario?.enabled && scenario.conditions.some((condition) =>
          condition.source === "zone_class_count" && !zones.some((zone) => zone.id === condition.zone_id)));
      })) throw new Error("Configure and select an available detection region before enabling a class-based adjustment.");
      const next = structuredClone(latest);
      next.profiles[next.active_profile].scenarios = scenarios;
      const result = await saveSignalRules(next) as unknown as ScenarioSignalRulesConfig;
      setSaved(result);
      setDraft(withPresets(result, zones));
      setNotice("Live signal adjustment rules saved to the existing protected scenario controller.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save live adjustments.");
    } finally {
      setSaving(false);
    }
  }

  return <div className="page-stack signal-rules-page">
    <section className="panel">
      <div className="panel-header">
        <div><h2>Live Signal Adjustments</h2><p className="placeholder-copy">Configure AI-triggered simulation rules. These are ranked scenarios in the existing signal controller, not a second traffic-light controller.</p></div>
        <span className="status-pill muted">{draft?.active_profile ?? "Loading"}</span>
      </div>
      <div className="live-inference-meta">
        <span>Mode: <strong>{status?.mode ?? "Unavailable"}</strong></span>
        <span>Legacy controller adjustment: <strong>{status?.winning_scenario_label ?? "None"}</strong></span>
        <span>Observed data: <strong>{status?.data_fresh ? "Fresh" : "Stale / unavailable"}</strong></span>
      </div>
      {crosswalkSignals && <div className="signal-timing-table-wrap">
        <table className="signal-timing-table">
          <thead><tr><th>Crosswalk</th><th>Camera observation</th><th>Active simulation adjustment</th></tr></thead>
          <tbody>{Object.values(crosswalkSignals.crosswalks).map((item) => (
            <tr key={item.crosswalk_id}>
              <td>{item.crosswalk_id}</td>
              <td>{item.observation_provenance === "camera_ai"
                ? (item.camera_coverage ?? "camera AI") + " · " + (item.camera_sources ?? []).join(", ")
                : "Not available"}</td>
              <td>{(item.signal as ScenarioSignalStatus | null)?.winning_scenario_label ?? "None"}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>}
      <p className="small-note">Rules run only when adaptive/test mode has fresh observations and dry-run is disabled. Emergency priority requests safe phase transitions; it does not immediately switch lights or grant real-world emergency access. Slow clearance uses a crossing-occupancy signal, not inferred walking speed. Class-based rules require a model that detects the class in a saved Crosswalk region. Legacy zones still affect the legacy global controller; Crosswalk regions feed their corresponding independent controllers. Untyped Crosswalk regions do not imply that objects are waiting, queued or currently crossing.</p>
    </section>
    {draft && PRESETS.map((preset) => {
      const rule = scenarios.find((item) => item.id === preset.id);
      if (!rule) return null;
      const condition = rule.conditions[0];
      const live = status?.scenario_status?.find((item) => item.scenario_id === rule.id);
      return <section className="panel" key={preset.id}>
        <div className="panel-header">
          <div><h3>{preset.title}</h3><p className="placeholder-copy">{preset.description}</p></div>
          <label className="inline-toggle">
            <input type="checkbox" checked={rule.enabled} onChange={(event) => update(rule.id, (item) => { item.enabled = event.target.checked; })} />
            Enabled
          </label>
        </div>
        <div className="form-grid">
          {condition.source === "zone_class_count" && <>
            <label>Detection region
              <select value={condition.zone_id} onChange={(event) => update(rule.id, (item) => {
                const first = item.conditions[0]; if (first.source === "zone_class_count") first.zone_id = event.target.value;
              })}>
                {!zones.some((zone) => zone.id === condition.zone_id) && <option value={condition.zone_id}>Select a configured region</option>}
                {zones.map((zone) => <option key={zone.id} value={zone.id}>{zone.label}</option>)}
              </select>
            </label>
            <label>Detection class
              <input value={condition.class_name} onChange={(event) => update(rule.id, (item) => {
                const first = item.conditions[0]; if (first.source === "zone_class_count") first.class_name = event.target.value.trim();
              })} />
            </label>
          </>}
          <label>{preset.metric === "pedestrians_waiting" ? "Pedestrian threshold" : preset.metric === "vehicles_waiting" ? "Vehicle threshold" : preset.metric ? "Pedestrians still crossing (minimum)" : "Class count threshold"}
            <input type="number" min={1} max={500} step={1} value={condition.threshold} onChange={(event) => update(rule.id, (item) => {
              item.conditions[0].threshold = Number(event.target.value);
            })} />
          </label>
          {preset.id === "aitl_slow_clearance" && rule.conditions[1]?.source === "metric" && <label>Trigger when phase has at most (seconds)
            <input type="number" min={0.5} max={30} step={0.5} value={rule.conditions[1].threshold}
              onChange={(event) => update(rule.id, (item) => { item.conditions[1].threshold = Number(event.target.value); })} />
          </label>}
          {preset.action !== "request_next_phase" && <label>{preset.action === "hold_current_phase" ? "Minimum protected clearance remaining (seconds)" : "Requested extension (seconds)"}
            <input type="number" min={0} max={60} step={0.5} value={rule.action.adjustment_seconds}
              onChange={(event) => update(rule.id, (item) => { item.action.adjustment_seconds = Number(event.target.value); })} />
          </label>}
          <label>Cooldown (seconds)
            <input type="number" min={0} max={600} step={1} value={rule.cooldown_seconds}
              onChange={(event) => update(rule.id, (item) => { item.cooldown_seconds = Number(event.target.value); })} />
          </label>
        </div>
        <p className="small-note">Phase: {rule.action.target_phases.join(", ").replaceAll("_", " ")} · State: {live?.state ?? "Not evaluated"}{live?.reason ? " · " + live.reason : ""}</p>
      </section>;
    })}
    <section className="panel">
      <div className="button-row">
        <button type="button" disabled={saving} onClick={() => void load().catch((reason) => setError(String(reason)))}>Reload rules</button>
        <button className="primary" type="button" disabled={!changed || saving} onClick={() => void save()}>{saving ? "Saving..." : "Save live adjustments"}</button>
      </div>
      {error && <p className="error-message" role="alert">{error}</p>}
      {notice && <p className="success-message" role="status">{notice}</p>}
    </section>
  </div>;
}
