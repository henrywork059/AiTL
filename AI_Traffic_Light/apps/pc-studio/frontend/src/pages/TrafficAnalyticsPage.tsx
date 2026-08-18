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
      ? "Clear all stored occupancy samples? Flow events, captures, labels, zones, and models will not be changed."
      : "Clear all stored tracked flow events? Occupancy history, captures, labels, zones, and models will not be changed.";
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
            <h2>Traffic measurements</h2>
            <p className="placeholder-copy">Occupancy samples how many detected objects are present. Flow / Tracks records track-derived crossings and region events. Keep the two metrics separate when interpreting results.</p>
          </div>
          <div className="traffic-mode-tabs" role="group" aria-label="Traffic analytics mode">
            <button type="button" className={mode === "occupancy" ? "active" : ""} onClick={() => setMode("occupancy")}>Occupancy</button>
            <button type="button" className={mode === "flow" ? "active" : ""} onClick={() => setMode("flow")}>Flow / Tracks</button>
          </div>
        </div>

        <div className="traffic-analytics-controls">
          <label>Time window
            <select value={minutes} onChange={(event) => setMinutes(Number(event.target.value))}>
              {WINDOWS.map((windowOption) => <option key={windowOption.value} value={windowOption.value}>{windowOption.label}</option>)}
            </select>
          </label>

          {mode === "occupancy" ? (
            <label>Area
              <select value={regionId ?? ""} onChange={(event) => setRegionId(event.target.value || null)}>
                <option value="">Whole frame</option>
                {regionOptions.map((region) => <option key={region.id} value={region.id}>{region.label} ({region.type.split("_").join(" ")})</option>)}
              </select>
            </label>
          ) : (
            <>
              <label>Event scope
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
            <button className="primary" type="button" onClick={() => void refresh()} disabled={refreshing}>{refreshing ? "Refreshing..." : "Refresh"}</button>
            <button type="button" onClick={() => window.location.assign(mode === "occupancy" ? occupancyExportUrl : flowExportUrl)}>Export CSV</button>
            <button className="danger" type="button" onClick={() => void clearCurrent()} disabled={clearing}>{clearing ? "Clearing..." : mode === "occupancy" ? "Clear occupancy history" : "Clear flow history"}</button>
          </div>
        </div>

        {mode === "occupancy" ? (
          <>
            <TrafficHistoryChart points={history?.points ?? []} />
            <p className="small-note">Selected area: <strong>{selectedScope}</strong>. Occupancy is a sampled present-in-frame count; adding samples together does not produce throughput.</p>
          </>
        ) : (
          <>
            <TrafficFlowChart buckets={flow?.buckets ?? []} series={flowRegionId ? "regions" : "passages"} />
            <p className="small-note">A passage is counted when a stable prototype track crosses a configured counting line. Each track is counted at most once per line in the current session.</p>
          </>
        )}
        {error && <p className="error-message">{error}</p>}
      </section>

      {mode === "occupancy" ? (
        <>
          <div className="metric-grid traffic-analytics-metrics">
            <div className="metric-card"><span>Vehicles now</span><strong>{latest?.vehicles ?? 0}</strong><small>{selectedScope}</small></div>
            <div className="metric-card"><span>Pedestrians now</span><strong>{latest?.pedestrians ?? 0}</strong><small>{selectedScope}</small></div>
            <div className="metric-card"><span>Average vehicles</span><strong>{summary?.average_vehicles ?? 0}</strong><small>{summary?.sample_count ?? 0} samples</small></div>
            <div className="metric-card"><span>Average pedestrians</span><strong>{summary?.average_pedestrians ?? 0}</strong><small>{summary?.sample_count ?? 0} samples</small></div>
            <div className="metric-card"><span>Peak vehicles</span><strong>{summary?.peak_vehicles.count ?? 0}</strong><small>{timestampLabel(summary?.peak_vehicles.recorded_at_ms ?? null)}</small></div>
            <div className="metric-card"><span>Peak pedestrians</span><strong>{summary?.peak_pedestrians.count ?? 0}</strong><small>{timestampLabel(summary?.peak_pedestrians.recorded_at_ms ?? null)}</small></div>
          </div>

          <div className="two-column-grid">
            <section className="panel">
              <div className="panel-header"><h2>Occupancy summary</h2><span className="status-pill muted">sampled counts</span></div>
              <div className="camera-status-list training-status-list">
                <div><span>Configured regions</span><strong>{regionOptions.length}</strong></div>
                <div><span>Stored samples</span><strong>{history?.stored_samples ?? 0}</strong></div>
                <div><span>Retention limit</span><strong>{history?.max_samples ?? 0}</strong></div>
                <div><span>Highest average region</span><strong>{summary?.busiest_region?.label ?? "not enough data"}</strong></div>
              </div>
              {summary?.busiest_region && <p className="small-note">Average combined occupancy in that region: {summary.busiest_region.average_total} detected objects per sample.</p>}
            </section>

            <section className="panel">
              <div className="panel-header"><h2>Signal-phase context</h2><span className="status-pill muted">simulation</span></div>
              <div className="camera-status-list training-status-list">
                <div><span>Phase changes</span><strong>{summary?.phase_change_count ?? 0}</strong></div>
                <div><span>Current / latest phase</span><strong>{latest?.phase?.split("_").join(" ") ?? "none"}</strong></div>
                <div><span>Latest transition</span><strong>{phaseChange ? `${phaseChange.from.replaceAll("_", " ")} → ${phaseChange.to.replaceAll("_", " ")}` : "none"}</strong></div>
                <div><span>Transition time</span><strong>{timestampLabel(phaseChange?.recorded_at_ms ?? null)}</strong></div>
              </div>
            </section>
          </div>
        </>
      ) : (
        <>
          <div className="metric-grid traffic-analytics-metrics">
            <div className="metric-card"><span>Vehicle passages</span><strong>{flowSummary?.unique_vehicle_passages ?? 0}</strong><small>unique line crossings</small></div>
            <div className="metric-card"><span>Pedestrian passages</span><strong>{flowSummary?.unique_pedestrian_passages ?? 0}</strong><small>unique line crossings</small></div>
            <div className="metric-card"><span>Region entries</span><strong>{flowSummary?.region_entries ?? 0}</strong><small>outside → inside</small></div>
            <div className="metric-card"><span>Region exits</span><strong>{flowSummary?.region_exits ?? 0}</strong><small>inside → outside</small></div>
            <div className="metric-card"><span>Average dwell</span><strong>{durationLabel(flowSummary?.average_dwell_ms)}</strong><small>completed region visits</small></div>
            <div className="metric-card"><span>Average pedestrian wait</span><strong>{durationLabel(flowSummary?.average_pedestrian_wait_ms)}</strong><small>pedestrian waiting zones</small></div>
          </div>

          <div className="two-column-grid">
            <section className="panel">
              <div className="panel-header"><h2>Passage direction</h2><span className="status-pill status-secondary">tracked flow</span></div>
              <div className="camera-status-list training-status-list">
                {Object.entries(flowSummary?.direction_counts ?? {}).length === 0
                  ? <div><span>No line crossings recorded</span><strong>0</strong></div>
                  : Object.entries(flowSummary?.direction_counts ?? {}).map(([direction, count]) => (
                    <div key={direction}><span>{direction.split("_").join(" ")}</span><strong>{count}</strong></div>
                  ))}
              </div>
              <p className="small-note">Direction is derived from the dominant movement axis when the track crosses the configured line.</p>
            </section>

            <section className="panel">
              <div className="panel-header"><h2>Flow-event storage</h2><span className="status-pill muted">runtime data</span></div>
              <div className="camera-status-list training-status-list">
                <div><span>Stored events</span><strong>{flow?.stored_events ?? 0}</strong></div>
                <div><span>Retention limit</span><strong>{flow?.max_events ?? 0}</strong></div>
                <div><span>Tracks represented</span><strong>{flowSummary?.unique_event_tracks ?? 0}</strong></div>
                <div><span>Latest event</span><strong>{timestampLabel(flow?.newest_event_at_ms ?? null)}</strong></div>
              </div>
              <p className="small-note">Flow events are runtime data under <code>outputs/traffic_flow/</code> and are excluded from source patches.</p>
            </section>
          </div>

          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>Recent tracked events</h2>
                <p className="placeholder-copy">Most recent line crossings and region entry/exit/dwell events for the selected filters.</p>
              </div>
              <span className="status-pill muted">{recentFlowEvents.length} shown</span>
            </div>
            {recentFlowEvents.length === 0 ? (
              <p className="placeholder-copy">No matching events yet. Configure a counting line or region and allow tracked objects to cross or enter it.</p>
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
        <div className="panel-header"><h2>Analytics geometry</h2><span className="status-pill status-info">Zone Editor</span></div>
        <p className="placeholder-copy"><strong>Counting regions</strong> support occupancy and track entry/exit/dwell metrics. <strong>Counting lines</strong> use two points and create directional passage events. Both are analytics geometry and do not directly alter simulated signal timing.</p>
      </section>
      <FunctionChecklist area="Traffic analytics" />
    </div>
  );
}
