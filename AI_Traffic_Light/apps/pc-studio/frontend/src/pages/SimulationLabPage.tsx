import { useCallback, useEffect, useMemo, useState } from "react";
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
import "./simulationLab.css";

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
  return `${name} · ${item.scenario.density} · ${item.scenario.duration_seconds}s`;
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
  const [tab, setTab] = useState<TabId>("summary");
  const [sampleMode, setSampleMode] = useState<SampleMode>("adaptive");
  const [duration, setDuration] = useState(300);
  const [density, setDensity] = useState<"light" | "normal" | "busy">("normal");
  const [seed, setSeed] = useState(25025);
  const [sampleInterval, setSampleInterval] = useState(1);
  const [profile, setProfile] = useState<string>("");
  const [profiles, setProfiles] = useState<string[]>([]);
  const [label, setLabel] = useState("");
  const [runs, setRuns] = useState<SimulationExperimentSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [result, setResult] = useState<SimulationExperiment | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pageSize, setPageSize] = useState(25);
  const [samplePage, setSamplePage] = useState(0);

  const refreshRunList = useCallback(async (preferredRunId?: string) => {
    const response = await fetchSimulationExperiments(50);
    setRuns(response.experiments);
    const nextId = preferredRunId || selectedRunId || response.experiments[0]?.run_id || "";
    setSelectedRunId(nextId);
    if (nextId) setResult(await fetchSimulationExperiment(nextId));
    else setResult(null);
  }, [selectedRunId]);

  useEffect(() => {
    void (async () => {
      try {
        const config = await fetchSignalRules();
        const available = Object.keys(config.profiles);
        setProfiles(available);
        setProfile(config.active_profile);
        await refreshRunList();
      } catch (nextError) {
        setError(nextError instanceof Error ? nextError.message : "Simulation Lab could not be initialized.");
      }
    })();
  }, []); // Load once; run selection is refreshed explicitly after actions.

  async function runExperiment() {
    setBusy(true);
    setError(null);
    try {
      const next = await runSimulationExperiment({
        duration_seconds: duration,
        density,
        seed,
        sample_interval_seconds: sampleInterval,
        profile: profile || null,
        label,
      });
      setResult(next);
      setSelectedRunId(next.run_id);
      setSamplePage(0);
      const response = await fetchSimulationExperiments(50);
      setRuns(response.experiments);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Experiment failed.");
    } finally {
      setBusy(false);
    }
  }

  async function selectRun(runId: string) {
    setSelectedRunId(runId);
    setSamplePage(0);
    if (!runId) {
      setResult(null);
      return;
    }
    setBusy(true);
    try {
      setResult(await fetchSimulationExperiment(runId));
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Experiment could not be loaded.");
    } finally {
      setBusy(false);
    }
  }

  async function deleteRun() {
    if (!result || !window.confirm("Delete this stored simulation experiment? This only removes its experiment result JSON.")) return;
    setBusy(true);
    try {
      await deleteSimulationExperiment(result.run_id);
      setSelectedRunId("");
      setResult(null);
      const response = await fetchSimulationExperiments(50);
      setRuns(response.experiments);
      if (response.experiments[0]) await selectRun(response.experiments[0].run_id);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Experiment could not be deleted.");
    } finally {
      setBusy(false);
    }
  }

  const sampleSource = result?.[sampleMode].timeline ?? [];
  const samplePageCount = Math.max(1, Math.ceil(sampleSource.length / pageSize));
  const clampedSamplePage = Math.min(samplePage, samplePageCount - 1);
  const visibleSamples = useMemo(
    () => sampleSource.slice(clampedSamplePage * pageSize, clampedSamplePage * pageSize + pageSize),
    [sampleSource, clampedSamplePage, pageSize],
  );

  return (
    <div className="experiment-page">
      <section className="panel experiment-workspace">
        <div className="experiment-header">
          <div>
            <h2>Fixed vs Adaptive Simulation Lab</h2>
            <p className="placeholder-copy">Run the same seeded prototype junction in Fixed and Adaptive modes, then compare waiting, queues, throughput, signal use, scenario activity, and conflict diagnostics.</p>
          </div>
          <span className="status-pill muted">isolated benchmark</span>
        </div>

        <div className="experiment-control-grid">
          <label>Density
            <select value={density} onChange={(event: ChangeEvent<HTMLSelectElement>) => setDensity(event.target.value as typeof density)}>
              <option value="light">Light</option><option value="normal">Normal</option><option value="busy">Busy</option>
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
            <select value={selectedRunId} onChange={(event: ChangeEvent<HTMLSelectElement>) => void selectRun(event.target.value)}>
              <option value="">No stored run selected</option>
              {runs.map((item) => <option key={item.run_id} value={item.run_id}>{scenarioLabel(item)}</option>)}
            </select>
          </label>
          <div className="button-row">
            <button type="button" disabled={!result} onClick={() => result && window.location.assign(simulationExperimentExportUrl(result.run_id))}>Export samples CSV</button>
            <button className="danger" type="button" disabled={!result || busy} onClick={() => void deleteRun()}>Delete run</button>
          </div>
          {result && <div className="experiment-scenario-strip"><strong>{result.scenario.profile}</strong><span>{result.scenario.density}</span><span>{result.scenario.duration_seconds}s</span><span>seed {result.scenario.seed}</span><span>{new Date(result.created_at_ms).toLocaleString()}</span></div>}
        </div>

        {error && <p className="error-message experiment-error">{error}</p>}

        <div className="experiment-tabs" role="tablist" aria-label="Simulation experiment data groups">
          {([
            ["summary", "Summary"], ["waiting", "Waiting & queues"], ["throughput", "Throughput"], ["signal", "Signal behavior"], ["samples", "Raw samples"],
          ] as [TabId, string][]).map(([id, text]) => (
            <button key={id} type="button" role="tab" aria-selected={tab === id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}>{text}</button>
          ))}
        </div>

        <div className="experiment-tab-panel" role="tabpanel">
          {!result ? <div className="experiment-empty"><strong>No experiment selected.</strong><span>Choose a stored run or start a new comparison.</span></div> : (
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
  const rules = Object.entries(a.rule_applications).sort((left, right) => right[1] - left[1]);
  return (
    <div className="experiment-table-grid">
      <ComparisonTable title="Signal utilization" rows={[
        ...phases.map((phase) => metricRow(`${phase.replaceAll("_", " ")} time`, f.phase_time_seconds[phase] ?? 0, a.phase_time_seconds[phase] ?? 0, "s")),
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
        <div className="experiment-toggle" role="group" aria-label="Sample mode"><button className={mode === "fixed" ? "active" : ""} onClick={() => onModeChange("fixed")}>Fixed</button><button className={mode === "adaptive" ? "active" : ""} onClick={() => onModeChange("adaptive")}>Adaptive</button></div>
        <label>Rows <select value={pageSize} onChange={(event: ChangeEvent<HTMLSelectElement>) => onPageSizeChange(Number(event.target.value))}>{[25, 50, 100].map((value) => <option key={value}>{value}</option>)}</select></label>
        <span>{total} samples · page {page + 1}/{pageCount}</span>
        <div className="button-row"><button disabled={page <= 0} onClick={() => onPageChange(page - 1)}>Previous</button><button disabled={page >= pageCount - 1} onClick={() => onPageChange(page + 1)}>Next</button></div>
      </div>
      <div className="experiment-sample-table-wrap"><table className="experiment-data-table"><thead><tr><th>t</th><th>Phase</th><th>Vehicle queue</th><th>Ped queue</th><th>Vehicles served</th><th>Ped served</th><th>Active scenario</th></tr></thead><tbody>{samples.map((sample) => <tr key={`${mode}-${sample.t}`}><td>{sample.t.toFixed(1)}s</td><td>{sample.phase.replaceAll("_", " ")}</td><td>{sample.vehicle_queue}</td><td>{sample.pedestrian_queue}</td><td>{sample.vehicle_passages}</td><td>{sample.pedestrian_crossings}</td><td>{sample.active_rules.length ? sample.active_rules.join(", ") : "—"}</td></tr>)}</tbody></table></div>
    </div>
  );
}

function ComparisonTable({ title, rows }: { title: string; rows: ReactNode[] }) {
  return <section className="experiment-table-panel"><h3>{title}</h3><div className="experiment-data-table-wrap"><table className="experiment-data-table"><thead><tr><th>Metric</th><th>Fixed</th><th>Adaptive</th><th>Δ</th></tr></thead><tbody>{rows}</tbody></table></div></section>;
}
