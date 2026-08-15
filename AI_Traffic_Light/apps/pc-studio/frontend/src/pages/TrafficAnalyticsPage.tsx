import { useCallback, useEffect, useMemo, useState } from "react";
import {
  clearTrafficFlow,
  clearTrafficHistory,
  fetchTrafficFlow,
  fetchTrafficHistory,
  trafficFlowExportUrl,
  trafficHistoryExportUrl,
} from "../api";
import { FunctionChecklist } from "../components/FunctionChecklist";
import { TrafficFlowChart } from "../components/TrafficFlowChart";
import { TrafficHistoryChart } from "../components/TrafficHistoryChart";
import type { TrafficFlow, TrafficHistory } from "../types";
import "./trafficAnalytics.css";

const WINDOWS = [
  { label: "1 min", value: 1 },
  { label: "5 min", value: 5 },
  { label: "15 min", value: 15 },
  { label: "1 hour", value: 60 },
  { label: "6 hours", value: 360 },
  { label: "All stored", value: 0 },
];

const FLOW_CLASSES = ["", "person", "car", "bus", "truck", "motorcycle", "bicycle"];

type AnalyticsMode = "occupancy" | "flow";

function timestampLabel(timestampMs: number | null): string {
  if (!timestampMs) return "none";
  return new Date(timestampMs).toLocaleString();
}

function durationLabel(durationMs: number | undefined): string {
  if (!durationMs) return "0.0 s";
  return `${(durationMs / 1000).toFixed(1)} s`;
}

function eventLabel(eventType: string): string {
  return eventType.split("_").join(" ");
}

export function TrafficAnalyticsPage() {
  const [mode, setMode] = useState<AnalyticsMode>("occupancy");
  const [history, setHistory] = useState<TrafficHistory | null>(null);
  const [flow, setFlow] = useState<TrafficFlow | null>(null);
  const [minutes, setMinutes] = useState(15);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [flowScope, setFlowScope] = useState("");
  const [className, setClassName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [clearing, setClearing] = useState(false);

  const flowLineId = flowScope.startsWith("line:") ? flowScope.slice(5) : null;
  const flowRegionId = flowScope.startsWith("region:") ? flowScope.slice(7) : null;

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      if (mode === "occupancy") {
        setHistory(await fetchTrafficHistory(minutes, regionId));
      } else {
        setFlow(await fetchTrafficFlow(minutes, flowLineId, flowRegionId, className || null));
      }
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Traffic analytics could not be loaded.");
    } finally {
      setRefreshing(false);
    }
  }, [mode, minutes, regionId, flowLineId, flowRegionId, className]);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 2000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const latest = history && history.points.length > 0 ? history.points[history.points.length - 1] : null;
  const regionOptions = history?.regions ?? [];
  const summary = history?.summary;
  const phaseChange = summary?.latest_phase_change;
  const selectedScope = history?.scope.label ?? "Whole frame";
  const occupancyExportUrl = useMemo(() => trafficHistoryExportUrl(minutes, regionId), [minutes, regionId]);
  const flowExportUrl = useMemo(
    () => trafficFlowExportUrl(minutes, flowLineId, flowRegionId, className || null),
    [minutes, flowLineId, flowRegionId, className],
  );
  const flowSummary = flow?.summary;
  const recentFlowEvents = [...(flow?.events ?? [])].slice(-12).reverse();

  async function clearCurrent() {
    const occupancy = mode === "occupancy";
    const prompt = occupancy
      ? "Clear all stored traffic occupancy history? This does not remove flow events, captures, labels, zones, or trained models."
      : "Clear all stored tracked flow events? This does not remove occupancy history, captures, labels, zones, or trained models.";
    if (!window.confirm(prompt)) return;
    setClearing(true);
    try {
      if (occupancy) await clearTrafficHistory();
      else await clearTrafficFlow();
      await refresh();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Traffic analytics could not be cleared.");
    } finally {
      setClearing(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Traffic analytics</h2>
            <p className="placeholder-copy">Compare V021 sampled occupancy with V022 track-derived unique passages, direction, region entry/exit, and dwell time.</p>
          </div>
          <div className="traffic-mode-tabs" role="group" aria-label="Traffic analytics mode">
            <button type="button" className={mode === "occupancy" ? "active" : ""} onClick={() => setMode("occupancy")}>Occupancy</button>
            <button type="button" className={mode === "flow" ? "active" : ""} onClick={() => setMode("flow")}>Flow / tracks</button>
          </div>
        </div>

        <div className="traffic-analytics-controls">
          <label>Time window
            <select value={minutes} onChange={(event) => setMinutes(Number(event.target.value))}>
              {WINDOWS.map((windowOption) => <option key={windowOption.value} value={windowOption.value}>{windowOption.label}</option>)}
            </select>
          </label>

          {mode === "occupancy" ? (
            <label>Count scope
              <select value={regionId ?? ""} onChange={(event) => setRegionId(event.target.value || null)}>
                <option value="">Whole frame</option>
                {regionOptions.map((region) => <option key={region.id} value={region.id}>{region.label} ({region.type.split("_").join(" ")})</option>)}
              </select>
            </label>
          ) : (
            <>
              <label>Flow scope
                <select value={flowScope} onChange={(event) => setFlowScope(event.target.value)}>
                  <option value="">All tracked events</option>
                  {(flow?.lines ?? []).map((line) => <option key={`line:${line.id}`} value={`line:${line.id}`}>Line: {line.label}</option>)}
                  {(flow?.regions ?? []).map((region) => <option key={`region:${region.id}`} value={`region:${region.id}`}>Region: {region.label}</option>)}
                </select>
              </label>
              <label>Class
                <select value={className} onChange={(event) => setClassName(event.target.value)}>
                  {FLOW_CLASSES.map((item) => <option key={item || "all"} value={item}>{item || "All tracked classes"}</option>)}
                </select>
              </label>
            </>
          )}

          <div className="button-row wrap-row traffic-analytics-actions">
            <button type="button" onClick={() => void refresh()} disabled={refreshing}>{refreshing ? "Refreshing..." : "Refresh"}</button>
            <button type="button" onClick={() => window.location.assign(mode === "occupancy" ? occupancyExportUrl : flowExportUrl)}>Export CSV</button>
            <button type="button" onClick={() => void clearCurrent()} disabled={clearing}>{clearing ? "Clearing..." : mode === "occupancy" ? "Clear occupancy" : "Clear flow"}</button>
          </div>
        </div>

        {mode === "occupancy" ? (
          <>
            <TrafficHistoryChart points={history?.points ?? []} />
            <p className="small-note">Scope: <strong>{selectedScope}</strong>. Occupancy remains a sampled per-frame metric. Do not sum these samples and call them throughput.</p>
          </>
        ) : (
          <>
            <TrafficFlowChart buckets={flow?.buckets ?? []} series={flowRegionId ? "regions" : "passages"} />
            <p className="small-note">Unique passage counts come only from a stable track crossing a configured <strong>counting line</strong>. Each track is counted at most once per line in the current prototype session, reducing jitter/double-counting.</p>
          </>
        )}
        {error && <p className="error-message">{error}</p>}
      </section>

      {mode === "occupancy" ? (
        <>
          <div className="metric-grid traffic-analytics-metrics">
            <div className="metric-card"><span>Current vehicles</span><strong>{latest?.vehicles ?? 0}</strong><small>{selectedScope}</small></div>
            <div className="metric-card"><span>Current pedestrians</span><strong>{latest?.pedestrians ?? 0}</strong><small>{selectedScope}</small></div>
            <div className="metric-card"><span>Average vehicles</span><strong>{summary?.average_vehicles ?? 0}</strong><small>{summary?.sample_count ?? 0} samples</small></div>
            <div className="metric-card"><span>Average pedestrians</span><strong>{summary?.average_pedestrians ?? 0}</strong><small>{summary?.sample_count ?? 0} samples</small></div>
            <div className="metric-card"><span>Peak vehicles</span><strong>{summary?.peak_vehicles.count ?? 0}</strong><small>{timestampLabel(summary?.peak_vehicles.recorded_at_ms ?? null)}</small></div>
            <div className="metric-card"><span>Peak pedestrians</span><strong>{summary?.peak_pedestrians.count ?? 0}</strong><small>{timestampLabel(summary?.peak_pedestrians.recorded_at_ms ?? null)}</small></div>
          </div>

          <div className="two-column-grid">
            <section className="panel">
              <div className="panel-header"><h2>Region summary</h2><span className="status-pill">occupancy</span></div>
              <div className="camera-status-list training-status-list">
                <div><span>Configured count scopes</span><strong>{regionOptions.length}</strong></div>
                <div><span>Stored samples</span><strong>{history?.stored_samples ?? 0}</strong></div>
                <div><span>Retention cap</span><strong>{history?.max_samples ?? 0}</strong></div>
                <div><span>Busiest region</span><strong>{summary?.busiest_region?.label ?? "not enough data"}</strong></div>
              </div>
              {summary?.busiest_region && <p className="small-note">Highest average combined occupancy: {summary.busiest_region.average_total} detected objects/sample.</p>}
            </section>

            <section className="panel">
              <div className="panel-header"><h2>Simulation phase events</h2><span className="status-pill muted">context only</span></div>
              <div className="camera-status-list training-status-list">
                <div><span>Phase changes</span><strong>{summary?.phase_change_count ?? 0}</strong></div>
                <div><span>Latest phase</span><strong>{latest?.phase?.split("_").join(" ") ?? "none"}</strong></div>
                <div><span>Latest change</span><strong>{phaseChange ? `${phaseChange.from.replaceAll("_", " ")} → ${phaseChange.to.replaceAll("_", " ")}` : "none"}</strong></div>
                <div><span>Change time</span><strong>{timestampLabel(phaseChange?.recorded_at_ms ?? null)}</strong></div>
              </div>
            </section>
          </div>
        </>
      ) : (
        <>
          <div className="metric-grid traffic-analytics-metrics">
            <div className="metric-card"><span>Unique vehicle passages</span><strong>{flowSummary?.unique_vehicle_passages ?? 0}</strong><small>counting-line crossings</small></div>
            <div className="metric-card"><span>Unique pedestrian passages</span><strong>{flowSummary?.unique_pedestrian_passages ?? 0}</strong><small>counting-line crossings</small></div>
            <div className="metric-card"><span>Region entries</span><strong>{flowSummary?.region_entries ?? 0}</strong><small>outside → inside</small></div>
            <div className="metric-card"><span>Region exits</span><strong>{flowSummary?.region_exits ?? 0}</strong><small>inside → outside</small></div>
            <div className="metric-card"><span>Average dwell</span><strong>{durationLabel(flowSummary?.average_dwell_ms)}</strong><small>completed region visits</small></div>
            <div className="metric-card"><span>Pedestrian wait</span><strong>{durationLabel(flowSummary?.average_pedestrian_wait_ms)}</strong><small>pedestrian waiting zones</small></div>
          </div>

          <div className="two-column-grid">
            <section className="panel">
              <div className="panel-header"><h2>Directional passages</h2><span className="status-pill">unique flow</span></div>
              <div className="camera-status-list training-status-list">
                {Object.entries(flowSummary?.direction_counts ?? {}).length === 0
                  ? <div><span>No line crossings yet</span><strong>0</strong></div>
                  : Object.entries(flowSummary?.direction_counts ?? {}).map(([direction, count]) => (
                    <div key={direction}><span>{direction.split("_").join(" ")}</span><strong>{count}</strong></div>
                  ))}
              </div>
              <p className="small-note">Direction is derived from the dominant movement axis at the line crossing: left/right or top/bottom.</p>
            </section>

            <section className="panel">
              <div className="panel-header"><h2>Flow storage</h2><span className="status-pill muted">runtime data</span></div>
              <div className="camera-status-list training-status-list">
                <div><span>Stored events</span><strong>{flow?.stored_events ?? 0}</strong></div>
                <div><span>Retention cap</span><strong>{flow?.max_events ?? 0}</strong></div>
                <div><span>Unique event tracks</span><strong>{flowSummary?.unique_event_tracks ?? 0}</strong></div>
                <div><span>Latest event</span><strong>{timestampLabel(flow?.newest_event_at_ms ?? null)}</strong></div>
              </div>
              <p className="small-note">Flow events persist under outputs/traffic_flow/ and are excluded from source patches.</p>
            </section>
          </div>

          <section className="panel">
            <div className="panel-header"><h2>Recent tracking events</h2><span className="status-pill">{recentFlowEvents.length} shown</span></div>
            {recentFlowEvents.length === 0 ? (
              <p className="placeholder-copy">Draw a counting line or let tracked objects enter/exit configured regions to generate events.</p>
            ) : (
              <div className="traffic-event-table-wrap">
                <table className="traffic-event-table">
                  <thead><tr><th>Time</th><th>Track</th><th>Class</th><th>Event</th><th>Scope</th><th>Direction / dwell</th></tr></thead>
                  <tbody>
                    {recentFlowEvents.map((event) => (
                      <tr key={event.event_id}>
                        <td>{new Date(event.timestamp_ms).toLocaleTimeString()}</td>
                        <td>{event.track_id}</td>
                        <td>{event.class_name}</td>
                        <td>{eventLabel(event.event_type)}</td>
                        <td>{event.line_label ?? event.region_label ?? "—"}</td>
                        <td>{event.direction?.split("_").join(" ") ?? (event.dwell_ms !== undefined ? durationLabel(event.dwell_ms) : "—")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}

      <section className="panel">
        <div className="panel-header"><h2>Configure analytics geometry</h2><span className="status-pill">Zone Editor</span></div>
        <p className="placeholder-copy"><strong>Counting regions</strong> provide occupancy plus track entry/exit/dwell metrics. <strong>Counting lines</strong> use exactly two points and create directional unique-passage events when a tracked object crosses them. Both remain analytics-only and do not change simulated signal decisions.</p>
      </section>
      <FunctionChecklist area="Traffic analytics" />
    </div>
  );
}
