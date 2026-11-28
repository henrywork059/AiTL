import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, ReactNode } from "react";
import { fetchSignalRules } from "../api";
import {
  deleteSimulationExperiment,
  fetchSimulationExperiment,
  fetchSimulationExperiments,
  runSimulationExperiment,
  simulationExperimentExportUrl,
} from "../experimentApi";
import type { ExperimentDelta, ExperimentModeResult, SimulationExperiment, SimulationExperimentSummary } from "../types/experiments";
import { createExperimentOperationGate, chooseStoredRunId, verifiedExperimentResult } from "../lib/experimentRunState";
import "./simulationLab.css";
import {NativeSimulationWorkspace} from "./NativeSimulationWorkspace";

type TabId = "summary" | "waiting" | "throughput" | "signal" | "samples";
type SampleMode = "fixed" | "adaptive";

type ComparisonRow = {
  key: string;
  label: string;
  unit: string;
};

const DURATION_OPTIONS = [60, 180, 300, 600, 900, 1800];
const COMPARISON_ROWS: ComparisonRow[] = [
  { key: "vehicle_wait_average", label: "Average vehicle wait", unit: "s" },
  { key: "vehicle_wait_p95", label: "Vehicle wait p95", unit: "s" },
  { key: "pedestrian_wait_average", label: "Average pedestrian wait", unit: "s" },
  { key: "pedestrian_wait_p95", label: "Pedestrian wait p95", unit: "s" },
  { key: "vehicle_queue_average", label: "Average vehicle queue", unit: "" },
  { key: "pedestrian_queue_average", label: "Average pedestrian queue", unit: "" },
  { key: "vehicle_throughput", label: "Vehicle throughput", unit: "/min" },
  { key: "pedestrian_throughput", label: "Pedestrian throughput", unit: "/min" },
  { key: "combined_throughput", label: "Combined services", unit: "/min" },
  { key: "vehicle_green_efficiency", label: "Vehicle green efficiency", unit: "/green min" },
  { key: "simultaneous_queue_time", label: "Both queues active", unit: "s" },
  { key: "protected_overlap_seconds", label: "Conflict-overlap diagnostic", unit: "s" },
];

function formatValue(value: number, unit = ""): string {
  const text = Number.isInteger(value) ? String(value) : value.toFixed(2);
  return unit ? `${text} ${unit}` : text;
}

function deltaText(delta: ExperimentDelta): string {
  if (delta.percent_change === null) return delta.difference === 0 ? "0" : `${delta.difference > 0 ? "+" : ""}${delta.difference.toFixed(2)}`;
  return `${delta.percent_change > 0 ? "+" : ""}${delta.percent_change.toFixed(1)}%`;
}

function directionClass(delta: ExperimentDelta): string {
  if (delta.adaptive_direction === "better") return "experiment-better";
  if (delta.adaptive_direction === "worse") return "experiment-worse";
  return "experiment-same";
}

function scenarioLabel(item: SimulationExperimentSummary): string {
  const name = item.label.trim() || new Date(item.created_at_ms).toLocaleString();
  return `${name} · ${item.scenario.density} · ${item.scenario.duration_seconds}s${item.scenario.demand_model==="live_slots"?" · live slots":item.scenario.demand_model==="protected_slots"?" · protected slots":""}`;
}

function metricRow(label: string, fixed: number, adaptive: number, unit = "") {
  const difference = adaptive - fixed;
  return (
    <tr key={label}>
      <th>{label}</th>
      <td>{formatValue(fixed, unit)}</td>
      <td>{formatValue(adaptive, unit)}</td>
      <td>{difference > 0 ? "+" : ""}{formatValue(difference, unit)}</td>
    </tr>
  );
}

export function SimulationLabPage() {
  const [nativeWorkspace,setNativeWorkspace]=useState(false);
  const [tab, setTab] = useState<TabId>("summary");
  const [sampleMode, setSampleMode] = useState<SampleMode>("adaptive");
  const [duration, setDuration] = useState(300);
  const [demandModel,setDemandModel]=useState<"historical"|"live_slots"|"protected_slots">("historical");
  const [density, setDensity] = useState<"light" | "normal" | "busy">("normal");
  const [seed, setSeed] = useState(25025);
  const [sampleInterval, setSampleInterval] = useState(1);
  const [profile, setProfile] = useState<string>("");
  const [profiles, setProfiles] = useState<string[]>([]);
  const [label, setLabel] = useState("");
  const [runs, setRuns] = useState<SimulationExperimentSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [loadedResult, setResult] = useState<SimulationExperiment | null>(null);
  const result = verifiedExperimentResult(selectedRunId, loadedResult);
  const [busy, setBusy] = useState(true);
  const operationGate = useRef(createExperimentOperationGate()).current;
  const [error, setError] = useState<string | null>(null);
  const [pageSize, setPageSize] = useState(25);
  const [samplePage, setSamplePage] = useState(0);

  async function performOperation(task: (isCurrent: () => boolean) => Promise<void>, fallback: string) {
    const operation = operationGate.begin();
    if (!operation) return;
    setBusy(true);
    setError(null);
    try {
      await task(operation.isCurrent);
    } catch (nextError) {
      if (operation.isCurrent()) setError(nextError instanceof Error ? nextError.message : fallback);
    } finally {
      if (operation.isCurrent()) {
        operation.finish();
        setBusy(false);
      }
    }
  }

  async function loadSelectedRun(runId: string, isCurrent: () => boolean) {
    if (!isCurrent()) return;
    setSelectedRunId(runId);
    setSamplePage(0);
    setResult(null);
    if (!runId) return;
    const next = await fetchSimulationExperiment(runId);
    if (!isCurrent()) return;
    if (!verifiedExperimentResult(runId, next)) throw new Error("Stored experiment identity did not match the selected run.");
    setResult(next);
  }

  async function refreshRunList(isCurrent: () => boolean, preferredRunId?: string) {
    const response = await fetchSimulationExperiments(50);
    if (!isCurrent()) return;
    setRuns(response.experiments);
    await loadSelectedRun(chooseStoredRunId(response.experiments, preferredRunId), isCurrent);
  }

  useEffect(() => {
    void performOperation(async (isCurrent) => {
      // Independent reads: stored results remain available if profile loading fails.
      const [config, listing] = await Promise.allSettled([fetchSignalRules(), fetchSimulationExperiments(50)]);
      if (!isCurrent()) return;
      if (config.status === "fulfilled") {
        setProfiles(Object.keys(config.value.profiles));
        setProfile(config.value.active_profile);
      }
      if (listing.status === "fulfilled") {
        setRuns(listing.value.experiments);
        await loadSelectedRun(chooseStoredRunId(listing.value.experiments), isCurrent);
      } else {
        throw listing.reason;
      }
      if (config.status === "rejected") throw config.reason;
    }, "Simulation Lab could not be initialized.");
    return () => operationGate.retire();
  }, []); // Load once; retiring the operation also protects StrictMode remounts.

  async function runExperiment() {
    if (busy || !profile) return;
    await performOperation(async (isCurrent) => {
      const next = await runSimulationExperiment({
        duration_seconds: duration,
        density,
        demand_model: demandModel,
        seed,
        sample_interval_seconds: sampleInterval,
        profile: profile || null,
        label,
      });
      if (!isCurrent()) return;
      if (!next.run_id) throw new Error("Experiment response did not include its stored run ID.");
      const summary: SimulationExperimentSummary = {
        run_id: next.run_id, created_at_ms: next.created_at_ms, label: next.label,
        scenario: next.scenario, headline: next.comparison,
      };
      // A successful create is not undone by a failed follow-up list refresh.
      setRuns(previous => [summary, ...previous.filter(item => item.run_id !== next.run_id)]);
      setSelectedRunId(next.run_id);
      setResult(next);
      setSamplePage(0);
      try {
        const response = await fetchSimulationExperiments(50);
        if (isCurrent()) setRuns(response.experiments.some(item => item.run_id === next.run_id)
          ? response.experiments : [summary, ...response.experiments]);
      } catch {
        if (isCurrent()) setError("Experiment saved; the stored-run list could not be refreshed.");
      }
    }, "Experiment failed.");
  }

  async function selectRun(runId: string) {
    if (busy) return;
    await performOperation(isCurrent => loadSelectedRun(runId, isCurrent), "Experiment could not be loaded.");
  }

  async function refreshStoredRuns() {
    if (busy) return;
    await performOperation(async (isCurrent) => {
      setResult(null);
      const config = await fetchSignalRules();
      if (!isCurrent()) return;
      const available = Object.keys(config.profiles);
      setProfiles(available);
      setProfile(current => available.includes(current) ? current : config.active_profile);
      await refreshRunList(isCurrent, selectedRunId || undefined);
    }, "Stored runs could not be refreshed.");
  }

  async function deleteRun() {
    if (busy || !result || !window.confirm("Delete this stored simulation experiment? This only removes its experiment result JSON.")) return;
    const runId = result.run_id;
    await performOperation(async (isCurrent) => {
      // A failed or uncertain deletion must not leave stale export/delete actions.
      setResult(null);
      const response = await deleteSimulationExperiment(runId);
      if (!isCurrent()) return;
      if (response.deleted !== true || response.run_id !== runId) throw new Error("Deletion was not confirmed for the selected run. Refresh stored runs.");
      setSelectedRunId("");
      setRuns(previous => previous.filter(item => item.run_id !== runId));
      try {
        await refreshRunList(isCurrent);
      } catch {
        if (isCurrent()) setError("Experiment deleted; the stored-run list could not be refreshed.");
      }
    }, "Experiment could not be deleted.");
  }

  const sampleSource = result?.[sampleMode].timeline ?? [];
  const samplePageCount = Math.max(1, Math.ceil(sampleSource.length / pageSize));
  const clampedSamplePage = Math.min(samplePage, samplePageCount - 1);
  const visibleSamples = useMemo(
    () => sampleSource.slice(clampedSamplePage * pageSize, clampedSamplePage * pageSize + pageSize),
    [sampleSource, clampedSamplePage, pageSize],
  );

  if(nativeWorkspace)return <div className="experiment-page native-lab-page"><button type="button" onClick={()=>setNativeWorkspace(false)}>Back to legacy experiments</button><NativeSimulationWorkspace profile={profile||undefined}/></div>;

  return (
    <div className="experiment-page">
      <section className="panel experiment-workspace">
        <div className="experiment-header">
          <div>
            <h2>Fixed vs Adaptive Simulation Lab</h2>
            <p className="placeholder-copy">Run the same seeded prototype junction in Fixed and Adaptive modes, then compare waiting, queues, throughput, signal use, scenario activity, and conflict diagnostics.</p>
          </div>
          <div className="button-row"><span className="status-pill muted">isolated benchmark</span><button type="button" disabled={busy} onClick={()=>setNativeWorkspace(true)}>Native evaluation workspace</button></div>
        </div>

        <div className="experiment-control-grid">
          <label>Density
            <select value={density} onChange={(event: ChangeEvent<HTMLSelectElement>) => setDensity(event.target.value as typeof density)}>
              <option value="light">Light</option><option value="normal">Normal</option><option value="busy">Busy</option>
            </select>
          </label>
          <label>Demand model
            <select value={demandModel} disabled={busy} onChange={(event: ChangeEvent<HTMLSelectElement>) => setDemandModel(event.target.value as typeof demandModel)}>
              <option value="historical">Historical benchmark</option>
              <option value="live_slots">Live camera slots (50 ms)</option>
              <option value="protected_slots">Protected crosswalk slots (50 ms)</option>
            </select>
          </label>
          <label>Duration
            <select value={duration} onChange={(event: ChangeEvent<HTMLSelectElement>) => setDuration(Number(event.target.value))}>
              {DURATION_OPTIONS.map((value) => <option key={value} value={value}>{value < 60 ? `${value}s` : `${value / 60} min`}</option>)}
            </select>
          </label>
          <label>Signal profile
            <select value={profile} onChange={(event: ChangeEvent<HTMLSelectElement>) => setProfile(event.target.value)}>
              {profiles.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <label>Seed
            <input type="number" min={0} max={2147483647} value={seed} onChange={(event: ChangeEvent<HTMLInputElement>) => setSeed(Number(event.target.value))} />
          </label>
          <label>Sample interval
            <select value={sampleInterval} onChange={(event: ChangeEvent<HTMLSelectElement>) => setSampleInterval(Number(event.target.value))}>
              {[1, 2, 5, 10].map((value) => <option key={value} value={value}>{value}s</option>)}
            </select>
          </label>
          <label>Run label
            <input value={label} maxLength={80} placeholder="Optional" onChange={(event: ChangeEvent<HTMLInputElement>) => setLabel(event.target.value)} />
          </label>
          <button className="primary experiment-run-button" type="button" disabled={busy || !profile} onClick={() => void runExperiment()}>{busy ? "Working..." : "Run comparison"}</button>
        </div>

        <div className="experiment-saved-row">
          <label>Stored run
            <select value={selectedRunId} disabled={busy} onChange={(event: ChangeEvent<HTMLSelectElement>) => void selectRun(event.target.value)}>
              <option value="">No stored run selected</option>
              {runs.map((item) => <option key={item.run_id} value={item.run_id}>{scenarioLabel(item)}</option>)}
            </select>
          </label>
          <div className="button-row">
            <button type="button" disabled={busy} onClick={() => void refreshStoredRuns()}>Refresh stored runs</button>
            <button type="button" disabled={busy || !result} onClick={() => !busy && result && window.location.assign(simulationExperimentExportUrl(result.run_id))}>Export samples CSV</button>
            <button className="danger" type="button" disabled={!result || busy} onClick={() => void deleteRun()}>Delete run</button>
          </div>
          {result && <div className="experiment-scenario-strip"><strong>{result.scenario.profile}</strong><span>{result.scenario.density}</span><span>{result.scenario.duration_seconds}s</span><span>seed {result.scenario.seed}</span>{result.scenario.demand_model==="live_slots"&&<span>Live camera slots · 50 ms</span>}{result.scenario.demand_model==="protected_slots"&&<span>Protected crosswalk · 50 ms</span>}<span>{new Date(result.created_at_ms).toLocaleString()}</span></div>}
        </div>

        {error && <p className="error-message experiment-error" role="alert">{error}</p>}

        <div className="experiment-tabs" role="tablist" aria-label="Simulation experiment data groups"
          onKeyDown={(event) => {
            if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
            event.preventDefault();
            const ids: TabId[] = ["summary", "waiting", "throughput", "signal", "samples"];
            const index = ids.indexOf(tab);
            const next = event.key === "Home" ? ids[0] : event.key === "End" ? ids[ids.length - 1]
              : ids[(index + (event.key === "ArrowRight" ? 1 : -1) + ids.length) % ids.length];
            setTab(next);
            event.currentTarget.querySelector<HTMLButtonElement>(`#experiment-tab-${next}`)?.focus();
          }}>
          {([
            ["summary", "Summary"], ["waiting", "Waiting & queues"], ["throughput", "Throughput"], ["signal", "Signal behavior"], ["samples", "Raw samples"],
          ] as [TabId, string][]).map(([id, text]) => (
            <button key={id} id={`experiment-tab-${id}`} type="button" role="tab" aria-selected={tab === id}
              aria-controls="experiment-tab-panel" tabIndex={tab === id ? 0 : -1}
              className={tab === id ? "active" : ""} onClick={() => setTab(id)}>{text}</button>
          ))}
        </div>

        <div className="experiment-tab-panel" id="experiment-tab-panel" role="tabpanel" aria-labelledby={`experiment-tab-${tab}`} tabIndex={0}>
          {!result ? <div className="experiment-empty"><strong>{busy ? "Loading experiment..." : selectedRunId ? "Selected experiment unavailable." : "No experiment selected."}</strong><span>{busy ? "Waiting for the current operation." : "Choose a stored run, refresh the list or start a new comparison."}</span></div> : (
            <>
              {tab === "summary" && <SummaryTab result={result} />}
              {tab === "waiting" && <WaitingTab fixed={result.fixed} adaptive={result.adaptive} />}
              {tab === "throughput" && <ThroughputTab fixed={result.fixed} adaptive={result.adaptive} />}
              {tab === "signal" && <SignalTab fixed={result.fixed} adaptive={result.adaptive} />}
              {tab === "samples" && (
                <SamplesTab
                  mode={sampleMode}
                  onModeChange={(nextMode) => { setSampleMode(nextMode); setSamplePage(0); }}
                  pageSize={pageSize}
                  onPageSizeChange={(nextSize) => { setPageSize(nextSize); setSamplePage(0); }}
                  page={clampedSamplePage}
                  pageCount={samplePageCount}
                  onPageChange={setSamplePage}
                  samples={visibleSamples}
                  total={sampleSource.length}
                />
              )}
            </>
          )}
        </div>
      </section>
    </div>
  );
}

function SummaryTab({ result }: { result: SimulationExperiment }) {
  const keys = ["vehicle_wait_average", "pedestrian_wait_average", "vehicle_throughput", "pedestrian_throughput", "combined_throughput", "simultaneous_queue_time"];
  return (
    <div className="experiment-summary-grid">
      {keys.map((key) => {
        const delta = result.comparison[key];
        const row = COMPARISON_ROWS.find((item) => item.key === key)!;
        return (
          <div className="experiment-compare-card" key={key}>
            <div><span>{row.label}</span><strong className={directionClass(delta)}>{deltaText(delta)}</strong></div>
            <div className="experiment-fixed-adaptive"><span>Fixed <strong>{formatValue(delta.fixed, row.unit)}</strong></span><span>Adaptive <strong>{formatValue(delta.adaptive, row.unit)}</strong></span></div>
          </div>
        );
      })}
      <section className="experiment-summary-note">
        <strong>Interpretation</strong>
        <p>Green numbers mean Adaptive moved the metric in the preferred direction for this seeded simulation. They are experiment results, not a general claim that one policy is always superior.</p>
        <small>{result.scope_note}</small>
      </section>
    </div>
  );
}

function WaitingTab({ fixed, adaptive }: { fixed: ExperimentModeResult; adaptive: ExperimentModeResult }) {
  const fw = fixed.metrics.waiting; const aw = adaptive.metrics.waiting;
  const fq = fixed.metrics.queues; const aq = adaptive.metrics.queues;
  return (
    <div className="experiment-table-grid">
      <ComparisonTable title="Wait-time distribution" rows={[
        metricRow("Vehicle average", fw.vehicle.average_seconds, aw.vehicle.average_seconds, "s"),
        metricRow("Vehicle median", fw.vehicle.median_seconds, aw.vehicle.median_seconds, "s"),
        metricRow("Vehicle p95", fw.vehicle.p95_seconds, aw.vehicle.p95_seconds, "s"),
        metricRow("Vehicle maximum", fw.vehicle.max_seconds, aw.vehicle.max_seconds, "s"),
        metricRow("Pedestrian average", fw.pedestrian.average_seconds, aw.pedestrian.average_seconds, "s"),
        metricRow("Pedestrian median", fw.pedestrian.median_seconds, aw.pedestrian.median_seconds, "s"),
        metricRow("Pedestrian p95", fw.pedestrian.p95_seconds, aw.pedestrian.p95_seconds, "s"),
        metricRow("Pedestrian maximum", fw.pedestrian.max_seconds, aw.pedestrian.max_seconds, "s"),
      ]} />
      <ComparisonTable title="Queue pressure" rows={[
        metricRow("Vehicle average queue", fq.vehicle.average, aq.vehicle.average),
        metricRow("Vehicle p95 queue", fq.vehicle.p95, aq.vehicle.p95),
        metricRow("Vehicle peak queue", fq.vehicle.max, aq.vehicle.max),
        metricRow("Vehicle queue-seconds", fq.vehicle.queue_seconds, aq.vehicle.queue_seconds, "s"),
        metricRow("Vehicle queue active", fq.vehicle.occupied_share_percent, aq.vehicle.occupied_share_percent, "%"),
        metricRow("Pedestrian average queue", fq.pedestrian.average, aq.pedestrian.average),
        metricRow("Pedestrian p95 queue", fq.pedestrian.p95, aq.pedestrian.p95),
        metricRow("Pedestrian peak queue", fq.pedestrian.max, aq.pedestrian.max),
        metricRow("Pedestrian queue-seconds", fq.pedestrian.queue_seconds, aq.pedestrian.queue_seconds, "s"),
        metricRow("Both queues active", fq.simultaneous_queue_seconds, aq.simultaneous_queue_seconds, "s"),
      ]} />
    </div>
  );
}

function ThroughputTab({ fixed, adaptive }: { fixed: ExperimentModeResult; adaptive: ExperimentModeResult }) {
  const f = fixed.metrics.throughput; const a = adaptive.metrics.throughput;
  return <ComparisonTable title="Completed service and efficiency" rows={[
    metricRow("Vehicle passages", f.vehicle_passages, a.vehicle_passages),
    metricRow("Vehicle passages / min", f.vehicle_per_minute, a.vehicle_per_minute),
    metricRow("Pedestrian crossings", f.pedestrian_crossings, a.pedestrian_crossings),
    metricRow("Pedestrian crossings / min", f.pedestrian_per_minute, a.pedestrian_per_minute),
    metricRow("Combined services", f.combined_services, a.combined_services),
    metricRow("Combined services / min", f.combined_services_per_minute, a.combined_services_per_minute),
    metricRow("Vehicle passages / green min", f.vehicle_passages_per_green_minute, a.vehicle_passages_per_green_minute),
  ]} />;
}

function SignalTab({ fixed, adaptive }: { fixed: ExperimentModeResult; adaptive: ExperimentModeResult }) {
  const f = fixed.metrics.signal; const a = adaptive.metrics.signal;
  const phases = Array.from(new Set([...Object.keys(f.phase_time_seconds), ...Object.keys(a.phase_time_seconds)]));
  const applied=Array.from(new Set([...Object.keys(f.applied_phase_time_seconds??{}),...Object.keys(a.applied_phase_time_seconds??{})]));
  const rules = Object.entries(a.rule_applications).sort((left, right) => right[1] - left[1]);
  return (
    <div className="experiment-table-grid">
      <ComparisonTable title="Signal utilization" rows={[
        ...phases.map((phase) => metricRow(`${phase.replaceAll("_", " ")} time`, f.phase_time_seconds[phase] ?? 0, a.phase_time_seconds[phase] ?? 0, "s")),
        ...applied.map(phase=>metricRow(`Applied ${phase.replaceAll("_"," ")}`,f.applied_phase_time_seconds?.[phase]??0,a.applied_phase_time_seconds?.[phase]??0,"s")),
        ...(f.admission_hold_seconds!==undefined&&a.admission_hold_seconds!==undefined?[metricRow("Protective admission holds",f.admission_hold_seconds,a.admission_hold_seconds,"s")]:[]),
        metricRow("Phase transitions", f.phase_transitions, a.phase_transitions),
        metricRow("Completed cycles", f.cycles_completed, a.cycles_completed),
        metricRow("Clearance time", f.clearance_time_seconds, a.clearance_time_seconds, "s"),
        metricRow("Scenario applications", f.rule_application_count, a.rule_application_count),
        metricRow("Timing extensions", f.extension_seconds, a.extension_seconds, "s"),
        metricRow("Timing reductions", f.reduction_seconds, a.reduction_seconds, "s"),
      ]} />
      <section className="experiment-rule-panel">
        <div className="panel-header"><h3>Adaptive scenario applications</h3><span className="status-pill muted">{a.rule_application_count}</span></div>
        {rules.length === 0 ? <p className="placeholder-copy">No adaptive scenario changed a phase duration during this run.</p> : (
          <div className="experiment-rule-list">{rules.map(([rule, count]) => <div key={rule}><span>{rule.replaceAll("_", " ")}</span><strong>{count}</strong></div>)}</div>
        )}
        <div className="experiment-diagnostic">
          <span>Conflict-overlap diagnostic</span>
          <strong>Fixed {fixed.metrics.diagnostics.protected_overlap_seconds}s · Adaptive {adaptive.metrics.diagnostics.protected_overlap_seconds}s</strong>
          <small>{adaptive.metrics.diagnostics.note}</small>
        </div>
      </section>
    </div>
  );
}

function SamplesTab({ mode, onModeChange, pageSize, onPageSizeChange, page, pageCount, onPageChange, samples, total }: {
  mode: SampleMode;
  onModeChange: (mode: SampleMode) => void;
  pageSize: number;
  onPageSizeChange: (size: number) => void;
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  samples: SimulationExperiment[SampleMode]["timeline"];
  total: number;
}) {
  return (
    <div className="experiment-samples">
      <div className="experiment-sample-toolbar">
        <div className="experiment-toggle" role="group" aria-label="Sample mode"><button aria-pressed={mode === "fixed"} className={mode === "fixed" ? "active" : ""} onClick={() => onModeChange("fixed")}>Fixed</button><button aria-pressed={mode === "adaptive"} className={mode === "adaptive" ? "active" : ""} onClick={() => onModeChange("adaptive")}>Adaptive</button></div>
        <label>Rows <select value={pageSize} onChange={(event: ChangeEvent<HTMLSelectElement>) => onPageSizeChange(Number(event.target.value))}>{[25, 50, 100].map((value) => <option key={value}>{value}</option>)}</select></label>
        <span>{total} samples · page {page + 1}/{pageCount}</span>
        <div className="button-row"><button disabled={page <= 0} onClick={() => onPageChange(page - 1)}>Previous</button><button disabled={page >= pageCount - 1} onClick={() => onPageChange(page + 1)}>Next</button></div>
      </div>
      <div className="experiment-sample-table-wrap"><table className="experiment-data-table"><thead><tr><th>t</th><th>Requested phase</th><th>Applied admission</th><th>Vehicle queue</th><th>Ped queue</th><th>Vehicles served</th><th>Ped served</th><th>Active scenario</th></tr></thead><tbody>{samples.map((sample) => <tr key={`${mode}-${sample.t}`}><td>{sample.t.toFixed(1)}s</td><td>{sample.phase.replaceAll("_", " ")}</td><td>{sample.applied_phase?.replaceAll("_"," ")??"—"}</td><td>{sample.vehicle_queue}</td><td>{sample.pedestrian_queue}</td><td>{sample.vehicle_passages}</td><td>{sample.pedestrian_crossings}</td><td>{sample.active_rules.length ? sample.active_rules.join(", ") : "—"}</td></tr>)}</tbody></table></div>
    </div>
  );
}

function ComparisonTable({ title, rows }: { title: string; rows: ReactNode[] }) {
  return <section className="experiment-table-panel"><h3>{title}</h3><div className="experiment-data-table-wrap"><table className="experiment-data-table"><thead><tr><th>Metric</th><th>Fixed</th><th>Adaptive</th><th>Δ</th></tr></thead><tbody>{rows}</tbody></table></div></section>;
}
