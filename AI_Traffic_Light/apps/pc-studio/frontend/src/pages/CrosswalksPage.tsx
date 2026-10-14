import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchCrosswalks, saveCrosswalks } from "../lib/crosswalksApi";
import { fetchRemoteCameraStatus, refreshCameraAfterRemoteChange, saveSimulationCamera, liveCameraMjpegUrl, type RemoteCameraProfile } from "../lib/remoteCameraApi";
import { CrosswalkRegionEditor } from "./CrosswalkRegionEditor";
import type { CameraStatus } from "../types";
import { useSerialPolling } from "../lib/useSerialPolling";
import type { Crosswalk, CrosswalkConfig, CrosswalkRegion } from "../types/crosswalks";
import "./crosswalksPage.css";

const LIMIT = 32;

function nextId(items: Crosswalk[]): string {
  const ids = new Set(items.map((item) => item.id));
  let number = 1;
  while (ids.has("crosswalk_" + number)) number++;
  return "crosswalk_" + number;
}

function cameraState(camera: RemoteCameraProfile | undefined): string {
  if (!camera) return "Missing saved camera";
  if (camera.kind === "simulation") return camera.streaming ? "Simulation running" : "Simulation stopped";
  if (camera.paused_for_simulation) return "Paused";
  if (camera.stream_connected) return "Streaming";
  if (camera.streaming) return "Reconnecting";
  if (camera.connected && camera.device_reachable) return "Connected";
  return camera.last_error ? "Error" : "Not connected";
}

type Props = {
  cameraStatus: CameraStatus | null;
  changingMode: boolean;
  onSimulationChange: (enabled: boolean) => Promise<void>;
  onCameraStatusChange: (status: CameraStatus) => void;
};

export function CrosswalksPage({ cameraStatus, changingMode, onSimulationChange, onCameraStatusChange }: Props) {
  const [saved, setSaved] = useState<CrosswalkConfig | null>(null);
  const [draft, setDraft] = useState<CrosswalkConfig | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [cameras, setCameras] = useState<RemoteCameraProfile[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [regionEditorOpen, setRegionEditorOpen] = useState(false);

  const load = useCallback(async () => {
    const next = await fetchCrosswalks();
    setSaved(next);
    setDraft(structuredClone(next));
    setSelectedId((old) => next.crosswalks.some((item) => item.id === old) ? old : next.crosswalks[0]?.id ?? null);
  }, []);

  useEffect(() => {
    void load().catch((err) => setError(err instanceof Error ? err.message : "Crosswalk loading failed."));
  }, [load]);

  const pollCameras = useCallback(async () => {
    setCameras((await fetchRemoteCameraStatus()).cameras);
  }, []);
  useSerialPolling(pollCameras, 2000, { onError: () => undefined });

  const selected = useMemo(
    () => draft?.crosswalks.find((item) => item.id === selectedId) ?? null,
    [draft, selectedId],
  );
  const cameraById = useMemo(() => new Map(cameras.map((camera) => [camera.source_id, camera])), [cameras]);
  const dirty = Boolean(saved && draft && JSON.stringify(saved) !== JSON.stringify(draft));

  function update(changes: Partial<Crosswalk>) {
    if (!draft || !selected) return;
    setDraft({
      ...draft,
      crosswalks: draft.crosswalks.map((item) => item.id === selected.id ? { ...item, ...changes } : item),
    });
    setNotice(null);
  }

  function add() {
    if (!draft || draft.crosswalks.length >= LIMIT) return;
    const id = nextId(draft.crosswalks);
    const next: Crosswalk = { id, label: "New crosswalk", location: "", camera_side_a_id: null, camera_side_b_id: null, regions: [] };
    setDraft({ ...draft, crosswalks: [...draft.crosswalks, next] });
    setSelectedId(id);
    setError(null);
    setNotice(null);
  }

  function remove() {
    if (!selected || !draft || !window.confirm("Remove this crosswalk? Save to confirm deletion.")) return;
    const others = draft.crosswalks.filter((item) => item.id !== selected.id);
    setDraft({ ...draft, crosswalks: others });
    setSelectedId(others[0]?.id ?? null);
    setNotice(null);
  }

  async function save() {
    if (!draft) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const next = await saveCrosswalks(draft);
      setSaved(next);
      setDraft(structuredClone(next));
      setNotice("Crosswalks saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save crosswalks.");
    } finally {
      setBusy(false);
    }
  }

  async function assignSimulationPair() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      const cameraRegistry = await saveSimulationCamera();
      setCameras(cameraRegistry.cameras);
      onCameraStatusChange(await refreshCameraAfterRemoteChange());
      update({ camera_side_a_id: "simulation_camera", camera_side_b_id: "simulation_camera_b" });
      setNotice("Simulation pair assigned. Save changes to keep the assignment.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add simulation camera pair.");
    } finally {
      setBusy(false);
    }
  }

  async function reload() {
    if (dirty && !window.confirm("Discard unsaved edits?")) return;
    setBusy(true);
    setError(null);
    try {
      await load();
      setNotice("Saved crosswalks reloaded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reload crosswalks.");
    } finally {
      setBusy(false);
    }
  }

  function cameraPicker(field: "camera_side_a_id" | "camera_side_b_id", label: string) {
    if (!selected) return null;
    const current = selected[field];
    const other = selected[field === "camera_side_a_id" ? "camera_side_b_id" : "camera_side_a_id"];
    return (
      <label className="crosswalk-camera-select">
        {label}
        <select
          value={current ?? ""}
          disabled={busy}
          onChange={(event) => update(field === "camera_side_a_id"
            ? { camera_side_a_id: event.target.value || null }
            : { camera_side_b_id: event.target.value || null })}
        >
          <option value="">No camera assigned</option>
          {current && !cameraById.has(current) && <option value={current}>{current} (missing camera)</option>}
          {cameras.filter((camera) => camera.source_id !== other).map((camera) => (
            <option key={camera.source_id} value={camera.source_id}>{camera.source_id} — {camera.kind === "simulation" ? "PC simulation" : camera.host}</option>
          ))}
        </select>
      </label>
    );
  }

  if (regionEditorOpen && selected) {
    return (
      <CrosswalkRegionEditor
        crosswalk={selected}
        cameras={cameras}
        cameraStatus={cameraStatus}
        changingMode={changingMode}
        onSimulationChange={onSimulationChange}
        onCameraStatusChange={onCameraStatusChange}
        onRegionsChange={(regions: CrosswalkRegion[]) => update({ regions })}
        onClose={() => setRegionEditorOpen(false)}
      />
    );
  }

  const sideA = selected?.camera_side_a_id ? cameraById.get(selected.camera_side_a_id) : undefined;
  const sideB = selected?.camera_side_b_id ? cameraById.get(selected.camera_side_b_id) : undefined;

  return (
    <div className="page-stack">
      <div className="crosswalk-layout">
        <section className="panel">
          <div className="panel-header">
            <h2>Defined crosswalks</h2>
            <span className="status-pill muted">{draft?.crosswalks.length ?? 0} / {LIMIT}</span>
          </div>
          <div className="crosswalk-list" aria-label="Defined crosswalks">
            {draft?.crosswalks.map((item) => (
              <button
                type="button"
                key={item.id}
                className={item.id === selectedId ? "crosswalk-list-item active" : "crosswalk-list-item"}
                onClick={() => setSelectedId(item.id)}
              >
                <strong>{item.label || item.id}</strong>
                <small>{item.location || item.id}</small>
                <small>{[item.camera_side_a_id, item.camera_side_b_id].filter(Boolean).length} / 2 cameras</small>
              </button>
            ))}
            {!draft && <p className="small-note">Loading crosswalks…</p>}
            {draft?.crosswalks.length === 0 && <p className="small-note">No crosswalks yet.</p>}
          </div>
          <div className="button-row">
            <button type="button" onClick={add} disabled={busy || !draft || draft.crosswalks.length >= LIMIT}>Add crosswalk</button>
            <button type="button" onClick={remove} disabled={busy || !selected}>Remove</button>
          </div>
          {selected && (
            <div className="crosswalk-editor training-form">
              <h3>Edit crosswalk</h3>
              <div className="form-grid">
                <label>Crosswalk name
                  <input value={selected.label} maxLength={120} disabled={busy}
                    onChange={(event) => update({ label: event.target.value })} />
                </label>
                <label>Location / description
                  <input value={selected.location} maxLength={160} disabled={busy} placeholder="e.g. South gate"
                    onChange={(event) => update({ location: event.target.value })} />
                </label>
              </div>
              <p className="small-note">ID: {selected.id}</p>
              <div className="button-row">
                <button type="button" onClick={() => setRegionEditorOpen(true)}>
                  Edit regions ({selected.regions.length})
                </button>
              </div>
            </div>
          )}
          <div className="button-row">
            <button className="primary" type="button" onClick={() => void save()} disabled={busy || !dirty}>
              {busy ? "Working…" : "Save changes"}
            </button>
            <button type="button" onClick={() => void reload()} disabled={busy || !draft}>Reload saved</button>
            {dirty && <span className="status-pill status-planned">Unsaved changes</span>}
          </div>
          {notice && <p className="success-message" role="status">{notice}</p>}
          {error && <p className="error-message" role="alert">{error}</p>}
        </section>

        <section className="panel">
          <div className="panel-header">
            <h2>Crosswalk layout</h2>
            <span className="status-pill muted">Schematic only</span>
          </div>
          <div className="button-row">
            <span className={cameraStatus?.simulation_enabled ? "status-pill status-implemented" : "status-pill muted"}>
              {cameraStatus?.simulation_enabled ? "Simulation active" : "Physical cameras"}
            </span>
            <button type="button" disabled={changingMode || !cameraStatus}
              onClick={() => void onSimulationChange(!cameraStatus?.simulation_enabled)}>
              {cameraStatus?.simulation_enabled ? "Stop simulation" : "Start simulation"}
            </button>
            <button type="button" disabled={busy || !selected} onClick={() => void assignSimulationPair()}>Assign simulation pair</button>
          </div>
          {selected ? (
            <>
              {cameraPicker("camera_side_a_id", "Side A — first pedestrian approach")}
              <svg className="crosswalk-figure" viewBox="0 0 640 380" role="img"
                aria-label="Vertical pedestrian crossing from Side A to Side B, with horizontal white zebra stripes across the road and one camera at each end">
                <rect width="640" height="380" fill="#d1d8d0" rx="12" />
                <rect y="125" width="640" height="130" fill="#39434a" />
                <path d="M0 190 H640" stroke="#f0cd73" strokeWidth="3" strokeDasharray="24 20" />
                <path d="M240 75 V305 M400 75 V305" stroke="#315f9e" strokeWidth="3" strokeDasharray="10 8" opacity="0.6" fill="none" />
                {Array.from({ length: 7 }, (_, index) => (
                  <rect key={index} x="250" y={138 + index * 17} width="140" height="10" rx="2" fill="#f7f8f5" />
                ))}
                <path d="M320 89 V120 M307 109 L320 122 L333 109" fill="none" stroke="#315f9e" strokeWidth="5" strokeLinecap="round" />
                <path d="M320 291 V260 M307 272 L320 259 L333 272" fill="none" stroke="#315f9e" strokeWidth="5" strokeLinecap="round" />
                <rect x="280" y="25" width="80" height="48" rx="9" fill={selected.camera_side_a_id ? "#315f9e" : "#6d747d"} />
                <circle cx="302" cy="49" r="10" fill="#dbeafe" />
                <text x="332" y="55" fontSize="17" fill="white">A</text>
                <rect x="280" y="307" width="80" height="48" rx="9" fill={selected.camera_side_b_id ? "#315f9e" : "#6d747d"} />
                <circle cx="302" cy="331" r="10" fill="#dbeafe" />
                <text x="332" y="337" fontSize="17" fill="white">B</text>
                <text x="18" y="102" fontSize="16" fill="#26352c">Pedestrian side A</text>
                <text x="18" y="285" fontSize="16" fill="#26352c">Pedestrian side B</text>
                <text x="18" y="210" fontSize="16" fill="white">Road</text>
                {([["1", 422, 18], ["2", 616, 182], ["3", 422, 362], ["4", 24, 182]] as const).map(([edge, x, y]) => (
                  <g key={edge} className="crosswalk-edge-marker" aria-label={`Crosswalk edge ${edge}`}>
                    <rect x={x - 17} y={y - 15} width="34" height="30" rx="5" />
                    <text x={x} y={y + 5} textAnchor="middle">{edge}</text>
                  </g>
                ))}
              </svg>
              <div className="crosswalk-camera-details">
                <div><strong>Side A</strong><span>{selected.camera_side_a_id || "Unassigned"} — {selected.camera_side_a_id ? cameraState(sideA) : "No camera"}</span></div>
                <div><strong>Side B</strong><span>{selected.camera_side_b_id || "Unassigned"} — {selected.camera_side_b_id ? cameraState(sideB) : "No camera"}</span></div>
              </div>
              {cameraPicker("camera_side_b_id", "Side B — opposite pedestrian approach")}
              {((selected.camera_side_a_id && !sideA) || (selected.camera_side_b_id && !sideB)) && (
                <p className="error-message">An assigned camera is missing from Camera Settings. Reassign or clear it.</p>
              )}
              {cameraStatus?.simulation_enabled && sideA?.kind === "simulation" && sideB?.kind === "simulation" && (
                <div className="crosswalk-simulation-previews">
                  <div><strong>Side A</strong><img src={`${liveCameraMjpegUrl()}?source_id=simulation_camera`} alt="Simulated camera A" /></div>
                  <div><strong>Side B · vertically mirrored</strong><img src={`${liveCameraMjpegUrl()}?source_id=simulation_camera_b`} alt="Mirrored camera B" /></div>
                </div>
              )}
              <p className="small-note">Both cameras can be assigned. Simultaneous two-camera inference and physical signal control are not enabled.</p>
            </>
          ) : <p className="crosswalk-empty">Select or add a crosswalk to see its two camera positions.</p>}
        </section>
      </div>
    </div>
  );
}
