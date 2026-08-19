import { useCallback, useEffect, useMemo, useState } from "react";
import {
  clearSignalDecisionHistory,
  clearSignalIncident,
  fetchActiveZones,
  fetchSignalDecisionHistory,
  fetchSignalRules,
  fetchSignalStatus,
  fetchTrafficState,
  previewSignalRules,
  resetSignalRules,
  resetSignalRulesRuntime,
  saveSignalRules,
  setSignalTestInputs,
} from "../api";
import { useSerialPolling } from "../lib/useSerialPolling";
import type {
  SignalDecisionHistory,
  SignalPhaseKey,
  SignalRulesPreview,
  SignalTestInputs,
  Zone,
} from "../types";
import type {
  ScenarioCondition,
  ScenarioSignalRulesConfig,
  ScenarioSignalStatus,
  ScenarioTrafficState,
  SignalMetric,
  SignalScenario,
  SignalScenarioStatus,
} from "../types/signalScenarios";
import "./signalRules.css";

type TabId = "live" | "timing" | "scenarios" | "test" | "history";

const PHASE_LABELS: Record<SignalPhaseKey, string> = {
  vehicle_green: "Vehicle green",
  vehicle_yellow: "Vehicle yellow",
  all_red_to_pedestrian: "All red → pedestrian",
  pedestrian_green: "Pedestrian WALK",
  pedestrian_flashing: "Pedestrian CLEAR",
  all_red_to_vehicle: "All red → vehicles",
};

const PHASE_KEYS = Object.keys(PHASE_LABELS) as SignalPhaseKey[];
const KNOWN_CLASSES = ["*", "person", "car", "bus", "truck", "motorcycle", "bicycle"];

const METRICS: { value: SignalMetric; label: string; testOnly?: boolean }[] = [
  { value: "pedestrians_waiting", label: "Pedestrians waiting" },
  { value: "pedestrians_crossing", label: "Pedestrians crossing" },
  { value: "vehicles_waiting", label: "Vehicles queued" },
  { value: "pedestrian_wait_seconds", label: "Pedestrian wait duration" },
  { value: "vehicle_wait_seconds", label: "Vehicle wait duration" },
  { value: "crossing_dwell_seconds", label: "Crossing dwell duration" },
  { value: "mobility_assistance", label: "Mobility assistance test flag", testOnly: true },
  { value: "incident_person_fallen", label: "Fallen-person incident test flag", testOnly: true },
];

const OPERATORS = [
  { value: "gt", label: ">" },
  { value: "gte", label: "≥" },
  { value: "lt", label: "<" },
  { value: "lte", label: "≤" },
  { value: "eq", label: "=" },
] as const;

const ACTIONS = [
  { value: "extend_current_phase", label: "Extend current phase" },
  { value: "reduce_current_phase", label: "Reduce current phase" },
  { value: "hold_current_phase", label: "Hold current phase / keep clearance" },
  { value: "request_next_phase", label: "Request next protected phase sooner" },
  { value: "incident_hold", label: "Simulation incident all-red hold" },
] as const;

function cloneConfig(config: ScenarioSignalRulesConfig): ScenarioSignalRulesConfig {
  return JSON.parse(JSON.stringify(config)) as ScenarioSignalRulesConfig;
}

function numeric(value: string, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function phaseClass(phase: string | undefined): string {
  if (phase === "pedestrian_green" || phase === "vehicle_green") return "status-pill status-implemented";
  if (phase === "vehicle_yellow" || phase === "pedestrian_flashing") return "status-pill status-planned";
  return "status-pill";
}

function conditionText(condition: ScenarioCondition, zones: Zone[]): string {
  const operator = OPERATORS.find((item) => item.value === condition.operator)?.label ?? condition.operator;
  if (condition.source === "metric") {
    const label = METRICS.find((item) => item.value === condition.metric)?.label ?? condition.metric;
    return `${label} ${operator} ${condition.threshold}`;
  }
  const zone = zones.find((item) => item.id === condition.zone_id);
  const classLabel = condition.class_name === "*" ? "all detected classes" : condition.class_name;
  return `${classLabel} ${operator} ${condition.threshold} in ${zone?.label ?? condition.zone_id}`;
}

function actionText(scenario: SignalScenario): string {
  const action = ACTIONS.find((item) => item.value === scenario.action.type)?.label ?? scenario.action.type;
  const seconds = scenario.action.type === "incident_hold" ? "" : ` · ${scenario.action.adjustment_seconds}s`;
  const request = scenario.action.request_service ? ` · request ${scenario.action.request_service}` : "";
  return `${action}${seconds}${request}`;
}

function defaultScenario(zones: Zone[], existing: SignalScenario[]): SignalScenario {
  const rank = existing.length === 0 ? 10 : Math.max(...existing.map((item) => item.rank)) + 10;
  const firstZone = zones.find((item) => !["ignore", "counting_line"].includes(item.type));
  const id = `scenario_${Date.now().toString(36)}`;
  return {
    id,
    label: "New traffic scenario",
    enabled: true,
    rank,
    match: "all",
    conditions: firstZone
      ? [{ source: "zone_class_count", zone_id: firstZone.id, class_name: "person", operator: "gt", threshold: 2 }]
      : [{ source: "metric", metric: "pedestrians_waiting", operator: "gt", threshold: 2 }],
    persistence_seconds: 1,
    cooldown_seconds: 5,
    action: {
      type: "reduce_current_phase",
      adjustment_seconds: 3,
      target_phases: ["vehicle_green"],
      request_service: "pedestrian",
    },
  };
}

function statusClass(state: string): string {
  if (state === "winner") return "status-pill status-implemented";
  if (state === "triggered") return "status-pill status-secondary";
  if (state === "suppressed" || state === "unavailable") return "status-pill status-planned";
  return "status-pill muted";
}

export function TrafficLogicPage() {
  const [tab, setTab] = useState<TabId>("live");
  const [traffic, setTraffic] = useState<ScenarioTrafficState | null>(null);
  const [signal, setSignal] = useState<ScenarioSignalStatus | null>(null);
  const [savedConfig, setSavedConfig] = useState<ScenarioSignalRulesConfig | null>(null);
  const [draftConfig, setDraftConfig] = useState<ScenarioSignalRulesConfig | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [history, setHistory] = useState<SignalDecisionHistory | null>(null);
  const [preview, setPreview] = useState<SignalRulesPreview | null>(null);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null);
  const [testInputs, setTestInputs] = useState<SignalTestInputs>({
    pedestrians_waiting: 0,
    pedestrians_crossing: 0,
    vehicles_waiting: 0,
    mobility_assistance: false,
    incident_person_fallen: false,
  });
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const loadConfiguration = useCallback(async () => {
    const config = await fetchSignalRules() as unknown as ScenarioSignalRulesConfig;
    setSavedConfig(config);
    setDraftConfig(cloneConfig(config));
    const profile = config.profiles[config.active_profile];
    setSelectedScenarioId((current) => current && profile.scenarios.some((item) => item.id === current) ? current : profile.scenarios[0]?.id ?? null);
  }, []);

  const refreshHistory = useCallback(async () => {
    setHistory(await fetchSignalDecisionHistory(300));
  }, []);

  const pollLiveState = useCallback(async () => {
    try {
      const [nextTraffic, nextSignal] = await Promise.all([fetchTrafficState(), fetchSignalStatus()]);
      setTraffic(nextTraffic as ScenarioTrafficState);
      const scenarioSignal = nextSignal as unknown as ScenarioSignalStatus;
      setSignal(scenarioSignal);
      setTestInputs(scenarioSignal.test_inputs);
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Traffic state could not be evaluated.");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function initial() {
      try {
        const [nextTraffic, nextSignal, config, nextHistory, zoneStatus] = await Promise.all([
          fetchTrafficState(),
          fetchSignalStatus(),
          fetchSignalRules(),
          fetchSignalDecisionHistory(300),
          fetchActiveZones(),
        ]);
        if (cancelled) return;
        const scenarioConfig = config as unknown as ScenarioSignalRulesConfig;
        const scenarioSignal = nextSignal as unknown as ScenarioSignalStatus;
        setTraffic(nextTraffic as ScenarioTrafficState);
        setSignal(scenarioSignal);
        setSavedConfig(scenarioConfig);
        setDraftConfig(cloneConfig(scenarioConfig));
        setZones(zoneStatus.zones);
        setHistory(nextHistory);
        setTestInputs(scenarioSignal.test_inputs);
        setSelectedScenarioId(scenarioConfig.profiles[scenarioConfig.active_profile].scenarios[0]?.id ?? null);
        setError(null);
      } catch (nextError) {
        if (!cancelled) setError(nextError instanceof Error ? nextError.message : "Traffic logic could not be loaded.");
      }
    }
    void initial();
    return () => { cancelled = true; };
  }, []);

  useSerialPolling(pollLiveState, 1000, { enabled: true, immediate: false });

  const activeProfile = draftConfig ? draftConfig.profiles[draftConfig.active_profile] : null;
  const scenarios = useMemo(
    () => [...(activeProfile?.scenarios ?? [])].sort((a, b) => a.rank - b.rank || a.id.localeCompare(b.id)),
    [activeProfile],
  );
  const selectedScenario = scenarios.find((item) => item.id === selectedScenarioId) ?? scenarios[0] ?? null;
  const countableZones = zones.filter((item) => !["ignore", "counting_line"].includes(item.type));
  const dirty = useMemo(
    () => Boolean(savedConfig && draftConfig && JSON.stringify(savedConfig) !== JSON.stringify(draftConfig)),
    [savedConfig, draftConfig],
  );
  const scenarioStatuses = signal?.scenario_status ?? [];
  const statusById = useMemo(
    () => new Map(scenarioStatuses.map((item) => [item.scenario_id, item])),
    [scenarioStatuses],
  );
  const classOptions = useMemo(() => {
    const classes = new Set(KNOWN_CLASSES);
    Object.values(traffic?.zone_class_counts ?? {}).forEach((counts) => Object.keys(counts).forEach((name) => classes.add(name)));
    return [...classes];
  }, [traffic]);

  function mutateConfig(mutator: (next: ScenarioSignalRulesConfig) => void) {
    if (!draftConfig) return;
    const next = cloneConfig(draftConfig);
    mutator(next);
    setDraftConfig(next);
    setNotice(null);
  }

  function mutateScenario(scenarioId: string, mutator: (scenario: SignalScenario) => void) {
    mutateConfig((next) => {
      const scenario = next.profiles[next.active_profile].scenarios.find((item) => item.id === scenarioId);
      if (scenario) mutator(scenario);
    });
  }

  function updatePhase(phaseKey: SignalPhaseKey, field: "base_seconds" | "min_seconds" | "max_seconds", value: number) {
    mutateConfig((next) => { next.profiles[next.active_profile].phases[phaseKey][field] = value; });
  }

  function addScenario() {
    if (!activeProfile) return;
    const scenario = defaultScenario(countableZones, activeProfile.scenarios);
    mutateConfig((next) => { next.profiles[next.active_profile].scenarios.push(scenario); });
    setSelectedScenarioId(scenario.id);
    setTab("scenarios");
  }

  function duplicateScenario(source: SignalScenario) {
    const duplicate = JSON.parse(JSON.stringify(source)) as SignalScenario;
    duplicate.id = `scenario_${Date.now().toString(36)}`;
    duplicate.label = `${source.label} copy`;
    duplicate.rank = scenarios.length === 0 ? 10 : Math.min(10000, Math.max(...scenarios.map((item) => item.rank)) + 10);
    mutateConfig((next) => { next.profiles[next.active_profile].scenarios.push(duplicate); });
    setSelectedScenarioId(duplicate.id);
  }

  function deleteScenario(scenario: SignalScenario) {
    if (!window.confirm(`Delete scenario “${scenario.label}”? This removes only this draft scenario after you Save Rules.`)) return;
    mutateConfig((next) => {
      const profile = next.profiles[next.active_profile];
      profile.scenarios = profile.scenarios.filter((item) => item.id !== scenario.id);
    });
    const remaining = scenarios.filter((item) => item.id !== scenario.id);
    setSelectedScenarioId(remaining[0]?.id ?? null);
  }

  function addCondition(scenario: SignalScenario) {
    if (scenario.conditions.length >= 8) return;
    mutateScenario(scenario.id, (next) => {
      const firstZone = countableZones[0];
      next.conditions.push(firstZone
        ? { source: "zone_class_count", zone_id: firstZone.id, class_name: "person", operator: "gt", threshold: 0 }
        : { source: "metric", metric: "pedestrians_waiting", operator: "gt", threshold: 0 });
    });
  }

  function changeConditionSource(scenario: SignalScenario, index: number, source: "metric" | "zone_class_count") {
    mutateScenario(scenario.id, (next) => {
      if (source === "metric") {
        next.conditions[index] = { source: "metric", metric: "pedestrians_waiting", operator: "gt", threshold: 0 };
      } else {
        next.conditions[index] = {
          source: "zone_class_count",
          zone_id: countableZones[0]?.id ?? "zone",
          class_name: "person",
          operator: "gt",
          threshold: 0,
        };
      }
    });
  }

  function removeCondition(scenario: SignalScenario, index: number) {
    if (scenario.conditions.length <= 1) return;
    mutateScenario(scenario.id, (next) => { next.conditions.splice(index, 1); });
  }

  async function save() {
    if (!draftConfig) return;
    setSaving(true);
    try {
      const config = await saveSignalRules(draftConfig) as unknown as ScenarioSignalRulesConfig;
      setSavedConfig(config);
      setDraftConfig(cloneConfig(config));
      setNotice("Signal scenarios saved. Rank 1 is highest; only the highest-ranked eligible triggered scenario executes each evaluation.");
      setError(null);
      await pollLiveState();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Signal scenarios could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function resetDefaults() {
    if (!window.confirm("Reset signal timing and scenario rules to source defaults? Runtime datasets, models, zones, analytics and experiment results are not deleted.")) return;
    setSaving(true);
    try {
      const config = await resetSignalRules() as unknown as ScenarioSignalRulesConfig;
      setSavedConfig(config);
      setDraftConfig(cloneConfig(config));
      setSelectedScenarioId(config.profiles[config.active_profile].scenarios[0]?.id ?? null);
      setNotice("Default signal timing and ranked scenarios restored.");
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Signal scenarios could not be reset.");
    } finally {
      setSaving(false);
    }
  }

  async function applyTestInputs() {
    try {
      const next = await setSignalTestInputs(testInputs);
      setTestInputs(next);
      await pollLiveState();
      setNotice("Manual test inputs applied. Mobility/fall flags are Test-mode inputs only.");
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Test inputs could not be applied.");
    }
  }

  async function previewLiveObservation() {
    try {
      const next = await previewSignalRules({
        phase_key: signal?.phase_key && PHASE_KEYS.includes(signal.phase_key as SignalPhaseKey) ? signal.phase_key : "vehicle_green",
        pedestrians_waiting: traffic?.pedestrians_waiting ?? 0,
        pedestrians_crossing: traffic?.pedestrians_crossing ?? 0,
        vehicles_waiting: traffic?.vehicles_waiting ?? 0,
        zone_class_counts: traffic?.zone_class_counts ?? {},
      });
      setPreview(next);
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Scenario preview failed.");
    }
  }

  function setProfile(name: string) {
    mutateConfig((next) => { next.active_profile = name; });
    const profile = draftConfig?.profiles[name];
    setSelectedScenarioId(profile?.scenarios[0]?.id ?? null);
  }

  return (
    <div className="page-stack signal-rules-page">
      <datalist id="signal-scenario-class-options">{classOptions.map((name) => <option key={name} value={name}>{name === "*" ? "All detected classes" : name}</option>)}</datalist>
      <section className="panel signal-policy-toolbar">
        <div className="panel-header">
          <div>
            <h2>Signal Timing & Scenario Rules</h2>
            <p className="placeholder-copy">Build conditions such as “car count &gt; 5 in Queue A”, rank the scenarios, and define the bounded signal response. Only one eligible scenario wins each arbitration evaluation.</p>
          </div>
          <div className="signal-toolbar-actions">
            <span className={signal?.winning_scenario_id ? "status-pill status-secondary" : "status-pill muted"}>
              {signal?.winning_scenario_label ? `Winner: ${signal.winning_scenario_label}` : "No scenario winner"}
            </span>
            {dirty && <span className="status-pill status-planned">unsaved</span>}
          </div>
        </div>

        <div className="signal-tabs" role="tablist" aria-label="Signal rule panels">
          {([
            ["live", "Live Decision"],
            ["timing", "Signal Timing"],
            ["scenarios", "Scenario Rules"],
            ["test", "Test & Safety"],
            ["history", "History"],
          ] as [TabId, string][]).map(([id, label]) => (
            <button key={id} type="button" className={tab === id ? "signal-tab active" : "signal-tab"} onClick={() => setTab(id)}>{label}</button>
          ))}
        </div>

        {draftConfig && (
          <div className="signal-config-bar">
            <label>Mode
              <select value={draftConfig.mode} onChange={(event) => mutateConfig((next) => { next.mode = event.target.value as ScenarioSignalRulesConfig["mode"]; })}>
                <option value="fixed">Fixed</option>
                <option value="adaptive">Adaptive scenarios</option>
                <option value="test">Test scenarios</option>
              </select>
            </label>
            <label>Profile
              <select value={draftConfig.active_profile} onChange={(event) => setProfile(event.target.value)}>
                {Object.keys(draftConfig.profiles).map((name) => <option key={name} value={name}>{name}</option>)}
              </select>
            </label>
            <label className="inline-check"><input type="checkbox" checked={draftConfig.dry_run} onChange={(event) => mutateConfig((next) => { next.dry_run = event.target.checked; })} /> Dry run</label>
            <button className="button primary" type="button" disabled={!dirty || saving} onClick={() => void save()}>{saving ? "Saving..." : "Save Rules"}</button>
            <button className="button" type="button" disabled={!dirty || !savedConfig} onClick={() => savedConfig && setDraftConfig(cloneConfig(savedConfig))}>Discard</button>
            <button className="button" type="button" disabled={saving} onClick={() => void resetDefaults()}>Reset Defaults</button>
          </div>
        )}
        <p className="small-note">Rank <strong>1</strong> is highest. Triggered scenarios that are unavailable for the current phase or still in cooldown do not block the next eligible ranked scenario. Yellow and all-red ordering/minimums remain protected.</p>
        <p className="small-note">This controller is for the local model/simulation only and is not connected to physical or public-road traffic infrastructure.</p>
        {notice && <p className="success-message">{notice}</p>}
        {error && <p className="error-message">{error}</p>}
      </section>

      {tab === "live" && (
        <div className="signal-tab-body">
          <div className="two-column-grid">
            <section className="panel">
              <div className="panel-header">
                <div><h2>Live controller</h2><p className="placeholder-copy">Current protected phase and winning scenario.</p></div>
                <span className={phaseClass(signal?.phase)}>{signal?.phase?.split("_").join(" ") ?? "checking"}</span>
              </div>
              {signal ? (
                <>
                  <div className="metric-grid signal-live-metrics">
                    <div className="metric-card"><span>Base duration</span><strong>{signal.base_duration_seconds.toFixed(1)}s</strong></div>
                    <div className="metric-card"><span>Effective duration</span><strong>{signal.effective_duration_seconds.toFixed(1)}s</strong></div>
                    <div className="metric-card"><span>Remaining</span><strong>{signal.seconds_remaining.toFixed(1)}s</strong></div>
                    <div className="metric-card"><span>Next phase</span><strong>{signal.next_phase.split("_").join(" ")}</strong></div>
                    <div className="metric-card"><span>Pending service</span><strong>{signal.pending_request ?? "none"}</strong></div>
                    <div className="metric-card"><span>Scenario winner</span><strong>{signal.winning_scenario_label ?? "none"}</strong></div>
                  </div>
                  <div className="camera-status-list training-status-list">
                    <div><span>Mode</span><strong>{signal.mode}{signal.dry_run ? " / dry run" : ""}</strong></div>
                    <div><span>Profile</span><strong>{signal.active_profile}</strong></div>
                    <div><span>Observation</span><strong>{signal.data_fresh ? "fresh" : "fallback"}</strong></div>
                    <div><span>Phase key</span><strong>{signal.phase_key}</strong></div>
                  </div>
                </>
              ) : <p>Loading controller state...</p>}
              {signal?.fallback_reason && <p className="warning-box">{signal.fallback_reason}</p>}
              {signal?.incident_hold && <p className="error-message">Simulation incident hold is active. Clear it from Test & Safety.</p>}
            </section>

            <section className="panel">
              <div className="panel-header"><div><h2>Rank arbitration</h2><p className="placeholder-copy">Lower rank number wins among eligible triggered scenarios.</p></div><span className="status-pill muted">{scenarioStatuses.length} scenarios</span></div>
              <div className="scenario-arbitration-list">
                {scenarioStatuses.length === 0 ? <p className="placeholder-copy">No scenarios are configured in this profile.</p> : scenarioStatuses.map((item) => (
                  <article key={item.scenario_id} className={item.state === "winner" ? "scenario-arbitration-item winner" : "scenario-arbitration-item"}>
                    <div className="scenario-rank-badge">#{item.rank}</div>
                    <div className="scenario-arbitration-copy"><strong>{item.label}</strong><p>{item.reason}</p></div>
                    <span className={statusClass(item.state)}>{item.state}</span>
                  </article>
                ))}
              </div>
            </section>
          </div>

          <section className="panel">
            <div className="panel-header"><div><h2>Live zone / class observation</h2><p className="placeholder-copy">These per-frame class counts are the values available to zone/class scenario conditions.</p></div><button type="button" onClick={() => void previewLiveObservation()}>Preview current observation</button></div>
            <div className="scenario-zone-grid">
              {countableZones.length === 0 ? <p className="placeholder-copy">Create zones first to use zone/class scenario conditions.</p> : countableZones.map((zone) => {
                const counts = traffic?.zone_class_counts?.[zone.id] ?? {};
                return (
                  <article className="scenario-zone-card" key={zone.id}>
                    <div><strong>{zone.label}</strong><small>{zone.id} · {zone.type.replaceAll("_", " ")}</small></div>
                    <div className="scenario-zone-counts">
                      {Object.keys(counts).length === 0 ? <span>no detections</span> : Object.entries(counts).map(([name, count]) => <span key={name}>{name}: <strong>{count}</strong></span>)}
                    </div>
                  </article>
                );
              })}
            </div>
            {preview && <p className="small-note">Preview winner: <strong>{(preview as SignalRulesPreview & { winning_scenario_id?: string | null }).winning_scenario_id ?? "none"}</strong>; effective phase duration {preview.effective_duration_seconds.toFixed(1)}s. Preview does not mutate the running controller.</p>}
          </section>
        </div>
      )}

      {tab === "timing" && activeProfile && (
        <div className="signal-tab-body">
          <section className="panel">
            <div className="panel-header"><div><h2>Protected signal timing</h2><p className="placeholder-copy">Fixed mode uses base timing directly. Scenario actions can only adjust within these bounds and the cycle cap.</p></div><span className="status-pill muted">protected sequence</span></div>
            <div className="signal-timing-table-wrap">
              <table className="signal-timing-table">
                <thead><tr><th>Phase</th><th>Minimum</th><th>Base</th><th>Maximum</th></tr></thead>
                <tbody>{PHASE_KEYS.map((phaseKey) => {
                  const phase = activeProfile.phases[phaseKey];
                  return <tr key={phaseKey}>
                    <td><strong>{PHASE_LABELS[phaseKey]}</strong></td>
                    <td><input type="number" min="0" step="0.5" value={phase.min_seconds} onChange={(event) => updatePhase(phaseKey, "min_seconds", numeric(event.target.value))} /></td>
                    <td><input type="number" min="0" step="0.5" value={phase.base_seconds} onChange={(event) => updatePhase(phaseKey, "base_seconds", numeric(event.target.value))} /></td>
                    <td><input type="number" min="0" step="0.5" value={phase.max_seconds} onChange={(event) => updatePhase(phaseKey, "max_seconds", numeric(event.target.value))} /></td>
                  </tr>;
                })}</tbody>
              </table>
            </div>
          </section>
          <section className="panel">
            <div className="panel-header"><h2>Controller guards</h2><span className="status-pill muted">profile</span></div>
            <div className="scenario-guard-grid">
              <label>Maximum cycle seconds<input type="number" min="1" step="1" value={activeProfile.max_cycle_seconds} onChange={(event) => mutateConfig((next) => { next.profiles[next.active_profile].max_cycle_seconds = numeric(event.target.value); })} /></label>
              <label>Stale observation timeout<input type="number" min="1" max="30" step="0.5" value={activeProfile.stale_data_seconds} onChange={(event) => mutateConfig((next) => { next.profiles[next.active_profile].stale_data_seconds = numeric(event.target.value); })} /></label>
              <label>Demand memory seconds<input type="number" min="0" max="30" step="0.5" value={activeProfile.demand_memory_seconds} onChange={(event) => mutateConfig((next) => { next.profiles[next.active_profile].demand_memory_seconds = numeric(event.target.value); })} /></label>
            </div>
          </section>
        </div>
      )}

      {tab === "scenarios" && activeProfile && (
        <div className="signal-tab-body">
          <section className="panel">
            <div className="panel-header">
              <div><h2>Ranked scenario rules</h2><p className="placeholder-copy">Define one or more conditions, then choose the bounded signal action. Conditions can use a controller metric or a detected class count inside a specific zone.</p></div>
              <button className="primary" type="button" onClick={addScenario}>Add scenario</button>
            </div>
            <div className="scenario-workspace">
              <div className="scenario-list-panel" aria-label="Scenario list">
                {scenarios.length === 0 ? (
                  <div className="scenario-empty"><p>No scenarios in this profile.</p><button type="button" onClick={addScenario}>Create first scenario</button></div>
                ) : scenarios.map((scenario) => {
                  const liveStatus = statusById.get(scenario.id);
                  return (
                    <button key={scenario.id} type="button" className={selectedScenario?.id === scenario.id ? "scenario-list-item active" : "scenario-list-item"} onClick={() => setSelectedScenarioId(scenario.id)}>
                      <span className="scenario-list-rank">#{scenario.rank}</span>
                      <span className="scenario-list-copy"><strong>{scenario.label}</strong><small>{conditionText(scenario.conditions[0], zones)}{scenario.conditions.length > 1 ? ` +${scenario.conditions.length - 1}` : ""}</small></span>
                      <span className={statusClass(liveStatus?.state ?? "inactive")}>{liveStatus?.state ?? (scenario.enabled ? "ready" : "disabled")}</span>
                    </button>
                  );
                })}
              </div>

              {selectedScenario ? (
                <div className="scenario-editor">
                  <div className="scenario-editor-header">
                    <div><h3>{selectedScenario.label}</h3><p>Scenario id: <code>{selectedScenario.id}</code></p></div>
                    <div className="button-row wrap-row"><button type="button" onClick={() => duplicateScenario(selectedScenario)}>Duplicate</button><button className="danger" type="button" onClick={() => deleteScenario(selectedScenario)}>Delete</button></div>
                  </div>

                  <div className="scenario-editor-section">
                    <h4>Identity & arbitration</h4>
                    <div className="scenario-form-grid">
                      <label>Name<input value={selectedScenario.label} maxLength={120} onChange={(event) => mutateScenario(selectedScenario.id, (next) => { next.label = event.target.value; })} /></label>
                      <label>Rank <span className="field-hint">1 = highest</span><input type="number" min="1" max="10000" value={selectedScenario.rank} onChange={(event) => mutateScenario(selectedScenario.id, (next) => { next.rank = numeric(event.target.value, 1); })} /></label>
                      <label>Condition logic<select value={selectedScenario.match} onChange={(event) => mutateScenario(selectedScenario.id, (next) => { next.match = event.target.value as SignalScenario["match"]; })}><option value="all">ALL conditions must match</option><option value="any">ANY condition may match</option></select></label>
                      <label className="inline-check scenario-enabled"><input type="checkbox" checked={selectedScenario.enabled} onChange={(event) => mutateScenario(selectedScenario.id, (next) => { next.enabled = event.target.checked; })} /> Scenario enabled</label>
                    </div>
                  </div>

                  <div className="scenario-editor-section">
                    <div className="scenario-section-heading"><div><h4>Trigger conditions</h4><p>Example: <strong>car &gt; 5 in Vehicle Queue A</strong>.</p></div><button type="button" disabled={selectedScenario.conditions.length >= 8} onClick={() => addCondition(selectedScenario)}>Add condition</button></div>
                    <div className="scenario-condition-list">
                      {selectedScenario.conditions.map((condition, index) => (
                        <div className="scenario-condition-row" key={`${selectedScenario.id}-${index}`}>
                          <span className="scenario-condition-index">{index + 1}</span>
                          <label>Source<select value={condition.source} onChange={(event) => changeConditionSource(selectedScenario, index, event.target.value as "metric" | "zone_class_count")}><option value="zone_class_count">Zone / class count</option><option value="metric">Controller metric</option></select></label>
                          {condition.source === "zone_class_count" ? (
                            <>
                              <label>Zone<select value={condition.zone_id} onChange={(event) => mutateScenario(selectedScenario.id, (next) => { const item = next.conditions[index]; if (item.source === "zone_class_count") item.zone_id = event.target.value; })}>{countableZones.length === 0 && <option value={condition.zone_id}>{condition.zone_id}</option>}{countableZones.map((zone) => <option key={zone.id} value={zone.id}>{zone.label} ({zone.id})</option>)}</select></label>
                              <label>Class<input list="signal-scenario-class-options" value={condition.class_name} onChange={(event) => mutateScenario(selectedScenario.id, (next) => { const item = next.conditions[index]; if (item.source === "zone_class_count") item.class_name = event.target.value; })} /></label>
                            </>
                          ) : (
                            <label className="scenario-condition-wide">Metric<select value={condition.metric} onChange={(event) => mutateScenario(selectedScenario.id, (next) => { const item = next.conditions[index]; if (item.source === "metric") item.metric = event.target.value as SignalMetric; })}>{METRICS.map((item) => <option key={item.value} value={item.value}>{item.label}{item.testOnly ? " (Test only)" : ""}</option>)}</select></label>
                          )}
                          <label>Compare<select value={condition.operator} onChange={(event) => mutateScenario(selectedScenario.id, (next) => { next.conditions[index].operator = event.target.value as ScenarioCondition["operator"]; })}>{OPERATORS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
                          <label>Threshold<input type="number" step="0.1" value={condition.threshold} onChange={(event) => mutateScenario(selectedScenario.id, (next) => { next.conditions[index].threshold = numeric(event.target.value); })} /></label>
                          <button type="button" className="scenario-remove-condition" disabled={selectedScenario.conditions.length <= 1} onClick={() => removeCondition(selectedScenario, index)}>Remove</button>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="scenario-editor-section">
                    <h4>Signal response</h4>
                    <div className="scenario-form-grid response-grid">
                      <label>Action<select value={selectedScenario.action.type} onChange={(event) => mutateScenario(selectedScenario.id, (next) => { next.action.type = event.target.value as SignalScenario["action"]["type"]; if (next.action.type === "request_next_phase" && !next.action.request_service) next.action.request_service = "pedestrian"; })}>{ACTIONS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
                      <label>Adjustment seconds<input type="number" min="0" max="60" step="0.5" disabled={selectedScenario.action.type === "incident_hold"} value={selectedScenario.action.adjustment_seconds} onChange={(event) => mutateScenario(selectedScenario.id, (next) => { next.action.adjustment_seconds = numeric(event.target.value); })} /></label>
                      <label>Requested service<select value={selectedScenario.action.request_service ?? ""} onChange={(event) => mutateScenario(selectedScenario.id, (next) => { next.action.request_service = (event.target.value || null) as SignalScenario["action"]["request_service"]; })}><option value="">None</option><option value="pedestrian">Pedestrian</option><option value="vehicle">Vehicle</option></select></label>
                    </div>
                    <div className="scenario-phase-targets">
                      <span>Action may execute during:</span>
                      {PHASE_KEYS.map((phaseKey) => <label key={phaseKey} className="inline-check"><input type="checkbox" checked={selectedScenario.action.target_phases.includes(phaseKey)} onChange={(event) => mutateScenario(selectedScenario.id, (next) => { const targets = new Set(next.action.target_phases); if (event.target.checked) targets.add(phaseKey); else targets.delete(phaseKey); next.action.target_phases = [...targets]; })} /> {PHASE_LABELS[phaseKey]}</label>)}
                    </div>
                  </div>

                  <div className="scenario-editor-section">
                    <h4>Stability guards</h4>
                    <div className="scenario-form-grid">
                      <label>Persistence seconds <span className="field-hint">condition must stay true</span><input type="number" min="0" max="120" step="0.5" value={selectedScenario.persistence_seconds} onChange={(event) => mutateScenario(selectedScenario.id, (next) => { next.persistence_seconds = numeric(event.target.value); })} /></label>
                      <label>Cooldown seconds <span className="field-hint">before this scenario can reapply</span><input type="number" min="0" max="600" step="0.5" value={selectedScenario.cooldown_seconds} onChange={(event) => mutateScenario(selectedScenario.id, (next) => { next.cooldown_seconds = numeric(event.target.value); })} /></label>
                    </div>
                    {statusById.get(selectedScenario.id) && <ScenarioStatusDetail status={statusById.get(selectedScenario.id)!} />}
                  </div>
                </div>
              ) : <div className="scenario-editor scenario-empty"><p>Select or create a scenario.</p></div>}
            </div>
          </section>
        </div>
      )}

      {tab === "test" && (
        <div className="signal-tab-body">
          <div className="two-column-grid">
            <section className="panel">
              <div className="panel-header"><div><h2>Manual Test-mode inputs</h2><p className="placeholder-copy">Use these only to exercise metric conditions. Zone/class scenarios continue to use live zone observations.</p></div><span className="status-pill muted">Test mode only</span></div>
              <div className="scenario-form-grid">
                <label>Pedestrians waiting<input type="number" min="0" max="500" value={testInputs.pedestrians_waiting} onChange={(event) => setTestInputs((current) => ({ ...current, pedestrians_waiting: numeric(event.target.value) }))} /></label>
                <label>Pedestrians crossing<input type="number" min="0" max="500" value={testInputs.pedestrians_crossing} onChange={(event) => setTestInputs((current) => ({ ...current, pedestrians_crossing: numeric(event.target.value) }))} /></label>
                <label>Vehicles waiting<input type="number" min="0" max="500" value={testInputs.vehicles_waiting} onChange={(event) => setTestInputs((current) => ({ ...current, vehicles_waiting: numeric(event.target.value) }))} /></label>
                <label className="inline-check"><input type="checkbox" checked={testInputs.mobility_assistance} onChange={(event) => setTestInputs((current) => ({ ...current, mobility_assistance: event.target.checked }))} /> Mobility assistance test flag</label>
                <label className="inline-check"><input type="checkbox" checked={testInputs.incident_person_fallen} onChange={(event) => setTestInputs((current) => ({ ...current, incident_person_fallen: event.target.checked }))} /> Fallen-person incident test flag</label>
              </div>
              <div className="button-row wrap-row"><button className="primary" type="button" onClick={() => void applyTestInputs()}>Apply test inputs</button><button type="button" onClick={() => void previewLiveObservation()}>Preview current observation</button></div>
              <p className="small-note">These flags do not mean the current perception model detects mobility assistance or falls.</p>
            </section>

            <section className="panel">
              <div className="panel-header"><h2>Runtime controls</h2><span className="status-pill muted">transient state</span></div>
              <div className="button-stack">
                <button type="button" onClick={async () => { await resetSignalRulesRuntime(); await pollLiveState(); setNotice("Scenario persistence/cooldown/pending runtime state reset."); }}>Reset scenario runtime state</button>
                <button type="button" onClick={async () => { await clearSignalIncident(); await pollLiveState(); setNotice("Simulation incident hold cleared."); }}>Clear incident hold</button>
              </div>
              <p className="small-note">Resetting runtime state does not delete the saved scenario configuration.</p>
            </section>
          </div>
        </div>
      )}

      {tab === "history" && (
        <div className="signal-tab-body">
          <section className="panel">
            <div className="panel-header"><div><h2>Scenario decision history</h2><p className="placeholder-copy">Phase changes, configuration saves, incident state and executed scenario adjustments.</p></div><div className="button-row wrap-row"><button type="button" onClick={() => void refreshHistory()}>Refresh</button><button className="danger" type="button" onClick={async () => { if (!window.confirm("Clear signal decision history only? Saved rules, zones, datasets, analytics, models and experiments are unchanged.")) return; await clearSignalDecisionHistory(); await refreshHistory(); }}>Clear history</button></div></div>
            <div className="scenario-history-wrap">
              <table className="scenario-history-table">
                <thead><tr><th>Time</th><th>Event</th><th>Scenario / phase</th><th>Details</th></tr></thead>
                <tbody>{[...(history?.events ?? [])].reverse().map((event, index) => {
                  const scenario = String(event.details.scenario_label ?? event.details.scenario_id ?? event.details.rule_id ?? event.details.phase_key ?? event.details.to ?? "—");
                  return <tr key={`${event.timestamp_ms}-${index}`}><td>{new Date(event.timestamp_ms).toLocaleTimeString()}</td><td>{event.event_type.replaceAll("_", " ")}</td><td>{scenario}</td><td><code>{JSON.stringify(event.details)}</code></td></tr>;
                })}</tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function ScenarioStatusDetail({ status }: { status: SignalScenarioStatus }) {
  return (
    <div className="scenario-live-detail">
      <div><strong>Live state</strong><span className={statusClass(status.state)}>{status.state}</span></div>
      <p>{status.reason}</p>
      {status.conditions.length > 0 && <div className="scenario-live-conditions">{status.conditions.map((condition, index) => <span key={`${condition.label}-${index}`} className={condition.matched ? "matched" : ""}>{condition.label}: {condition.observed} {OPERATORS.find((item) => item.value === condition.operator)?.label} {condition.threshold}</span>)}</div>}
    </div>
  );
}
