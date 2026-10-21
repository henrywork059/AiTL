import { useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import type { CameraStatus } from "../types";
import { liveCameraMjpegUrl, refreshCameraAfterRemoteChange, selectRemoteCamera, type RemoteCameraProfile } from "../lib/remoteCameraApi";
import { SimulationCamera3D } from "../components/SimulationCamera3D";
import type { Crosswalk, CrosswalkRegion } from "../types/crosswalks";
import "./crosswalkRegionEditor.css";

const WIDTH = 1280;
const HEIGHT = 720;
const MAX_REGIONS = 24;
type Side = "camera_side_a_id" | "camera_side_b_id";

function newRegion(regions: CrosswalkRegion[]): CrosswalkRegion {
  const ids = new Set(regions.map((item) => item.id));
  let number = 1;
  while (ids.has("region_" + number)) number++;
  const initialVertices: CrosswalkRegion["vertices"] = [[390, 220], [890, 220], [890, 500], [390, 500]];
  return {
    id: "region_" + number,
    label: "Region " + number,
    vertices: initialVertices,
    vertices_by_side: { a: structuredClone(initialVertices), b: structuredClone(initialVertices) },
  };
}

function verticesForSide(region: CrosswalkRegion, side: "a" | "b"): CrosswalkRegion["vertices"] {
  return region.vertices_by_side?.[side] ?? region.vertices;
}

type Props = {
  crosswalk: Crosswalk;
  cameras: RemoteCameraProfile[];
  cameraStatus: CameraStatus | null;
  showSimulationTools: boolean;
  changingMode: boolean;
  onSimulationChange: (enabled: boolean) => Promise<void>;
  onCameraStatusChange: (status: CameraStatus) => void;
  onRegionsChange: (regions: CrosswalkRegion[]) => void;
  onSave: () => Promise<void>;
  saving: boolean;
  hasUnsavedChanges: boolean;
  onClose: () => void;
};

export function CrosswalkRegionEditor({
  crosswalk, cameras, cameraStatus, showSimulationTools, changingMode,
  onSimulationChange, onCameraStatusChange, onRegionsChange, onSave, saving, hasUnsavedChanges, onClose,
}: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(crosswalk.regions[0]?.id ?? null);
  const [side, setSide] = useState<Side>("camera_side_a_id");
  const [drag, setDrag] = useState<{ id: string; index: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sideKey = side === "camera_side_a_id" ? "a" : "b";
  const visibleRegions = crosswalk.regions.filter((region) => !region.camera_side || region.camera_side === sideKey);
  const selected = visibleRegions.find((region) => region.id === selectedId) ?? null;
  const sourceId = crosswalk[side];
  const selectedCamera = cameras.find((camera) => camera.source_id === sourceId);
  const simulated = Boolean(cameraStatus?.simulation_enabled);
  const previewReady = (showSimulationTools || selectedCamera?.kind !== "simulation") && (simulated
    ? Boolean(cameraStatus?.frame_available && selectedCamera?.kind === "simulation")
    : Boolean(sourceId && selectedCamera?.stream_connected && cameraStatus?.active_source_id === sourceId && !cameraStatus?.stale));
  const previewName = sourceId ?? "No camera assigned";
  const polygon = (region: CrosswalkRegion) => verticesForSide(region, sideKey).map(([x, y]) => x + "," + y).join(" ");
  const previewIs3d = Boolean(simulated && selectedCamera?.kind === "simulation" && showSimulationTools && sourceId);

  function updateRegion(id: string, patch: Partial<CrosswalkRegion>) {
    onRegionsChange(crosswalk.regions.map((region) => region.id === id ? { ...region, ...patch } : region));
  }

  function addRegion() {
    if (crosswalk.regions.length >= MAX_REGIONS) return;
    const region = newRegion(crosswalk.regions);
    onRegionsChange([...crosswalk.regions, region]);
    setSelectedId(region.id);
    setError(null);
  }

  function removeRegion() {
    if (!selected) return;
    const remaining = crosswalk.regions.filter((region) => region.id !== selected.id);
    onRegionsChange(remaining);
    setSelectedId(remaining.find((region) => !region.camera_side || region.camera_side === sideKey)?.id ?? null);
  }

  function onVertexDown(event: ReactPointerEvent<SVGCircleElement>, id: string, index: number) {
    event.preventDefault();
    event.stopPropagation();
    setSelectedId(id);
    setDrag({ id, index });
    event.currentTarget.ownerSVGElement?.setPointerCapture(event.pointerId);
  }

  function moveVertex(event: ReactPointerEvent<SVGSVGElement>) {
    if (!drag) return;
    const box = event.currentTarget.getBoundingClientRect();
    if (!box.width || !box.height) return;
    const x = Math.max(0, Math.min(WIDTH, Math.round((event.clientX - box.left) / box.width * WIDTH)));
    const y = Math.max(0, Math.min(HEIGHT, Math.round((event.clientY - box.top) / box.height * HEIGHT)));
    const region = crosswalk.regions.find((item) => item.id === drag.id);
    if (!region) return;
    const vertices = structuredClone(verticesForSide(region, sideKey));
    vertices[drag.index] = [x, y];
    updateRegion(region.id, { vertices_by_side: { ...region.vertices_by_side, [sideKey]: vertices } });
  }

  function endDrag(event: ReactPointerEvent<SVGSVGElement>) {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    setDrag(null);
  }

  async function previewPhysicalCamera() {
    if (!sourceId || !selectedCamera || simulated) return;
    setBusy(true);
    setError(null);
    try {
      await selectRemoteCamera(sourceId);
      onCameraStatusChange(await refreshCameraAfterRemoteChange());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not select camera.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleSimulation() {
    setBusy(true);
    setError(null);
    try {
      await onSimulationChange(!simulated);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not change simulation mode.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="crosswalk-region-workspace page-stack">
      <div className="panel-header">
        <div>
          <h2>{crosswalk.label} — Region editor</h2>
          <p className="placeholder-copy">Each region identifies one physical area. Define its polygon separately in the Side A and Side B camera views.</p>
        </div>
        <div className="button-row">
          <button className="primary" type="button" onClick={() => void onSave()} disabled={saving || !hasUnsavedChanges}>{saving ? "Saving…" : "Save regions"}</button>
          <button type="button" onClick={onClose}>Back to crosswalks</button>
          {hasUnsavedChanges && <span className="status-pill status-planned">Unsaved changes</span>}
        </div>
      </div>
      <div className="crosswalk-region-layout">
        <aside className="panel compact-panel crosswalk-region-tools">
          <div className="panel-header">
            <h3>Regions</h3>
            <span className="status-pill muted">{crosswalk.regions.length} / {MAX_REGIONS}</span>
          </div>
          <div className="crosswalk-region-list">
            {visibleRegions.map((region) => (
              <button
                type="button" key={region.id}
                className={selected?.id === region.id ? "active" : ""}
                onClick={() => setSelectedId(region.id)}
              >{region.label}</button>
            ))}
            {visibleRegions.length === 0 && <p className="small-note">No regions on this camera side.</p>}
          </div>
          <div className="button-row">
            <button className="primary" type="button" onClick={addRegion} disabled={crosswalk.regions.length >= MAX_REGIONS}>Add region</button>
            <button type="button" onClick={removeRegion} disabled={!selected}>Delete</button>
          </div>
          {selected && (
            <label>
              Region name
              <input
                maxLength={120}
                value={selected.label}
                onChange={(event) => updateRegion(selected.id, { label: event.target.value })}
              />
            </label>
          )}
           <hr />
          <h3>Preview source</h3>
          <span className="status-pill">{simulated ? "Simulation pair" : "Physical cameras"}</span>
          {(
            <>
              <div className="crosswalk-region-side-toggle" role="group" aria-label="Camera side">
                <button type="button" aria-pressed={side === "camera_side_a_id"}
                  onClick={() => setSide("camera_side_a_id")} disabled={busy}>Side A</button>
                <button type="button" aria-pressed={side === "camera_side_b_id"}
                  onClick={() => setSide("camera_side_b_id")} disabled={busy}>Side B</button>
              </div>
              {!simulated && <button type="button" onClick={() => void previewPhysicalCamera()}
                disabled={busy || changingMode || !selectedCamera}>
                Select camera for preview
              </button>}
            </>
          )}
          {showSimulationTools && <button type="button" onClick={() => void toggleSimulation()} disabled={busy || changingMode}>
            {simulated ? "Stop simulation" : "Use simulation camera"}
          </button>}
          {showSimulationTools && <p className="small-note">Simulation cameras use one 3D world. Region vertices are edited in a coordinate-aligned top view for accurate AI counting.</p>}
          {error && <p role="alert" className="error-message">{error}</p>}
        </aside>
        <section className="panel crosswalk-region-canvas-panel">
          <div className="panel-header">
            <strong>{previewName}</strong>
            <span className={previewReady ? "status-pill status-implemented" : "status-pill status-planned"}>
              {previewReady ? "Live preview" : "Preview unavailable"}
            </span>
          </div>
          <div className="crosswalk-region-frame">
            {previewReady
              ? previewIs3d && sourceId
                ? <SimulationCamera3D key={sourceId} sourceId={sourceId} editing />
                : <img key={previewName} src={liveCameraMjpegUrl()} alt={previewName} className="crosswalk-region-camera" />
              : <p className="crosswalk-region-frame-empty">
                  {simulated
                    ? "Waiting for the shared simulation frame."
                    : "Select a saved streaming side camera to align regions. Regions remain editable without a feed."}
                </p>}
            <svg
              viewBox={"0 0 " + WIDTH + " " + HEIGHT}
              className="crosswalk-region-overlay"
              aria-label="Drag the four numbered vertices to reshape the selected quadrilateral region"
              onPointerMove={moveVertex}
              onPointerUp={endDrag}
              onPointerCancel={endDrag}
            >
              {visibleRegions.map((region) => (
                <g key={region.id}>
                  <polygon
                    points={polygon(region)}
                    className={selected?.id === region.id ? "crosswalk-region-polygon is-selected" : "crosswalk-region-polygon"}
                  />
                  {selected?.id === region.id && verticesForSide(region, sideKey).map(([x, y], index) => (
                    <g key={index}>
                      <circle
                        cx={x} cy={y} r="17"
                        className="crosswalk-region-vertex"
                        onPointerDown={(event) => onVertexDown(event, region.id, index)}
                      />
                      <text x={x} y={y + 5} textAnchor="middle" className="crosswalk-region-vertex-label"
                        pointerEvents="none">{index + 1}</text>
                    </g>
                  ))}
                </g>
              ))}
            </svg>
          </div>
          <p className="small-note">Editing coordinates: {WIDTH} × {HEIGHT}. One region name refers to the same physical area in both cameras; each side has its own polygon. Counting remains separate per camera to prevent double-counting. Select Save regions above to persist changes.</p>
        </section>
      </div>
    </div>
  );
}
