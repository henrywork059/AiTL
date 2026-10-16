import { useEffect, useMemo, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import { fetchCrosswalks, saveCrosswalks } from "../lib/crosswalksApi";
import { fetchCrosswalkSignalNetwork } from "../api";
import type { CrosswalkSignalNetwork } from "../api";
import { useSerialPolling } from "../lib/useSerialPolling";
import { CrosswalkSignalIndicators } from "./CrosswalkSignalIndicators";
import type { ScenarioSignalStatus } from "../types/signalScenarios";
import type {
  CrosswalkConfig, CrosswalkNetwork, CrosswalkNetworkEdge, CrosswalkNetworkPosition, CrosswalkMovementConflict,
} from "../types/crosswalks";
import type { JunctionCameraView, JunctionNetworkOverview } from "../types/junctionNetwork";
import "./crosswalkNetworkPanel.css";

type Props = {
  config: CrosswalkConfig;
  overview: JunctionNetworkOverview | null;
  onSaved: (config: CrosswalkConfig) => void;
  onRefresh: () => Promise<void>;
  simulationEnabled: boolean;
};

const EDGES: CrosswalkNetworkEdge[] = ["1", "2", "3", "4"];
const EMPTY_NETWORK: CrosswalkNetwork = { positions: {}, links: [] };
const MAX_LINKS = 64;
const MOVEMENT_CONFLICTS: { id: CrosswalkMovementConflict; label: string }[] = [
  { id: "vehicle_vehicle", label: "Vehicles at both crossings" },
  { id: "vehicle_pedestrian", label: "Source vehicles × destination pedestrians" },
  { id: "pedestrian_vehicle", label: "Source pedestrians × destination vehicles" },
  { id: "pedestrian_pedestrian", label: "Pedestrians at both crossings" },
];

function cloneNetwork(network?: CrosswalkNetwork): CrosswalkNetwork {
  return structuredClone(network ?? EMPTY_NETWORK);
}

function defaultPosition(index: number, total: number): CrosswalkNetworkPosition {
  const columns = Math.min(3, Math.max(1, total));
  const rows = Math.max(1, Math.ceil(total / columns));
  const column = index % columns;
  const x = columns === 1 ? 50 : columns === 2 ? (column === 0 ? 29 : 71) : [18, 50, 82][column];
  return { x, y: Math.round(((Math.floor(index / columns) + 0.5) / rows) * 10000) / 100 };
}

function cameraLabel(sourceId: string | null, cameras: Map<string, JunctionCameraView>): string {
  if (!sourceId) return "Not assigned";
  const camera = cameras.get(sourceId);
  if (!camera) return sourceId + " · Profile unavailable";
  if (camera.kind === "simulation") return sourceId + (camera.streaming ? " · Simulating" : " · Simulation stopped");
  if (camera.stream_connected) return sourceId + " · Streaming";
  return sourceId + (camera.device_reachable ? " · Connected" : " · Offline");
}

function nextLinkId(ids: string[]): string {
  const used = new Set(ids);
  let number = 1;
  while (used.has("crosslink_" + number)) number += 1;
  return "crosslink_" + number;
}

export function CrosswalkNetworkPanel({ config, overview, onSaved, onRefresh }: Props) {
  const [draft, setDraft] = useState<CrosswalkNetwork>(() => cloneNetwork(config.network));
  const incomingKey = JSON.stringify(config.network ?? EMPTY_NETWORK);
  const [savedKey, setSavedKey] = useState(incomingKey);
  const [selectedId, setSelectedId] = useState<string | null>(config.crosswalks[0]?.id ?? null);
  const [keyboardSource, setKeyboardSource] = useState<{ id: string; edge: CrosswalkNetworkEdge } | null>(null);
  const [linkPreview, setLinkPreview] = useState<{ from: CrosswalkNetworkPosition; to: CrosswalkNetworkPosition } | null>(null);
  const [hoverEdge, setHoverEdge] = useState<string | null>(null);
  const [edgeCenters, setEdgeCenters] = useState<Record<string, CrosswalkNetworkPosition>>({});
  const linkDragRef = useRef<{ id: string; edge: CrosswalkNetworkEdge; pointerId: number } | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [signalNetwork, setSignalNetwork] = useState<CrosswalkSignalNetwork | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ id: string; pointerId: number; offsetX: number; offsetY: number } | null>(null);

  const dirty = JSON.stringify(draft) !== savedKey;
  const crosswalks = config.crosswalks;
  const selected = crosswalks.find((item) => item.id === selectedId) ?? crosswalks[0] ?? null;
  const canvasHeight = Math.max(560, Math.ceil(crosswalks.length / 3) * 340);

  useEffect(() => {
    // A camera/status refresh must not erase unsaved connection or layout edits.
    if (!dirty && incomingKey !== savedKey) {
      setDraft(cloneNetwork(config.network));
      setSavedKey(incomingKey);
    }
  }, [config.network, dirty, incomingKey, savedKey]);

  const positions = useMemo(() => new Map(crosswalks.map((crosswalk, index) => [
    crosswalk.id, draft.positions[crosswalk.id] ?? defaultPosition(index, crosswalks.length),
  ] as const)), [crosswalks, draft.positions]);
  useSerialPolling(async () => { setSignalNetwork(await fetchCrosswalkSignalNetwork()); }, 1000,
    { onError: () => setSignalNetwork(null) });
  const cameras = useMemo(() => new Map(
    (overview?.available_cameras ?? []).map((camera) => [camera.source_id, camera]),
  ), [overview]);

  const countsByCrosswalk = useMemo(() => {
    const result = new Map<string, { label: string; total: number; class_counts: Record<string, number> }[]>();
    if (!overview || overview.observation_provenance === "unavailable") return result;
    for (const item of Object.values(overview.crosswalk_region_counts ?? {})) {
      if (item.source_id !== overview.current_frame_source_id) continue;
      const entries = result.get(item.crosswalk_id) ?? [];
      entries.push({ label: item.label, total: item.total, class_counts: item.class_counts });
      result.set(item.crosswalk_id, entries);
    }
    return result;
  }, [overview]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const updateEdgeCenters = () => {
      const bounds = canvas.getBoundingClientRect();
      if (!bounds.width || !bounds.height) return;
      const points: Record<string, CrosswalkNetworkPosition> = {};
      canvas.querySelectorAll<HTMLButtonElement>("[data-crosswalk-id][data-crosswalk-edge]").forEach((button) => {
        const id = button.dataset.crosswalkId;
        const edge = button.dataset.crosswalkEdge;
        if (!id || !edge) return;
        const rect = button.getBoundingClientRect();
        points[id + ":" + edge] = {
          x: (rect.left + rect.width / 2 - bounds.left) / bounds.width * 100,
          y: (rect.top + rect.height / 2 - bounds.top) / bounds.height * 100,
        };
      });
      setEdgeCenters((current) => JSON.stringify(current) === JSON.stringify(points) ? current : points);
    };
    updateEdgeCenters();
    const observer = new ResizeObserver(updateEdgeCenters);
    observer.observe(canvas);
    canvas.querySelectorAll<HTMLElement>(".crossing-network-node").forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, [positions, overview]);

  function edgeUnderPointer(clientX: number, clientY: number) {
    const button = document.elementFromPoint(clientX, clientY)?.closest<HTMLButtonElement>("[data-crosswalk-id][data-crosswalk-edge]");
    if (!button || !canvasRef.current?.contains(button)) return null;
    const id = button.dataset.crosswalkId;
    const edge = button.dataset.crosswalkEdge;
    if (!id || !EDGES.includes(edge as CrosswalkNetworkEdge)) return null;
    return { id, edge: edge as CrosswalkNetworkEdge };
  }

  function pointFromPointer(clientX: number, clientY: number): CrosswalkNetworkPosition | null {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return null;
    return {
      x: (clientX - rect.left) / rect.width * 100,
      y: (clientY - rect.top) / rect.height * 100,
    };
  }

  function changeDraft(next: CrosswalkNetwork) {
    setDraft(next);
    setNotice(null);
    setError(null);
  }

  function beginDrag(id: string, event: ReactPointerEvent<HTMLButtonElement>) {
    const canvas = canvasRef.current;
    const point = positions.get(id);
    if (!canvas || !point || saving) return;
    const bounds = canvas.getBoundingClientRect();
    dragRef.current = {
      id, pointerId: event.pointerId,
      offsetX: event.clientX - bounds.left - point.x * bounds.width / 100,
      offsetY: event.clientY - bounds.top - point.y * bounds.height / 100,
    };
    canvas.setPointerCapture(event.pointerId);
    setSelectedId(id);
    event.preventDefault();
  }

  function moveDrag(event: ReactPointerEvent<HTMLDivElement>) {
    const connection = linkDragRef.current;
    if (connection && connection.pointerId === event.pointerId) {
      const next = pointFromPointer(event.clientX, event.clientY);
      if (next) setLinkPreview((current) => current ? { ...current, to: next } : current);
      const target = edgeUnderPointer(event.clientX, event.clientY);
      setHoverEdge(target && target.id !== connection.id ? target.id + ":" + target.edge : null);
      return;
    }
    const drag = dragRef.current;
    const canvas = canvasRef.current;
    if (!drag || !canvas || drag.pointerId !== event.pointerId) return;
    const bounds = canvas.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return;
    const clamp = (value: number, margin: number) => Math.max(margin, Math.min(100 - margin, value));
    const x = clamp((event.clientX - bounds.left - drag.offsetX) / bounds.width * 100, 130 / bounds.width * 100);
    const y = clamp((event.clientY - bounds.top - drag.offsetY) / bounds.height * 100, 100 / bounds.height * 100);
    setDraft((current) => ({
      ...current, positions: {
        ...current.positions, [drag.id]: { x: Math.round(x * 100) / 100, y: Math.round(y * 100) / 100 },
      },
    }));
    setNotice(null);
  }

  function endDrag(event: ReactPointerEvent<HTMLDivElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    if (canvasRef.current?.hasPointerCapture(event.pointerId)) canvasRef.current.releasePointerCapture(event.pointerId);
    dragRef.current = null;
  }

  function connectEdges(fromId: string, fromEdge: CrosswalkNetworkEdge, toId: string, toEdge: CrosswalkNetworkEdge) {
    if (saving) return;
    if (fromId === toId) {
      setError("Connections must join two different crossings.");
      return;
    }
    if (draft.links.length >= MAX_LINKS) {
      setError("Maximum number of crossing connections reached.");
      return;
    }
    const duplicate = draft.links.some((link) =>
      (link.source_crosswalk_id === fromId && link.destination_crosswalk_id === toId
        && link.source_edge === fromEdge && link.destination_edge === toEdge)
      || (link.source_crosswalk_id === toId && link.destination_crosswalk_id === fromId
        && link.source_edge === toEdge && link.destination_edge === fromEdge));
    if (duplicate) {
      setError("These two numbered edges are already connected.");
      return;
    }
    changeDraft({
      ...draft, links: [...draft.links, {
        id: nextLinkId(draft.links.map((link) => link.id)),
        source_crosswalk_id: fromId, destination_crosswalk_id: toId,
        source_edge: fromEdge, destination_edge: toEdge,
      }],
    });
  }

  function beginConnection(id: string, edge: CrosswalkNetworkEdge, event: ReactPointerEvent<HTMLButtonElement>) {
    const canvas = canvasRef.current;
    if (!canvas || saving) return;
    const bounds = canvas.getBoundingClientRect();
    const rect = event.currentTarget.getBoundingClientRect();
    const origin = {
      x: (rect.left + rect.width / 2 - bounds.left) / bounds.width * 100,
      y: (rect.top + rect.height / 2 - bounds.top) / bounds.height * 100,
    };
    linkDragRef.current = { id, edge, pointerId: event.pointerId };
    setLinkPreview({ from: origin, to: origin });
    setHoverEdge(null);
    setKeyboardSource(null);
    setSelectedId(id);
    canvas.setPointerCapture(event.pointerId);
    event.preventDefault();
    event.stopPropagation();
  }

  function finishConnection(event: ReactPointerEvent<HTMLDivElement>): boolean {
    const connection = linkDragRef.current;
    if (!connection || connection.pointerId !== event.pointerId) return false;
    const target = edgeUnderPointer(event.clientX, event.clientY);
    if (target && target.id !== connection.id) connectEdges(connection.id, connection.edge, target.id, target.edge);
    linkDragRef.current = null;
    setLinkPreview(null);
    setHoverEdge(null);
    const canvas = canvasRef.current;
    if (canvas?.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
    return true;
  }

  function cancelConnection(event: ReactPointerEvent<HTMLDivElement>): boolean {
    const connection = linkDragRef.current;
    if (!connection || connection.pointerId !== event.pointerId) return false;
    linkDragRef.current = null;
    setLinkPreview(null);
    setHoverEdge(null);
    const canvas = canvasRef.current;
    if (canvas?.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
    return true;
  }

  function connectWithKeyboard(id: string, edge: CrosswalkNetworkEdge) {
    setSelectedId(id);
    if (keyboardSource) {
      if (keyboardSource.id !== id) connectEdges(keyboardSource.id, keyboardSource.edge, id, edge);
      setKeyboardSource(null);
    } else {
      setKeyboardSource({ id, edge });
    }
  }

  async function save() {
    if (!dirty || saving) return;
    setSaving(true);
    setError(null);
    try {
      // Keep freshly edited crossing names, regions and camera assignments intact.
      const latest = await fetchCrosswalks();
      if (JSON.stringify(latest.network ?? EMPTY_NETWORK) !== savedKey) {
        setError("The Network was modified elsewhere. Reload before saving to prevent an overwrite.");
        return;
      }
      const existing = new Set(latest.crosswalks.map((item) => item.id));
      const network: CrosswalkNetwork = {
        positions: Object.fromEntries(Object.entries(draft.positions).filter(([id]) => existing.has(id))),
        links: draft.links.filter((link) => existing.has(link.source_crosswalk_id) && existing.has(link.destination_crosswalk_id)),
      };
      const saved = await saveCrosswalks({ ...latest, network });
      setDraft(cloneNetwork(saved.network));
      setSavedKey(JSON.stringify(saved.network ?? EMPTY_NETWORK));
      onSaved(saved);
      setNotice("Crossing positions and connections saved.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to save Network.");
    } finally {
      setSaving(false);
    }
  }

  function reload() {
    if (dirty && !window.confirm("Discard unsaved Network edits?")) return;
    setDraft(cloneNetwork(config.network));
    setSavedKey(incomingKey);
    setNotice(null);
    setError(null);
    void onRefresh();
  }

  return (
    <section className="crossing-network-section" aria-label="Crossing Network">
      <div className="panel crossing-network-toolbar">
        <div className="panel-header">
          <div>
            <h2>Network</h2>
            <p className="placeholder-copy">Saved crossings appear automatically. Drag one numbered edge label to another crossing’s edge label to connect them.</p>
          </div>
          <div className="button-row">
            <button className="primary" type="button" disabled={!dirty || saving} onClick={() => void save()}>
              {saving ? "Saving..." : "Save network"}
            </button>
            <button type="button" disabled={saving} onClick={reload}>Reload</button>
            <button type="button" disabled={saving} onClick={() => void onRefresh()}>Refresh crossings</button>
          </div>
        </div>
        <div className="crossing-network-metrics">
          <span><strong>{crosswalks.length}</strong> crossings</span>
          <span><strong>{draft.links.length}</strong> connections</span>
          <span><strong>{crosswalks.filter((item) => item.camera_side_a_id || item.camera_side_b_id).length}</strong> with assigned cameras</span>
          <span><strong>{countsByCrosswalk.size}</strong> currently observed</span>
        </div>
        <p className="small-note">Each saved crosswalk has its own software-only controller. Real ESP cameras can drive a clearly labeled virtual signal preview, not a physical traffic light. Network links do not yet define conflicting movements or coordinate adjacent controllers.</p>
        {dirty && <p className="small-note" role="status">Unsaved Network changes</p>}
        {notice && <p className="success-message" role="status">{notice}</p>}
        {error && <p className="error-message" role="alert">{error}</p>}
      </div>

      <div className="crossing-network-layout">
        <div className="panel crossing-network-map">
          <div className="panel-header"><h3>Crossing map</h3><span className="small-note">Drag a title to move · Drag edge label to edge label to connect</span></div>
          <div className="crossing-network-scroll">
            <div ref={canvasRef} className="crossing-network-canvas" style={{ height: canvasHeight }}
              onPointerMove={moveDrag}
              onPointerUp={(event) => { if (!finishConnection(event)) endDrag(event); }}
              onPointerCancel={(event) => { if (!cancelConnection(event)) endDrag(event); }}>
              <svg className="crossing-network-links" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                {draft.links.map((link) => {
                  const a = edgeCenters[link.source_crosswalk_id + ":" + link.source_edge] ?? positions.get(link.source_crosswalk_id);
                  const b = edgeCenters[link.destination_crosswalk_id + ":" + link.destination_edge] ?? positions.get(link.destination_crosswalk_id);
                  if (!a || !b) return null;
                  return <line key={link.id} x1={a.x} y1={a.y} x2={b.x} y2={b.y} />;
                })}
                {linkPreview && <line className="crossing-network-preview" x1={linkPreview.from.x} y1={linkPreview.from.y}
                  x2={linkPreview.to.x} y2={linkPreview.to.y} />}
              </svg>
              {crosswalks.map((crosswalk) => {
                const position = positions.get(crosswalk.id);
                const observed = countsByCrosswalk.get(crosswalk.id) ?? [];
                const active = overview?.current_frame_source_id;
                const liveHere = Boolean(overview && overview.observation_provenance !== "unavailable" && active
                  && (active === crosswalk.camera_side_a_id || active === crosswalk.camera_side_b_id));
                const crosswalkSignal = signalNetwork?.crosswalks[crosswalk.id];
                const available = Boolean(crosswalkSignal?.signal);
                const adjacentNotice = crosswalkSignal?.coordination_status === "held"
                  ? crosswalkSignal.coordination_reason
                  : crosswalkSignal?.emergency_priority
                  ? "Priority from " + crosswalkSignal.emergency_priority.source_crosswalk_id + ": " + crosswalkSignal.emergency_priority.reason
                  : crosswalkSignal?.neighbors.length
                  ? "Linked to " + crosswalkSignal.neighbors.length + " crossing(s) · route off unless explicitly enabled"
                  : null;
                return (
                  <article key={crosswalk.id} className={"crossing-network-node" + (selected?.id === crosswalk.id ? " is-selected" : "")}
                    style={{ left: (position?.x ?? 50) + "%", top: (position?.y ?? 50) + "%" }}>
                    <button type="button" className="crossing-network-heading"
                      aria-pressed={selected?.id === crosswalk.id}
                      onClick={() => setSelectedId(crosswalk.id)}
                      onPointerDown={(event) => beginDrag(crosswalk.id, event)}>
                      <strong>{crosswalk.label}</strong><small>{crosswalk.location || "Crossing"}</small>
                    </button>
                    <div className="crossing-network-edge-grid" aria-label={"Edges of " + crosswalk.label}>
                      {EDGES.map((edge) => <button type="button" key={edge}
                        data-crosswalk-id={crosswalk.id} data-crosswalk-edge={edge}
                        className={"crossing-network-edge crossing-network-edge-" + edge
                          + (hoverEdge === crosswalk.id + ":" + edge ? " is-drop-target" : "")}
                        aria-label={crosswalk.label + " edge " + edge + ". Drag to another crossing edge."}
                        title="Drag this label to a label on another crossing"
                        aria-pressed={keyboardSource?.id === crosswalk.id && keyboardSource.edge === edge}
                        onPointerDown={(event) => beginConnection(crosswalk.id, edge, event)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            connectWithKeyboard(crosswalk.id, edge);
                          }
                        }}>{edge}</button>)}
                      <div className="crossing-network-status">
                        <small>Side A: {cameraLabel(crosswalk.camera_side_a_id, cameras)}</small>
                        <small>Side B: {cameraLabel(crosswalk.camera_side_b_id, cameras)}</small>
                        <span className={liveHere ? "status-pill status-implemented" : "status-pill muted"}>
                          {liveHere ? "Current AI/simulation source" : "Not currently observed"}
                        </span>
                        {liveHere && observed.slice(0, 3).map((item, index) => (
                          <small key={index}>{item.label}: {item.total} detected ({Object.entries(item.class_counts)
                            .map(([name, count]) => count + " " + name).join(", ") || "none"})</small>
                        ))}
                        {liveHere && observed.length > 3 && <small>+{observed.length - 3} regions</small>}
                        {liveHere && observed.length === 0 && <small>No current region counts</small>}
                      </div>
                    </div>
                    <CrosswalkSignalIndicators signal={(crosswalkSignal?.signal ?? null) as ScenarioSignalStatus | null} available={available} adjacentNotice={adjacentNotice} virtualPreview={crosswalkSignal?.status === "virtual"} />
                    {crosswalkSignal?.observation_provenance === "camera_ai" && <div className="crossing-signal-summary">
                      <small>AI region counts ({crosswalkSignal.camera_coverage ?? "partial"}): {Object.entries(crosswalkSignal.region_class_counts ?? {}).map(([regionId, classes]) =>
                        regionId + ": " + (Object.entries(classes).map(([name, count]) => name + " " + count).join(", ") || "0")
                      ).join(" · ") || "No configured regions"}</small>
                    </div>}
                  </article>
                );
              })}
              {crosswalks.length === 0 && <div className="crossing-network-empty">
                No crossings yet. Add and save one under Traffic → Crosswalks; a new box appears here automatically.
              </div>}
            </div>
          </div>
        </div>

        <aside className="panel crossing-network-inspector">
          {!selected ? <p className="placeholder-copy">Select a crossing to connect it to another.</p> : (
            <>
              <h3>{selected.label}</h3>
              <p className="small-note">{selected.location || "No location description"} · {selected.regions.length} region(s)</p>
              <p className="small-note">
                Connect crossings by dragging directly from a numbered edge label on one crossing
                to a numbered edge label on another. The line is added when released on the destination.
                Keyboard: activate the first edge, then the destination edge.
              </p>
              <p className="small-note">Select each pair of movements that physically intersect between these connected crossings. The virtual coordinator will permit only non-conflicting movements, holding others at red until clearance. Routes are optional; an emergency request also requires defined conflicts. Nothing here controls physical signals.</p>
              <div className="crossing-network-link-list">
                <h4>Connections</h4>
                {draft.links.map((link) => {
                  const from = crosswalks.find((item) => item.id === link.source_crosswalk_id);
                  const to = crosswalks.find((item) => item.id === link.destination_crosswalk_id);
                  return <div className="crossing-network-link-row" key={link.id}>
                    <span>{from?.label ?? "Missing crossing"} [{link.source_edge}] ↔ {to?.label ?? "Missing crossing"} [{link.destination_edge}]</span>
                    <fieldset className="crossing-movement-conflicts">
                      <legend>Conflicting movements</legend>
                      {MOVEMENT_CONFLICTS.map(({ id, label }) => (
                        <label key={id}>
                          <input type="checkbox" checked={(link.movement_conflicts ?? []).includes(id)}
                            disabled={saving}
                            onChange={(event) => changeDraft({
                              ...draft,
                              links: draft.links.map((item) => item.id === link.id ? {
                                ...item,
                                movement_conflicts: event.target.checked
                                  ? [...(item.movement_conflicts ?? []), id]
                                  : (item.movement_conflicts ?? []).filter((value) => value !== id),
                              } : item),
                            })} />
                          {label}
                        </label>
                      ))}
                    </fieldset>
                    <label className="crossing-emergency-route">Emergency vehicle route
                      <select aria-label={"Emergency route for " + link.id}
                        value={link.emergency_route ?? "off"} disabled={saving}
                        onChange={(event) => changeDraft({
                          ...draft,
                          links: draft.links.map((item) => item.id === link.id ? {
                            ...item, emergency_route: event.target.value as NonNullable<typeof link.emergency_route>,
                          } : item),
                        })}>
                        <option value="off">Off</option>
                        <option value="source_to_destination">{from?.label ?? "Source"} → {to?.label ?? "Destination"}</option>
                        <option value="destination_to_source">{to?.label ?? "Destination"} → {from?.label ?? "Source"}</option>
                      </select>
                    </label>
                    <button type="button" className="compact" disabled={saving}
                      onClick={() => changeDraft({ ...draft, links: draft.links.filter((item) => item.id !== link.id) })}>Remove</button>
                  </div>;
                })}
                {draft.links.length === 0 && <p className="small-note">No connections defined. Drag between numbered labels to create one.</p>}
              </div>
            </>
          )}
        </aside>
      </div>
    </section>
  );
}
