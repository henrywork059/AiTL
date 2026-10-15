import { useEffect, useState } from "react";
import { fetchSignalRules, saveSignalRules } from "../api";
import type { SignalPhaseKey, SignalRulesConfig } from "../types";
import "./signalRules.css";

const PHASES: { id: SignalPhaseKey; label: string }[] = [
  { id: "vehicle_green", label: "Vehicle green" },
  { id: "vehicle_yellow", label: "Vehicle amber" },
  { id: "all_red_to_pedestrian", label: "All-red before pedestrian walk" },
  { id: "pedestrian_green", label: "Pedestrian walk" },
  { id: "pedestrian_flashing", label: "Pedestrian clearance" },
  { id: "all_red_to_vehicle", label: "All-red before vehicle green" },
];

export function SignalTimingPage() {
  const [saved, setSaved] = useState<SignalRulesConfig | null>(null);
  const [draft, setDraft] = useState<SignalRulesConfig | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const active = draft?.profiles[draft.active_profile];
  const dirty = Boolean(saved && draft && JSON.stringify(saved.profiles[saved.active_profile].phases) !== JSON.stringify(active?.phases));

  async function load() {
    const next = await fetchSignalRules();
    setSaved(next);
    setDraft(structuredClone(next));
    setError(null);
  }

  useEffect(() => { void load().catch((reason) => setError(String(reason))); }, []);

  function update(phase: SignalPhaseKey, value: number) {
    setDraft((current) => {
      if (!current) return current;
      const next = structuredClone(current);
      next.profiles[next.active_profile].phases[phase].base_seconds = value;
      setNotice(null);
      return next;
    });
  }

  async function save() {
    if (!saved || !draft || !active) return;
    setBusy(true);
    setError(null);
    try {
      // Merge just the phase bases with the latest config: never overwrite live-adjustment rules.
      const latest = await fetchSignalRules();
      if (latest.active_profile !== saved.active_profile ||
          JSON.stringify(latest.profiles[latest.active_profile].phases) !== JSON.stringify(saved.profiles[saved.active_profile].phases)) {
        throw new Error("Signal timing changed elsewhere. Reload before saving.");
      }
      const next = structuredClone(latest);
      for (const { id } of PHASES) next.profiles[next.active_profile].phases[id].base_seconds = active.phases[id].base_seconds;
      const result = await saveSignalRules(next);
      setSaved(result);
      setDraft(structuredClone(result));
      setNotice("Default signal timings saved. The controller will use the protected phase sequence.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save signal timings.");
    } finally {
      setBusy(false);
    }
  }

  return <div className="page-stack signal-rules-page">
    <section className="panel">
      <div className="panel-header">
        <div><h2>Traffic Light Settings</h2><p className="placeholder-copy">Edit default phase durations in the active signal profile. Protected minimums, maximums and the all-red phases remain enforced by the existing controller.</p></div>
        <span className="status-pill muted">{draft?.active_profile ?? "Loading"}</span>
      </div>
      {!active ? <p className="small-note">Loading signal configuration...</p> : <>
        <div className="signal-timing-table-wrap">
          <table className="signal-timing-table">
            <thead><tr><th>Signal phase</th><th>Default seconds</th><th>Protected minimum</th><th>Maximum</th></tr></thead>
            <tbody>{PHASES.map(({ id, label }) => {
              const phase = active.phases[id];
              return <tr key={id}>
                <td><strong>{label}</strong></td>
                <td><input aria-label={label + " default seconds"} type="number" step="0.5" min={phase.min_seconds} max={phase.max_seconds}
                  value={phase.base_seconds} onChange={(event) => update(id, Number(event.target.value))} /></td>
                <td>{phase.min_seconds} s</td><td>{phase.max_seconds} s</td>
              </tr>;
            })}</tbody>
          </table>
        </div>
        <p className="small-note">Changes are simulation/prototype configuration. Adaptive rules may adjust phases within these limits. Do not use this page to command physical roadway traffic lights.</p>
        <div className="button-row">
          <button type="button" onClick={() => void load().catch((reason) => setError(String(reason)))} disabled={busy}>Reload</button>
          <button className="primary" type="button" disabled={!dirty || busy || PHASES.some(({ id }) => {
            const p = active.phases[id];
            return !Number.isFinite(p.base_seconds) || p.base_seconds < p.min_seconds || p.base_seconds > p.max_seconds;
          })} onClick={() => void save()}>{busy ? "Saving..." : "Save default timing"}</button>
        </div>
      </>}
      {error && <p className="error-message" role="alert">{error}</p>}
      {notice && <p className="success-message" role="status">{notice}</p>}
    </section>
  </div>;
}
