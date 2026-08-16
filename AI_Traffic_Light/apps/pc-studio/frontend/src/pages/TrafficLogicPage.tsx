import { useEffect, useMemo, useState } from "react";
import {
  clearSignalDecisionHistory,
  clearSignalIncident,
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
import { FunctionChecklist } from "../components/FunctionChecklist";
import type {
  SignalDecisionHistory,
  SignalPhaseKey,
  SignalRulesConfig,
  SignalRulesPreview,
  SignalStatus,
  SignalTestInputs,
  TrafficState,
} from "../types";
import "./signalRules.css";

type TabId = "live" | "timing" | "rules" | "safety" | "history";

const PHASE_LABELS: Record<SignalPhaseKey, string> = {
  vehicle_green: "Vehicle green",
  vehicle_yellow: "Vehicle yellow",
  all_red_to_pedestrian: "All red → pedestrian",
  pedestrian_green: "Pedestrian WALK",
  pedestrian_flashing: "Pedestrian CLEAR",
  all_red_to_vehicle: "All red → vehicles",
};

function phaseClass(phase: string | undefined): string {
  if (phase === "pedestrian_green" || phase === "vehicle_green") return "status-pill status-implemented";
  if (phase === "vehicle_yellow" || phase === "pedestrian_flashing") return "status-pill status-planned";
  return "status-pill";
}

function cloneConfig(config: SignalRulesConfig): SignalRulesConfig {
  return JSON.parse(JSON.stringify(config)) as SignalRulesConfig;
}

function numeric(value: string, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function TrafficLogicPage() {
  const [tab, setTab] = useState<TabId>("live");
  const [traffic, setTraffic] = useState<TrafficState | null>(null);
  const [signal, setSignal] = useState<SignalStatus | null>(null);
  const [savedConfig, setSavedConfig] = useState<SignalRulesConfig | null>(null);
  const [draftConfig, setDraftConfig] = useState<SignalRulesConfig | null>(null);
  const [history, setHistory] = useState<SignalDecisionHistory | null>(null);
  const [preview, setPreview] = useState<SignalRulesPreview | null>(null);
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

  async function loadConfiguration() {
    const config = await fetchSignalRules();
    setSavedConfig(config);
    setDraftConfig(cloneConfig(config));
  }

  async function refreshHistory() {
    setHistory(await fetchSignalDecisionHistory(250));
  }

  useEffect(() => {
    let cancelled = false;
    async function initial() {
      try {
        const [nextTraffic, nextSignal, config, nextHistory] = await Promise.all([
          fetchTrafficState(),
          fetchSignalStatus(),
          fetchSignalRules(),
          fetchSignalDecisionHistory(250),
        ]);
        if (cancelled) return;
        setTraffic(nextTraffic);
        setSignal(nextSignal);
        setSavedConfig(config);
        setDraftConfig(cloneConfig(config));
        setHistory(nextHistory);
        setTestInputs(nextSignal.test_inputs);
        setError(null);
      } catch (nextError) {
        if (!cancelled) setError(nextError instanceof Error ? nextError.message : "Traffic logic could not be loaded.");
      }
    }
    void initial();
    const timer = window.setInterval(async () => {
      try {
        const [nextTraffic, nextSignal] = await Promise.all([fetchTrafficState(), fetchSignalStatus()]);
        if (!cancelled) {
          setTraffic(nextTraffic);
          setSignal(nextSignal);
          setTestInputs(nextSignal.test_inputs);
        }
      } catch (nextError) {
        if (!cancelled) setError(nextError instanceof Error ? nextError.message : "Traffic state could not be evaluated.");
      }
    }, 1000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const activeProfile = draftConfig ? draftConfig.profiles[draftConfig.active_profile] : null;
  const dirty = useMemo(
    () => Boolean(savedConfig && draftConfig && JSON.stringify(savedConfig) !== JSON.stringify(draftConfig)),
    [savedConfig, draftConfig],
  );

  function mutateConfig(mutator: (next: SignalRulesConfig) => void) {
    if (!draftConfig) return;
    const next = cloneConfig(draftConfig);
    mutator(next);
    setDraftConfig(next);
    setNotice(null);
  }

  function updatePhase(phaseKey: SignalPhaseKey, field: "base_seconds" | "min_seconds" | "max_seconds", value: number) {
    mutateConfig((next) => {
      next.profiles[next.active_profile].phases[phaseKey][field] = value;
    });
  }

  function updateRule(ruleId: string, field: string, value: boolean | number | string) {
    mutateConfig((next) => {
      const rule = next.profiles[next.active_profile].rules[ruleId] as Record<string, unknown>;
      rule[field] = value;
    });
  }

  async function save() {
    if (!draftConfig) return;
    setSaving(true);
    try {
      const config = await saveSignalRules(draftConfig);
      setSavedConfig(config);
      setDraftConfig(cloneConfig(config));
      setNotice("Signal policy saved. The simulator will use the validated policy on the next evaluation.");
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Signal policy could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function resetDefaults() {
    setSaving(true);
    try {
      const config = await resetSignalRules();
      setSavedConfig(config);
      setDraftConfig(cloneConfig(config));
      setNotice("Factory signal-rule defaults restored.");
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Signal rules could not be reset.");
    } finally {
      setSaving(false);
    }
  }

  async function applyTestInputs() {
    try {
      const next = await setSignalTestInputs(testInputs);
      setTestInputs(next);
      setSignal(await fetchSignalStatus());
      setNotice("Simulation/test inputs applied. They only affect Test mode.");
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Test inputs could not be applied.");
    }
  }

  async function runPreview(input: Record<string, unknown>) {
    try {
      setPreview(await previewSignalRules(input));
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Rule preview failed.");
    }
  }

  const zoneCounts = Object.entries(traffic?.zone_counts ?? {});
  const regionCounts = Object.entries(traffic?.region_counts ?? {});

  return (
    <div className="page-stack signal-rules-page">
      <section className="panel signal-policy-toolbar">
        <div className="panel-header">
          <div>
            <h2>Signal Rules & Adaptive Timing</h2>
            <p className="placeholder-copy">Configure and explain the simulated signal controller. This feature never connects to physical/public-road signal infrastructure.</p>
          </div>
          <div className="signal-toolbar-actions">
            <span className={signal?.data_fresh ? "status-pill status-implemented" : "status-pill status-planned"}>
              {signal?.data_fresh ? "adaptive data ready" : signal?.mode === "fixed" ? "fixed timing" : "fallback timing"}
            </span>
            {dirty && <span className="status-pill status-planned">unsaved</span>}
          </div>
        </div>
        <div className="signal-tabs" role="tablist" aria-label="Signal rule panels">
          {([
            ["live", "Live Decision"],
            ["timing", "Normal Timing"],
            ["rules", "Adaptive Rules"],
            ["safety", "Safety & Test"],
            ["history", "Decision History"],
          ] as [TabId, string][]).map(([id, label]) => (
            <button key={id} type="button" className={tab === id ? "signal-tab active" : "signal-tab"} onClick={() => setTab(id)}>{label}</button>
          ))}
        </div>
        {draftConfig && (
          <div className="signal-config-bar">
            <label>Mode
              <select value={draftConfig.mode} onChange={(event) => mutateConfig((next) => { next.mode = event.target.value as SignalRulesConfig["mode"]; })}>
                <option value="fixed">Fixed</option>
                <option value="adaptive">Adaptive</option>
                <option value="test">Test</option>
              </select>
            </label>
            <label>Profile
              <select value={draftConfig.active_profile} onChange={(event) => mutateConfig((next) => { next.active_profile = event.target.value; })}>
                {Object.keys(draftConfig.profiles).map((name) => <option key={name} value={name}>{name}</option>)}
              </select>
            </label>
            <label className="inline-check"><input type="checkbox" checked={draftConfig.dry_run} onChange={(event) => mutateConfig((next) => { next.dry_run = event.target.checked; })} /> Dry run</label>
            <button className="button primary" type="button" disabled={!dirty || saving} onClick={() => void save()}>{saving ? "Saving..." : "Save Rules"}</button>
            <button className="button" type="button" disabled={!dirty || !savedConfig} onClick={() => savedConfig && setDraftConfig(cloneConfig(savedConfig))}>Discard</button>
            <button className="button" type="button" disabled={saving} onClick={() => void resetDefaults()}>Reset Defaults</button>
          </div>
        )}
        {activeProfile && <p className="small-note">{activeProfile.description} Base cycle: {Object.values(activeProfile.phases).reduce((sum, phase) => sum + phase.base_seconds, 0).toFixed(1)}s. Maximum configured adaptive cycle: {activeProfile.max_cycle_seconds.toFixed(1)}s.</p>}
        {notice && <p className="success-message">{notice}</p>}
        {error && <p className="error-message">{error}</p>}
      </section>

      {tab === "live" && (
        <>
          <div className="two-column-grid">
            <section className="panel">
              <div className="panel-header"><div><h2>Live controller</h2><p className="placeholder-copy">The phase synthetic agents actually obey.</p></div><span className={phaseClass(signal?.phase)}>{signal?.phase?.split("_").join(" ") ?? "checking"}</span></div>
              {signal ? (
                <div className="metric-grid">
                  <div className="metric-card"><span>Base duration</span><strong>{signal.base_duration_seconds.toFixed(1)}s</strong></div>
                  <div className="metric-card"><span>Effective duration</span><strong>{signal.effective_duration_seconds.toFixed(1)}s</strong></div>
                  <div className="metric-card"><span>Remaining</span><strong>{signal.seconds_remaining.toFixed(1)}s</strong></div>
                  <div className="metric-card"><span>Next phase</span><strong>{signal.next_phase.split("_").join(" ")}</strong></div>
                  <div className="metric-card"><span>Pending request</span><strong>{signal.pending_request ?? "none"}</strong></div>
                  <div className="metric-card"><span>Active rules</span><strong>{signal.active_rules.length}</strong></div>
                </div>
              ) : <p>Loading controller state...</p>}
              {signal?.fallback_reason && <p className="warning-box">{signal.fallback_reason}</p>}
              {signal?.incident_hold && <p className="error-message">Incident hold active: simulated vehicle movement is held at all-red until explicitly cleared.</p>}
              {signal && (
                <div className="camera-status-list training-status-list">
                  <div><span>Operating mode</span><strong>{signal.mode}{signal.dry_run ? " / dry run" : ""}</strong></div>
                  <div><span>Profile</span><strong>{signal.active_profile}</strong></div>
                  <div><span>Data freshness</span><strong>{signal.data_fresh ? "fresh" : "fallback"}</strong></div>
                  <div><span>Phase key</span><strong>{signal.phase_key}</strong></div>
                </div>
              )}
            </section>

            <section className="panel">
              <div className="panel-header"><h2>Rule arbitration</h2><span className="status-pill">priority ordered</span></div>
              <div className="signal-rule-status-list">
                {(signal?.rule_status ?? []).map((rule) => (
                  <div className="signal-rule-status" key={rule.rule_id}>
                    <div><strong>{rule.label}</strong><p>{rule.reason}</p></div>
                    <span className={`status-pill signal-rule-${rule.state}`}>{rule.state}</span>
                  </div>
                ))}
              </div>
              <p className="small-note">A rule can be active, suppressed by phase/cooldown/fallback constraints, unavailable because its detector does not exist, or inactive because its trigger is not met.</p>
            </section>
          </div>

          <section className="panel">
            <div className="panel-header"><h2>Detection / demand context</h2><span className="status-pill muted">prototype observation</span></div>
            {traffic ? (
              <div className="metric-grid">
                <div className="metric-card"><span>Pedestrians waiting</span><strong>{traffic.pedestrians_waiting}</strong></div>
                <div className="metric-card"><span>Pedestrians crossing</span><strong>{traffic.pedestrians_crossing}</strong></div>
                <div className="metric-card"><span>Vehicles queued</span><strong>{traffic.vehicles_waiting}</strong></div>
                <div className="metric-card"><span>Active tracks</span><strong>{traffic.tracking?.active_track_count ?? 0}</strong></div>
              </div>
            ) : <p>Evaluating current traffic state...</p>}
            {traffic && <p className="reason-text">{traffic.decision_reason}</p>}
          </section>

          <section className="panel">
            <div className="panel-header"><h2>Decision-zone counts</h2><span className="status-pill">live centres</span></div>
            {zoneCounts.length === 0 ? <p className="placeholder-copy">No zone-count result is available yet.</p> : (
              <div className="camera-status-list training-status-list">
                {zoneCounts.map(([zoneId, count]) => <div key={zoneId}><span>{zoneId}</span><strong>{count}</strong></div>)}
              </div>
            )}
          </section>

          <section className="panel">
            <div className="panel-header"><h2>Per-region pedestrian / vehicle counts</h2><span className="status-pill">occupancy</span></div>
            {regionCounts.length === 0 ? <p className="placeholder-copy">No region occupancy result is available yet.</p> : (
              <div className="function-list">
                {regionCounts.map(([zoneId, counts]) => (
                  <article className="function-item" key={zoneId}><div><strong>{zoneId}</strong><p>{counts.pedestrians} pedestrian(s), {counts.vehicles} vehicle(s), {counts.total} total.</p></div><span className="status-pill">{counts.total}</span></article>
                ))}
              </div>
            )}
          </section>
        </>
      )}

      {tab === "timing" && activeProfile && (
        <section className="panel">
          <div className="panel-header"><div><h2>Normal operation timing</h2><p className="placeholder-copy">Base timing is used directly in Fixed mode and as the starting point for Adaptive/Test mode.</p></div><span className="status-pill">protected sequence</span></div>
          <div className="signal-timing-table">
            <div className="signal-timing-row header"><strong>Phase</strong><strong>Minimum</strong><strong>Base</strong><strong>Maximum</strong></div>
            {(Object.keys(PHASE_LABELS) as SignalPhaseKey[]).map((phaseKey) => {
              const timing = activeProfile.phases[phaseKey];
              return (
                <div className="signal-timing-row" key={phaseKey}>
                  <strong>{PHASE_LABELS[phaseKey]}</strong>
                  <input type="number" min={0} step={0.5} value={timing.min_seconds} onChange={(event) => updatePhase(phaseKey, "min_seconds", numeric(event.target.value, timing.min_seconds))} />
                  <input type="number" min={0} step={0.5} value={timing.base_seconds} onChange={(event) => updatePhase(phaseKey, "base_seconds", numeric(event.target.value, timing.base_seconds))} />
                  <input type="number" min={0} step={0.5} value={timing.max_seconds} onChange={(event) => updatePhase(phaseKey, "max_seconds", numeric(event.target.value, timing.max_seconds))} />
                </div>
              );
            })}
          </div>
          <div className="signal-limit-grid">
            <label>Maximum cycle seconds<input type="number" min={1} step={1} value={activeProfile.max_cycle_seconds} onChange={(event) => mutateConfig((next) => { next.profiles[next.active_profile].max_cycle_seconds = numeric(event.target.value, activeProfile.max_cycle_seconds); })} /></label>
            <label>Stale-data fallback after<input type="number" min={1} step={0.5} value={activeProfile.stale_data_seconds} onChange={(event) => mutateConfig((next) => { next.profiles[next.active_profile].stale_data_seconds = numeric(event.target.value, activeProfile.stale_data_seconds); })} /></label>
            <label>Demand memory seconds<input type="number" min={0} step={0.5} value={activeProfile.demand_memory_seconds} onChange={(event) => mutateConfig((next) => { next.profiles[next.active_profile].demand_memory_seconds = numeric(event.target.value, activeProfile.demand_memory_seconds); })} /></label>
          </div>
          <p className="small-note">Yellow and all-red transitions have backend-protected minimums. The API rejects min/base/max inversions and unsupported limits before replacing the saved policy.</p>
        </section>
      )}

      {tab === "rules" && activeProfile && (
        <section className="panel">
          <div className="panel-header"><div><h2>Adaptive rules</h2><p className="placeholder-copy">Structured predefined triggers keep the controller explainable; arbitrary Boolean scripting is intentionally not supported.</p></div><span className="status-pill">{Object.keys(activeProfile.rules).length} rules</span></div>
          <div className="signal-rule-editor-list">
            {Object.entries(activeProfile.rules).sort(([, a], [, b]) => b.priority - a.priority).map(([ruleId, rule]) => (
              <article className="signal-rule-editor" key={ruleId}>
                <div className="signal-rule-editor-head">
                  <label className="inline-check"><input type="checkbox" checked={rule.enabled} onChange={(event) => updateRule(ruleId, "enabled", event.target.checked)} /> <strong>{rule.label}</strong></label>
                  <span className="status-pill">priority {rule.priority}</span>
                </div>
                <p className="small-note">Trigger: <code>{rule.trigger}</code> → <code>{rule.action}</code> during {rule.target_phases.map((key) => PHASE_LABELS[key]).join(", ")}.</p>
                <div className="signal-rule-fields">
                  <label>Threshold<input type="number" min={0} step={0.5} value={rule.threshold} onChange={(event) => updateRule(ruleId, "threshold", numeric(event.target.value, rule.threshold))} /></label>
                  <label>Stable for (s)<input type="number" min={0} step={0.5} value={rule.persistence_seconds} onChange={(event) => updateRule(ruleId, "persistence_seconds", numeric(event.target.value, rule.persistence_seconds))} /></label>
                  <label>Adjustment (s)<input type="number" min={0} step={0.5} value={rule.adjustment_seconds} onChange={(event) => updateRule(ruleId, "adjustment_seconds", numeric(event.target.value, rule.adjustment_seconds))} /></label>
                  <label>Cooldown (s)<input type="number" min={0} step={0.5} value={rule.cooldown_seconds} onChange={(event) => updateRule(ruleId, "cooldown_seconds", numeric(event.target.value, rule.cooldown_seconds))} /></label>
                  <label>Priority<input type="number" min={0} max={10000} step={1} value={rule.priority} onChange={(event) => updateRule(ruleId, "priority", numeric(event.target.value, rule.priority))} /></label>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {tab === "safety" && (
        <>
          <section className="panel">
            <div className="panel-header"><div><h2>Safety, fallback & accessibility</h2><p className="placeholder-copy">These constraints remain bounded even when user rules request timing changes.</p></div><span className="status-pill muted">simulation only</span></div>
            <div className="function-list">
              <article className="function-item"><div><strong>Protected transitions</strong><p>Vehicle green cannot jump directly to pedestrian WALK. Yellow and all-red transitions remain in the sequence.</p></div><span className="status-pill">enforced</span></article>
              <article className="function-item"><div><strong>Minimum service</strong><p>Each phase is clamped to its configured minimum and cannot be shortened below time already served.</p></div><span className="status-pill">enforced</span></article>
              <article className="function-item"><div><strong>Stale-data fallback</strong><p>Adaptive timing stops using stale observations and returns to configured normal timings.</p></div><span className="status-pill">enforced</span></article>
              <article className="function-item"><div><strong>Demand memory / hysteresis</strong><p>Short detection dropouts retain demand briefly; rule persistence prevents single-frame trigger spikes.</p></div><span className="status-pill">enforced</span></article>
              <article className="function-item"><div><strong>Mobility / fall input</strong><p>No live wheelchair or fall detector is claimed. These conditions are available only as explicit Test-mode inputs until a compatible perception model exists.</p></div><span className="status-pill status-planned">test source</span></article>
            </div>
          </section>

          <section className="panel">
            <div className="panel-header"><div><h2>Scenario / test controls</h2><p className="placeholder-copy">Manual values are clearly separated from live detections and only affect Test mode.</p></div><span className="status-pill">manual test</span></div>
            <div className="signal-test-grid">
              <label>Waiting pedestrians<input type="number" min={0} max={500} value={testInputs.pedestrians_waiting} onChange={(event) => setTestInputs((current) => ({ ...current, pedestrians_waiting: numeric(event.target.value) }))} /></label>
              <label>Crossing pedestrians<input type="number" min={0} max={500} value={testInputs.pedestrians_crossing} onChange={(event) => setTestInputs((current) => ({ ...current, pedestrians_crossing: numeric(event.target.value) }))} /></label>
              <label>Waiting vehicles<input type="number" min={0} max={500} value={testInputs.vehicles_waiting} onChange={(event) => setTestInputs((current) => ({ ...current, vehicles_waiting: numeric(event.target.value) }))} /></label>
              <label className="inline-check"><input type="checkbox" checked={testInputs.mobility_assistance} onChange={(event) => setTestInputs((current) => ({ ...current, mobility_assistance: event.target.checked }))} /> Mobility assistance</label>
              <label className="inline-check"><input type="checkbox" checked={testInputs.incident_person_fallen} onChange={(event) => setTestInputs((current) => ({ ...current, incident_person_fallen: event.target.checked }))} /> Person fallen / incident</label>
            </div>
            <div className="button-row">
              <button className="button primary" type="button" onClick={() => void applyTestInputs()}>Apply Test Inputs</button>
              <button className="button" type="button" onClick={() => void clearSignalIncident().then(async (next) => { setTestInputs(next); setSignal(await fetchSignalStatus()); })}>Clear Incident</button>
              <button className="button" type="button" onClick={() => void resetSignalRulesRuntime().then(setSignal)}>Reset Adaptive State</button>
            </div>
          </section>

          <section className="panel">
            <div className="panel-header"><div><h2>Rule preview / dry-run matrix</h2><p className="placeholder-copy">Evaluate representative inputs without changing the active simulator state.</p></div><span className="status-pill">preview only</span></div>
            <div className="button-row wrap">
              <button className="button" type="button" onClick={() => void runPreview({ phase_key: "vehicle_green", vehicles_waiting: 10 })}>10 vehicles</button>
              <button className="button" type="button" onClick={() => void runPreview({ phase_key: "vehicle_green", pedestrians_waiting: 6, vehicles_waiting: 2, pedestrian_wait_seconds: 32 })}>6 pedestrians / 32s wait</button>
              <button className="button" type="button" onClick={() => void runPreview({ phase_key: "pedestrian_flashing", pedestrians_crossing: 1, crossing_dwell_seconds: 7 })}>Slow crossing</button>
              <button className="button" type="button" onClick={() => void runPreview({ phase_key: "pedestrian_green", mobility_assistance: true })}>Mobility assistance</button>
              <button className="button" type="button" onClick={() => void runPreview({ phase_key: "vehicle_green", incident_person_fallen: true })}>Incident</button>
            </div>
            {preview && (
              <div className="signal-preview-result">
                <strong>{PHASE_LABELS[preview.phase_key]}: {preview.base_duration_seconds.toFixed(1)}s → {preview.effective_duration_seconds.toFixed(1)}s</strong>
                {preview.would_enter_incident_hold && <p className="error-message">This scenario would enter simulated all-red incident hold in Test mode.</p>}
                <div className="signal-rule-status-list">
                  {preview.rules.filter((rule) => rule.state !== "inactive").map((rule) => <div className="signal-rule-status" key={rule.rule_id}><div><strong>{rule.label}</strong><p>{rule.reason}</p></div><span className="status-pill">{rule.state}</span></div>)}
                </div>
              </div>
            )}
          </section>
        </>
      )}

      {tab === "history" && (
        <section className="panel">
          <div className="panel-header"><div><h2>Signal decision history</h2><p className="placeholder-copy">Runtime audit trail for phase transitions, applied rules, resets, configuration saves, and incident holds.</p></div><span className="status-pill">runtime data</span></div>
          <div className="button-row">
            <button className="button" type="button" onClick={() => void refreshHistory()}>Refresh</button>
            <button className="button danger" type="button" onClick={() => void clearSignalDecisionHistory().then(refreshHistory)}>Clear History</button>
          </div>
          <p className="small-note">{history?.history_path ?? "outputs/signal_rules/decision_history.jsonl"} is runtime data and must not be included in patch ZIPs.</p>
          <div className="signal-history-list">
            {(history?.events ?? []).slice().reverse().map((event, index) => (
              <article className="function-item" key={`${event.timestamp_ms}-${index}`}>
                <div><strong>{event.event_type.split("_").join(" ")}</strong><p>{new Date(event.timestamp_ms).toLocaleString()} · {JSON.stringify(event.details)}</p></div>
              </article>
            ))}
            {history?.events.length === 0 && <p className="placeholder-copy">No signal decision events recorded yet.</p>}
          </div>
        </section>
      )}

      <FunctionChecklist area="Traffic logic" />
    </div>
  );
}
