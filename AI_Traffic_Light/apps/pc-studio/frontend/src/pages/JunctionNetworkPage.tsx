import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import { fetchJunctionNetworkOverview, resetJunctionNetwork, saveJunctionNetwork } from "../lib/junctionNetworkApi";
import { useSerialPolling } from "../lib/useSerialPolling";
import type {
  JunctionCameraView,
  JunctionConfig,
  JunctionLink,
  JunctionLoadLevel,
  JunctionNetworkConfig,
  JunctionNetworkOverview,
  JunctionOverviewNode,
} from "../types/junctionNetwork";
import "./junctionNetworkPage.css";

const LOAD_LABELS: Record<JunctionLoadLevel, string> = {
  unavailable: "No live data",
  clear: "Clear",
  light: "Light",
  moderate: "Moderate",
  heavy: "Heavy",
};

function cloneConfig(config: JunctionNetworkConfig): JunctionNetworkConfig {
  return JSON.parse(JSON.stringify(config)) as JunctionNetworkConfig;
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
}

function loadClass(level: JunctionLoadLevel): string {
  return `junction-load junction-load-${level}`;
}

function eventClass(severity: string): string {
  if (severity === "critical") return "junction-event junction-event-critical";
  if (severity === "attention") return "junction-event junction-event-attention";
  return "junction-event junction-event-info";
}

function warningClass(severity: string): string {
  if (severity === "critical") return "junction-warning junction-warning-critical";
  if (severity === "warning") return "junction-warning junction-warning-warning";
  return "junction-warning junction-warning-info";
}

function phaseLabel(phase: string | null): string {
  if (!phase) return "No live phase";
  return phase.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function nextId(prefix: string, existing: string[]): string {
  const base = `${prefix}_${Date.now().toString(36)}`;
  if (!existing.includes(base)) return base;
  let suffix = 2;
  while (existing.includes(`${base}_${suffix}`)) suffix += 1;
  return `${base}_${suffix}`;
}

function unsavedOverview(config: JunctionConfig): JunctionOverviewNode {
  return {
    id: config.id,
    label: config.label,
    enabled: config.enabled,
    active_intersection: false,
    position: config.position,
    source_ids: config.source_ids,
    primary_source_id: config.primary_source_id,
    signal_profile: config.signal_profile,
    cameras: [],
    camera_count: config.source_ids.length,
    reachable_camera_count: 0,
    streaming_camera_count: 0,
    live: {
      available: false,
      pipeline_source_active: false,
      source_id: null,
      source_mapping_matched: false,
      observation_provenance: "unavailable",
      phase: null,
      decision: null,
      decision_reason: null,
      evaluated_at_ms: null,
      source_timestamp_ms: null,
      vehicle: { total: 0, waiting: 0, load: "unavailable" },
      pedestrian: { total: 0, waiting: 0, crossing: 0, load: "unavailable" },
      decision_context: null,
    },
    events: [],
    warnings: [],
    warning_count: 0,
    event_count: 0,
  };
}

export function JunctionNetworkPage() {
  const [overview, setOverview] = useState<JunctionNetworkOverview | null>(null);
  const [savedConfig, setSavedConfig] = useState<JunctionNetworkConfig | null>(null);
  const [draft, setDraft] = useState<JunctionNetworkConfig | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [linkTarget, setLinkTarget] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ id: string; pointerId: number } | null>(null);

  const initialize = useCallback(async () => {
    try {
      const next = await fetchJunctionNetworkOverview();
      const config = cloneConfig(next.network);
      setOverview(next);
      setSavedConfig(config);
      setDraft(cloneConfig(config));
      setSelectedId((current) => current && config.intersections.some((item) => item.id === current)
        ? current
        : config.active_intersection_id);
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Junction Network could not be loaded.");
    }
  }, []);

  useEffect(() => {
    void initialize();
  }, [initialize]);

  const pollOverview = useCallback(async () => {
    try {
      setOverview(await fetchJunctionNetworkOverview());
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Live junction status could not be refreshed.");
    }
  }, []);

  useSerialPolling(pollOverview, 1000, { enabled: Boolean(draft), immediate: false });

  const dirty = useMemo(
    () => Boolean(savedConfig && draft && JSON.stringify(savedConfig) !== JSON.stringify(draft)),
    [savedConfig, draft],
  );

  const selectedConfig = useMemo(
    () => draft?.intersections.find((item) => item.id === selectedId) ?? null,
    [draft, selectedId],
  );

  const overviewById = useMemo(
    () => new Map((overview?.junctions ?? []).map((item) => [item.id, item])),
    [overview],
  );

  const selectedOverview = selectedConfig
    ? overviewById.get(selectedConfig.id) ?? unsavedOverview(selectedConfig)
    : null;

  const savedCameraIds = useMemo(
    () => new Set((overview?.available_cameras ?? []).map((camera) => camera.source_id)),
    [overview],
  );

  const relatedLinks = useMemo(
    () => draft && selectedId
      ? draft.links.filter((link) => link.source_intersection_id === selectedId || link.destination_intersection_id === selectedId)
      : [],
    [draft, selectedId],
  );

  const linkTargets = useMemo(
    () => draft && selectedId ? draft.intersections.filter((item) => item.id !== selectedId) : [],
    [draft, selectedId],
  );

  useEffect(() => {
    if (!linkTarget || !linkTargets.some((item) => item.id === linkTarget)) {
      setLinkTarget(linkTargets[0]?.id ?? "");
    }
  }, [linkTarget, linkTargets]);

  function mutateConfig(mutator: (next: JunctionNetworkConfig) => void) {
    setDraft((current) => {
      if (!current) return current;
      const next = cloneConfig(current);
      mutator(next);
      return next;
    });
    setNotice(null);
  }

  function mutateJunction(id: string, mutator: (junction: JunctionConfig) => void) {
    mutateConfig((next) => {
      const junction = next.intersections.find((item) => item.id === id);
      if (junction) mutator(junction);
    });
  }

  async function save() {
    if (!draft) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const saved = await saveJunctionNetwork(draft);
      const nextOverview = await fetchJunctionNetworkOverview();
      setSavedConfig(cloneConfig(saved));
      setDraft(cloneConfig(saved));
      setOverview(nextOverview);
      setSelectedId((current) => current && saved.intersections.some((item) => item.id === current)
        ? current
        : saved.active_intersection_id);
      setNotice("Junction layout, links and camera assignments saved.");
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Junction network could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function reset() {
    if (!window.confirm("Reset the junction network to the default single-junction configuration?")) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const saved = await resetJunctionNetwork();
      const nextOverview = await fetchJunctionNetworkOverview();
      setSavedConfig(cloneConfig(saved));
      setDraft(cloneConfig(saved));
      setOverview(nextOverview);
      setSelectedId(saved.active_intersection_id);
      setNotice("Junction network reset to defaults.");
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Junction network could not be reset.");
    } finally {
      setSaving(false);
    }
  }

  function addJunction() {
    if (!draft || draft.intersections.length >= 16) return;
    const id = nextId("junction", draft.intersections.map((item) => item.id));
    const offset = (draft.intersections.length % 5) * 6;
    mutateConfig((next) => {
      next.intersections.push({
        id,
        label: `Junction ${next.intersections.length + 1}`,
        enabled: true,
        source_ids: [],
        primary_source_id: null,
        zone_ids: [],
        signal_profile: "Normal",
        position: { x: clamp(50 + offset, 8, 92), y: clamp(50 - offset, 8, 92) },
      });
    });
    setSelectedId(id);
  }

  function removeSelectedJunction() {
    if (!draft || !selectedConfig || draft.intersections.length <= 1) return;
    if (!window.confirm(`Remove ${selectedConfig.label} and its connected lines from this draft?`)) return;
    const removedId = selectedConfig.id;
    mutateConfig((next) => {
      next.intersections = next.intersections.filter((item) => item.id !== removedId);
      next.links = next.links.filter(
        (link) => link.source_intersection_id !== removedId && link.destination_intersection_id !== removedId,
      );
      if (next.active_intersection_id === removedId) {
        next.active_intersection_id = next.intersections[0].id;
      }
    });
    setSelectedId(draft.intersections.find((item) => item.id !== removedId)?.id ?? null);
  }

  function setActiveJunction(id: string) {
    mutateConfig((next) => { next.active_intersection_id = id; });
  }

  function cameraOwner(sourceId: string): JunctionConfig | null {
    return draft?.intersections.find((item) => item.source_ids.includes(sourceId)) ?? null;
  }

  function toggleCamera(sourceId: string, checked: boolean) {
    if (!draft || !selectedConfig) return;
    const owner = cameraOwner(sourceId);
    if (checked && owner && owner.id !== selectedConfig.id) {
      if (!window.confirm(`Reassign ${sourceId} from ${owner.label} to ${selectedConfig.label}?`)) return;
    }

    mutateConfig((next) => {
      for (const junction of next.intersections) {
        if (junction.id === selectedConfig.id) continue;
        if (junction.source_ids.includes(sourceId)) {
          junction.source_ids = junction.source_ids.filter((item) => item !== sourceId);
          if (junction.primary_source_id === sourceId) {
            junction.primary_source_id = junction.source_ids[0] ?? null;
          }
        }
      }
      const junction = next.intersections.find((item) => item.id === selectedConfig.id);
      if (!junction) return;
      if (checked) {
        if (!junction.source_ids.includes(sourceId)) junction.source_ids.push(sourceId);
        if (!junction.primary_source_id) junction.primary_source_id = sourceId;
      } else {
        junction.source_ids = junction.source_ids.filter((item) => item !== sourceId);
        if (junction.primary_source_id === sourceId) junction.primary_source_id = junction.source_ids[0] ?? null;
      }
    });
  }

  function setPrimarySource(sourceId: string | null) {
    if (!selectedConfig) return;
    mutateJunction(selectedConfig.id, (junction) => {
      junction.primary_source_id = sourceId && junction.source_ids.includes(sourceId) ? sourceId : null;
    });
  }

  function addLink() {
    if (!draft || !selectedConfig || !linkTarget) return;
    if (draft.links.some(
      (link) => link.source_intersection_id === selectedConfig.id && link.destination_intersection_id === linkTarget,
    )) {
      setError("That directed junction connection already exists.");
      return;
    }
    const id = nextId("link", draft.links.map((item) => item.id));
    mutateConfig((next) => {
      next.links.push({
        id,
        enabled: true,
        source_intersection_id: selectedConfig.id,
        destination_intersection_id: linkTarget,
        source_approach: "outbound",
        destination_approach: "inbound",
        travel_time_seconds: 10,
      });
    });
  }

  function mutateLink(id: string, mutator: (link: JunctionLink) => void) {
    mutateConfig((next) => {
      const link = next.links.find((item) => item.id === id);
      if (link) mutator(link);
    });
  }

  function removeLink(id: string) {
    mutateConfig((next) => { next.links = next.links.filter((item) => item.id !== id); });
  }

  function setNodePosition(id: string, event: ReactPointerEvent) {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;
    const x = clamp(((event.clientX - rect.left) / rect.width) * 100, 5, 95);
    const y = clamp(((event.clientY - rect.top) / rect.height) * 100, 7, 93);
    mutateJunction(id, (junction) => { junction.position = { x: Number(x.toFixed(2)), y: Number(y.toFixed(2)) }; });
  }

  function startDrag(id: string, event: ReactPointerEvent<HTMLButtonElement>) {
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    setSelectedId(id);
    dragRef.current = { id, pointerId: event.pointerId };
    canvasRef.current?.setPointerCapture(event.pointerId);
    setNodePosition(id, event);
  }

  function moveDrag(event: ReactPointerEvent<HTMLDivElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    setNodePosition(drag.id, event);
  }

  function endDrag(event: ReactPointerEvent<HTMLDivElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    if (canvasRef.current?.hasPointerCapture(event.pointerId)) {
      canvasRef.current.releasePointerCapture(event.pointerId);
    }
    dragRef.current = null;
  }

  const availableCameras: JunctionCameraView[] = overview?.available_cameras ?? [];
  const otherMappedSources = selectedConfig?.source_ids.filter((sourceId) => !savedCameraIds.has(sourceId)) ?? [];

  if (!draft || !overview) {
    return (
      <div className="page-stack">
        <section className="panel">
          <h2>Junction Network</h2>
          <p className="placeholder-copy">Loading junction topology and camera assignments...</p>
          {error && <p className="error-message">{error}</p>}
        </section>
      </div>
    );
  }

  const summary = overview.summary;

  return (
    <div className="page-stack junction-network-page">
      <section className="panel junction-network-toolbar">
        <div className="junction-network-title-row">
          <div>
            <h2>Junction Network</h2>
            <p className="placeholder-copy">
              Arrange installed/model junctions, connect them with topology lines, assign one or more saved ESP cameras, and inspect live prototype traffic state.
            </p>
          </div>
          <div className="junction-network-actions">
            <button type="button" onClick={addJunction} disabled={draft.intersections.length >= 16}>Add junction</button>
            <button className="primary" type="button" onClick={() => void save()} disabled={!dirty || saving}>{saving ? "Saving..." : "Save network"}</button>
            <button type="button" onClick={() => void reset()} disabled={saving}>Reset</button>
          </div>
        </div>

        <div className="junction-network-summary">
          <div><strong>{draft.intersections.length}</strong><span>Junctions</span></div>
          <div><strong>{draft.links.length}</strong><span>Links</span></div>
          <div><strong>{summary.assigned_esp_camera_count}/{summary.saved_esp_camera_count}</strong><span>ESP assigned</span></div>
          <div><strong>{summary.reachable_esp_camera_count}</strong><span>ESP reachable</span></div>
          <div><strong>{summary.event_count}</strong><span>Live events</span></div>
          <div><strong>{summary.warning_junction_count}</strong><span>Warnings</span></div>
        </div>

        <div className="junction-network-status-row">
          <span className={`status-pill ${dirty ? "status-planned" : "status-implemented"}`}>{dirty ? "unsaved layout" : "saved"}</span>
          <span className="status-pill muted">Observation: {overview.observation_provenance}</span>
          <span className="status-pill muted">Updated {new Date(overview.generated_at_ms).toLocaleTimeString()}</span>
          <span className="small-note">{overview.scope_note}</span>
        </div>
        {notice && <p className="success-message">{notice}</p>}
        {error && <p className="error-message">{error}</p>}
      </section>

      <div className="junction-network-workspace">
        <section className="panel junction-map-panel">
          <div className="panel-header junction-map-header">
            <div>
              <h3>Network canvas</h3>
              <p className="placeholder-copy">Drag a junction using its top handle. Lines are configured topology, not live cooperative control.</p>
            </div>
            <div className="junction-legend" aria-label="Junction network legend">
              <span><i className="legend-swatch legend-clear" />clear/light</span>
              <span><i className="legend-swatch legend-moderate" />moderate</span>
              <span><i className="legend-swatch legend-heavy" />heavy</span>
              <span><i className="legend-swatch legend-warning" />warning/event</span>
            </div>
          </div>

          <div
            ref={canvasRef}
            className="junction-map-canvas"
            onPointerMove={moveDrag}
            onPointerUp={endDrag}
            onPointerCancel={endDrag}
          >
            <svg className="junction-link-layer" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
              <defs>
                <marker id="junction-link-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" />
                </marker>
              </defs>
              {draft.links.map((link) => {
                const source = draft.intersections.find((item) => item.id === link.source_intersection_id);
                const destination = draft.intersections.find((item) => item.id === link.destination_intersection_id);
                if (!source || !destination) return null;
                return (
                  <line
                    key={link.id}
                    x1={source.position.x}
                    y1={source.position.y}
                    x2={destination.position.x}
                    y2={destination.position.y}
                    className={link.enabled ? "junction-link" : "junction-link junction-link-disabled"}
                    markerEnd="url(#junction-link-arrow)"
                  />
                );
              })}
            </svg>

            {draft.intersections.map((config) => {
              const node = overviewById.get(config.id) ?? unsavedOverview(config);
              const selected = config.id === selectedId;
              const online = node.reachable_camera_count > 0 || node.cameras.some((camera) => camera.kind === "simulation" && camera.streaming);
              return (
                <article
                  key={config.id}
                  className={`junction-node ${selected ? "junction-node-selected" : ""} ${node.warning_count > 0 ? "junction-node-warning" : ""} ${config.enabled ? "" : "junction-node-disabled"}`}
                  style={{ left: `${config.position.x}%`, top: `${config.position.y}%` }}
                  onClick={() => setSelectedId(config.id)}
                >
                  <button className="junction-drag-handle" type="button" onPointerDown={(event) => startDrag(config.id, event)} title="Drag junction">
                    <span className={`junction-node-state ${online ? "junction-node-state-online" : ""}`} />
                    <span>{config.active_intersection_id ? "" : ""}</span>
                    <span className="junction-node-id">{config.id}</span>
                    <span className="junction-drag-symbol">•••</span>
                  </button>
                  <div className="junction-node-body">
                    <div className="junction-node-title-row">
                      <strong>{config.label}</strong>
                      {draft.active_intersection_id === config.id && <span className="junction-active-mark">ACTIVE</span>}
                    </div>
                    <div className="junction-node-loads">
                      <span className={loadClass(node.live.vehicle.load)} title={`Vehicles: ${LOAD_LABELS[node.live.vehicle.load]}`}>
                        V {LOAD_LABELS[node.live.vehicle.load]}
                      </span>
                      <span className={loadClass(node.live.pedestrian.load)} title={`Pedestrians: ${LOAD_LABELS[node.live.pedestrian.load]}`}>
                        P {LOAD_LABELS[node.live.pedestrian.load]}
                      </span>
                    </div>
                    <div className="junction-node-meta">
                      <span>CAM {config.source_ids.filter((source) => savedCameraIds.has(source)).length}</span>
                      <span>{node.live.pipeline_source_active ? phaseLabel(node.live.phase) : "No selected feed"}</span>
                    </div>
                    <div className="junction-node-alerts">
                      {node.event_count > 0 && <span className="junction-node-event-count">EV {node.event_count}</span>}
                      {node.warning_count > 0 && <span className="junction-node-warning-count">! {node.warning_count}</span>}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <aside className="panel junction-inspector">
          {selectedConfig && selectedOverview ? (
            <>
              <div className="panel-header">
                <div>
                  <h3>Junction details</h3>
                  <p className="placeholder-copy"><code>{selectedConfig.id}</code></p>
                </div>
                <span className={`status-pill ${selectedConfig.enabled ? "status-implemented" : "muted"}`}>{selectedConfig.enabled ? "enabled" : "disabled"}</span>
              </div>

              <div className="junction-form-grid">
                <label>Junction label
                  <input value={selectedConfig.label} maxLength={120} onChange={(event) => mutateJunction(selectedConfig.id, (junction) => { junction.label = event.target.value; })} />
                </label>
                <label className="junction-check-row">
                  <input type="checkbox" checked={selectedConfig.enabled} onChange={(event) => mutateJunction(selectedConfig.id, (junction) => { junction.enabled = event.target.checked; })} />
                  Enabled in network configuration
                </label>
              </div>

              <div className="junction-inline-actions">
                <button type="button" className={draft.active_intersection_id === selectedConfig.id ? "secondary" : ""} onClick={() => setActiveJunction(selectedConfig.id)} disabled={draft.active_intersection_id === selectedConfig.id}>
                  {draft.active_intersection_id === selectedConfig.id ? "Active junction" : "Set active junction"}
                </button>
                <button className="danger" type="button" onClick={removeSelectedJunction} disabled={draft.intersections.length <= 1}>Remove junction</button>
              </div>

              <section className="junction-inspector-section">
                <h4>Live state</h4>
                <div className="junction-live-grid">
                  <div><span>Vehicle load</span><strong className={loadClass(selectedOverview.live.vehicle.load)}>{LOAD_LABELS[selectedOverview.live.vehicle.load]}</strong><small>{selectedOverview.live.vehicle.total} total · {selectedOverview.live.vehicle.waiting} queued</small></div>
                  <div><span>Pedestrian load</span><strong className={loadClass(selectedOverview.live.pedestrian.load)}>{LOAD_LABELS[selectedOverview.live.pedestrian.load]}</strong><small>{selectedOverview.live.pedestrian.total} total · {selectedOverview.live.pedestrian.waiting} waiting · {selectedOverview.live.pedestrian.crossing} crossing</small></div>
                  <div><span>Signal</span><strong>{phaseLabel(selectedOverview.live.phase)}</strong><small>{selectedOverview.live.observation_provenance}</small></div>
                  <div><span>Decision</span><strong>{selectedOverview.live.decision ?? "Unavailable"}</strong><small>{selectedOverview.live.source_id ?? "No selected source"}</small></div>
                </div>
                {selectedOverview.live.decision_reason && <p className="small-note junction-decision-reason">{selectedOverview.live.decision_reason}</p>}
              </section>

              <section className="junction-inspector-section">
                <div className="junction-section-title">
                  <h4>ESP camera assignment</h4>
                  <span className="status-pill muted">{selectedConfig.source_ids.filter((source) => savedCameraIds.has(source)).length} assigned</span>
                </div>
                {availableCameras.length === 0 ? (
                  <p className="small-note">No saved ESP camera profiles are available. Add cameras in Camera Sources first.</p>
                ) : (
                  <div className="junction-camera-list">
                    {availableCameras.map((camera) => {
                      const checked = selectedConfig.source_ids.includes(camera.source_id);
                      const owner = cameraOwner(camera.source_id);
                      return (
                        <label key={camera.source_id} className="junction-camera-row">
                          <input type="checkbox" checked={checked} onChange={(event) => toggleCamera(camera.source_id, event.target.checked)} />
                          <span className={`junction-camera-state junction-camera-state-${camera.state}`} />
                          <span className="junction-camera-copy">
                            <strong>{camera.source_id}</strong>
                            <small>{camera.host ?? "no IP"} · {camera.state}{owner && owner.id !== selectedConfig.id ? ` · assigned to ${owner.label}` : ""}</small>
                          </span>
                          <span className="junction-camera-fps">{camera.measured_fps > 0 ? `${camera.measured_fps.toFixed(1)} FPS` : "—"}</span>
                        </label>
                      );
                    })}
                  </div>
                )}

                {selectedConfig.source_ids.length > 0 && (
                  <label className="junction-primary-select">Primary camera/source
                    <select value={selectedConfig.primary_source_id ?? ""} onChange={(event) => setPrimarySource(event.target.value || null)}>
                      <option value="">None</option>
                      {selectedConfig.source_ids.map((sourceId) => <option key={sourceId} value={sourceId}>{sourceId}</option>)}
                    </select>
                  </label>
                )}

                {otherMappedSources.length > 0 && (
                  <div className="junction-other-sources">
                    <span>Other mapped sources</span>
                    {otherMappedSources.map((sourceId) => <code key={sourceId}>{sourceId}</code>)}
                  </div>
                )}
              </section>

              <section className="junction-inspector-section">
                <div className="junction-section-title">
                  <h4>Connections</h4>
                  <span className="status-pill muted">{relatedLinks.length}</span>
                </div>
                {linkTargets.length > 0 && (
                  <div className="junction-add-link-row">
                    <select value={linkTarget} onChange={(event) => setLinkTarget(event.target.value)}>
                      {linkTargets.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
                    </select>
                    <button type="button" onClick={addLink}>Add line</button>
                  </div>
                )}
                <div className="junction-link-list">
                  {relatedLinks.map((link) => {
                    const outbound = link.source_intersection_id === selectedConfig.id;
                    const otherId = outbound ? link.destination_intersection_id : link.source_intersection_id;
                    const other = draft.intersections.find((item) => item.id === otherId);
                    return (
                      <div key={link.id} className="junction-link-row">
                        <div>
                          <strong>{outbound ? "→" : "←"} {other?.label ?? otherId}</strong>
                          <small>{link.id}</small>
                        </div>
                        <label>Travel s
                          <input type="number" min={0.1} max={300} step={0.1} value={link.travel_time_seconds} onChange={(event) => mutateLink(link.id, (item) => { item.travel_time_seconds = Number(event.target.value); })} />
                        </label>
                        <label className="junction-link-enabled"><input type="checkbox" checked={link.enabled} onChange={(event) => mutateLink(link.id, (item) => { item.enabled = event.target.checked; })} />on</label>
                        <button type="button" className="danger compact" onClick={() => removeLink(link.id)}>Remove</button>
                      </div>
                    );
                  })}
                  {relatedLinks.length === 0 && <p className="small-note">No topology lines touch this junction yet.</p>}
                </div>
              </section>

              <section className="junction-inspector-section">
                <div className="junction-section-title"><h4>Events</h4><span className="status-pill muted">{selectedOverview.event_count}</span></div>
                <div className="junction-message-list">
                  {selectedOverview.events.map((event, index) => (
                    <div key={`${event.type}-${index}`} className={eventClass(event.severity)}>
                      <strong>{event.label}</strong>
                      {event.detail && <span>{event.detail}</span>}
                      {event.provenance && <small>{event.provenance}</small>}
                    </div>
                  ))}
                  {selectedOverview.events.length === 0 && <p className="small-note">No current special event trigger for this junction.</p>}
                </div>
              </section>

              <section className="junction-inspector-section">
                <div className="junction-section-title"><h4>Warnings</h4><span className="status-pill muted">{selectedOverview.warning_count}</span></div>
                <div className="junction-message-list">
                  {selectedOverview.warnings.map((warning, index) => (
                    <div key={`${warning.code}-${index}`} className={warningClass(warning.severity)}>
                      <strong>{warning.code}</strong>
                      <span>{warning.message}</span>
                    </div>
                  ))}
                  {selectedOverview.warnings.length === 0 && <p className="small-note">No current warning for this junction.</p>}
                </div>
              </section>
            </>
          ) : (
            <p className="placeholder-copy">Select a junction node to inspect it.</p>
          )}
        </aside>
      </div>
    </div>
  );
}
