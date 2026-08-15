import { useCallback, useEffect, useMemo, useState } from "react";
import { clearTrafficHistory, fetchTrafficHistory, trafficHistoryExportUrl } from "../api";
import { FunctionChecklist } from "../components/FunctionChecklist";
import { TrafficHistoryChart } from "../components/TrafficHistoryChart";
import type { TrafficHistory } from "../types";
import "./trafficAnalytics.css";

const WINDOWS = [
  { label: "1 min", value: 1 },
  { label: "5 min", value: 5 },
  { label: "15 min", value: 15 },
  { label: "1 hour", value: 60 },
  { label: "6 hours", value: 360 },
  { label: "All stored", value: 0 },
];

function timestampLabel(timestampMs: number | null): string {
  if (!timestampMs) return "none";
  return new Date(timestampMs).toLocaleString();
}

export function TrafficAnalyticsPage() {
  const [history, setHistory] = useState<TrafficHistory | null>(null);
  const [minutes, setMinutes] = useState(15);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [clearing, setClearing] = useState(false);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const next = await fetchTrafficHistory(minutes, regionId);
      setHistory(next);
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Traffic history could not be loaded.");
    } finally {
      setRefreshing(false);
    }
  }, [minutes, regionId]);

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
  const exportUrl = useMemo(() => trafficHistoryExportUrl(minutes, regionId), [minutes, regionId]);

  async function clearHistory() {
    if (!window.confirm("Clear all stored traffic occupancy history? This only removes analytics history; captures, labels, zones, and trained models are not affected.")) return;
    setClearing(true);
    try {
      await clearTrafficHistory();
      await refresh();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Traffic history could not be cleared.");
    } finally {
      setClearing(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Traffic occupancy over time</h2>
            <p className="placeholder-copy">Detection-backed vehicle and pedestrian occupancy samples recorded while the backend is running.</p>
          </div>
          <span className="status-pill">{history?.recording ? `${history.sample_interval_ms} ms sampling` : "checking"}</span>
        </div>

        <div className="traffic-analytics-controls">
          <label>Time window
            <select value={minutes} onChange={(event) => setMinutes(Number(event.target.value))}>
              {WINDOWS.map((windowOption) => <option key={windowOption.value} value={windowOption.value}>{windowOption.label}</option>)}
            </select>
          </label>
          <label>Count scope
            <select value={regionId ?? ""} onChange={(event) => setRegionId(event.target.value || null)}>
              <option value="">Whole frame</option>
              {regionOptions.map((region) => <option key={region.id} value={region.id}>{region.label} ({region.type.split("_").join(" ")})</option>)}
            </select>
          </label>
          <div className="button-row wrap-row traffic-analytics-actions">
            <button type="button" onClick={() => void refresh()} disabled={refreshing}>{refreshing ? "Refreshing..." : "Refresh"}</button>
            <button type="button" onClick={() => window.location.assign(exportUrl)}>Export CSV</button>
            <button type="button" onClick={() => void clearHistory()} disabled={clearing}>{clearing ? "Clearing..." : "Clear history"}</button>
          </div>
        </div>

        <TrafficHistoryChart points={history?.points ?? []} />
        {error && <p className="error-message">{error}</p>}
        <p className="small-note">Scope: <strong>{selectedScope}</strong>. These values are sampled per-frame occupancy counts, not unique passage counts; the current prototype does not track stable object IDs across frames.</p>
      </section>

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
          <div className="panel-header"><h2>Region summary</h2><span className="status-pill">analytics</span></div>
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
          <p className="small-note">Phase events are recorded only to correlate analytics with the simulation recommendation. They do not represent physical traffic-signal control.</p>
        </section>
      </div>

      <section className="panel">
        <div className="panel-header"><h2>Using counting regions</h2><span className="status-pill">multiple regions supported</span></div>
        <p className="placeholder-copy">Open Zone Editor, create one or more zones with type <strong>counting region</strong>, save them, then select those regions above. Counting regions are analytics-only and do not change the traffic-phase recommendation rules.</p>
      </section>
      <FunctionChecklist area="Traffic analytics" />
    </div>
  );
}
