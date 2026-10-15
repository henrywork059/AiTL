import { useEffect, useMemo, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import { fetchCrosswalks, saveCrosswalks } from "../lib/crosswalksApi";
import type {
  CrosswalkConfig, CrosswalkNetwork, CrosswalkNetworkEdge, CrosswalkNetworkPosition,
} from "../types/crosswalks";
import type { JunctionCameraView, JunctionNetworkOverview } from "../types/junctionNetwork";
import "./crosswalkNetworkPanel.css";

type Props = {
  config: CrosswalkConfig;
  overview: JunctionNetworkOverview | null;
  onSaved: (config: CrosswalkConfig) => void;
  onRefresh: () => Promise<void>;
};

const EDGES: CrosswalkNetworkEdge[] = ["1", "2", "3", "4"];
const EMPTY_NETWORK: CrosswalkNetwork = { positions: {}, links: [] };
const MAX_LINKS = 64;

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
  const [sourceEdge, setSourceEdge] = useState<CrosswalkNetworkEdge>("2");
  const [targetId, setTargetId] = useState("");
  const [targetEdge, setTargetEdge] = useState<CrosswalkNetworkEdge>("4");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ id: string; pointerId: number; offsetX: number; offsetY: number } | null>(null);

  const dirty = JSON.stringify(draft) !== savedKey;
  const crosswalks = config.crosswalks;
  const selected = crosswalks.find((item) => item.id === selectedId) ?? crosswalks[0] ?? null;
  const targets = crosswalks.filter((item) => item.id !== selected?.id);
  const destination = targets.some((item) => item.id === targetId) ? targetId : targets[0]?.id ?? "";
  const canvasHeight = Math.max(480, Math.ceil(crosswalks.length / 3) * 250);

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

  function connect() {
    if (!selected || !destination || draft.links.length >= MAX_LINKS) return;
    const duplicate = draft.links.some((link) =>
      (link.source_crosswalk_id === selected.id && link.destination_crosswalk_id === destination
        && link.source_edge === sourceEdge && link.destination_edge === targetEdge)
      || (link.source_crosswalk_id === destination && link.destination_crosswalk_id === selected.id
        && link.source_edge === targetEdge && link.destination_edge === sourceEdge));
    if (duplicate) {
      setError("These numbered edges are already connected.");
      return;
    }
    changeDraft({
      ...draft, links: [...draft.links, {
        id: nextLinkId(draft.links.map((link) => link.id)),
        source_crosswalk_id: selected.id, destination_crosswalk_id: destination,
        source_edge: sourceEdge, destination_edge: targetEdge,
      }],
    });
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
            <p className="placeholder-copy">All saved crossings appear automatically. Move their boxes and connect numbered edges.</p>
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
        <p className="small-note">Only the selected camera can provide current AI counts. Other crossings show camera health and configuration, not invented observations. Connections do not control traffic lights.</p>
        {dirty && <p className="small-note" role="status">Unsaved Network changes</p>}
        {notice && <p className="success-message" role="status">{notice}</p>}
        {error && <p className="error-message" role="alert">{error}</p>}
      </div>

      <div className="crossing-network-layout">
        <div className="panel crossing-network-map">
          <div className="panel-header"><h3>Crossing map</h3><span className="small-note">Drag crossing titles to rearrange</span></div>
          <div className="crossing-network-scroll">
            <div ref={canvasRef} className="crossing-network-canvas" style={{ height: canvasHeight }}
              onPointerMove={moveDrag} onPointerUp={endDrag} onPointerCancel={endDrag}>
              <svg className="crossing-network-links" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                {draft.links.map((link) => {
                  const a = positions.get(link.source_crosswalk_id);
                  const b = positions.get(link.destination_crosswalk_id);
                  if (!a || !b) return null;
                  return <line key={link.id} x1={a.x} y1={a.y} x2={b.x} y2={b.y} />;
                })}
              </svg>
              {crosswalks.map((crosswalk) => {
                const position = positions.get(crosswalk.id);
                const observed = countsByCrosswalk.get(crosswalk.id) ?? [];
                const active = overview?.current_frame_source_id;
                const liveHere = Boolean(overview && overview.observation_provenance !== "unavailable" && active
                  && (active === crosswalk.camera_side_a_id || active === crosswalk.camera_side_b_id));
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
                        className={"crossing-network-edge crossing-network-edge-" + edge}
                        aria-label={crosswalk.label + " edge " + edge}
                        aria-pressed={selected?.id === crosswalk.id && sourceEdge === edge}
                        onClick={() => { setSelectedId(crosswalk.id); setSourceEdge(edge); }}>{edge}</button>)}
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
              <div className="crossing-network-link-form">
                <h4>Connect crossings</h4>
                <label>From edge
                  <select value={sourceEdge} disabled={saving} onChange={(event) => setSourceEdge(event.target.value as CrosswalkNetworkEdge)}>
                    {EDGES.map((edge) => <option key={edge} value={edge}>{edge}</option>)}
                  </select>
                </label>
                <label>Destination crossing
                  <select value={destination} disabled={saving || targets.length === 0} onChange={(event) => setTargetId(event.target.value)}>
                    {targets.length === 0 && <option value="">Add another crossing first</option>}
                    {targets.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
                  </select>
                </label>
                <label>Destination edge
                  <select value={targetEdge} disabled={saving || !destination} onChange={(event) => setTargetEdge(event.target.value as CrosswalkNetworkEdge)}>
                    {EDGES.map((edge) => <option key={edge} value={edge}>{edge}</option>)}
                  </select>
                </label>
                <button className="primary" type="button" disabled={saving || !destination || draft.links.length >= MAX_LINKS} onClick={connect}>Connect crossings</button>
                <p className="small-note">Edge numbers are connection points, not compass directions. Connections are topology only.</p>
              </div>
              <div className="crossing-network-link-list">
                <h4>Connections</h4>
                {draft.links.map((link) => {
                  const from = crosswalks.find((item) => item.id === link.source_crosswalk_id);
                  const to = crosswalks.find((item) => item.id === link.destination_crosswalk_id);
                  return <div className="crossing-network-link-row" key={link.id}>
                    <span>{from?.label ?? "Missing crossing"} [{link.source_edge}] ↔ {to?.label ?? "Missing crossing"} [{link.destination_edge}]</span>
                    <button type="button" className="compact" disabled={saving}
                      onClick={() => changeDraft({ ...draft, links: draft.links.filter((item) => item.id !== link.id) })}>Remove</button>
                  </div>;
                })}
                {draft.links.length === 0 && <p className="small-note">No connections defined.</p>}
              </div>
            </>
          )}
        </aside>
      </div>
    </section>
  );
}
