import { useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import type { CameraStatus } from "../types";
import { liveCameraMjpegUrl, refreshCameraAfterRemoteChange, selectRemoteCamera, type RemoteCameraProfile } from "../lib/remoteCameraApi";
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
  return {
    id: "region_" + number,
    label: "New region " + number,
    vertices: [[390, 220], [890, 220], [890, 500], [390, 500]],
  };
}

type Props = {
  crosswalk: Crosswalk;
  cameras: RemoteCameraProfile[];
  cameraStatus: CameraStatus | null;
  changingMode: boolean;
  onSimulationChange: (enabled: boolean) => Promise<void>;
  onCameraStatusChange: (status: CameraStatus) => void;
  onRegionsChange: (regions: CrosswalkRegion[]) => void;
  onClose: () => void;
};

export function CrosswalkRegionEditor({
  crosswalk, cameras, cameraStatus, changingMode,
  onSimulationChange, onCameraStatusChange, onRegionsChange, onClose,
}: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(crosswalk.regions[0]?.id ?? null);
  const [side, setSide] = useState<Side>("camera_side_a_id");
  const [drag, setDrag] = useState<{ id: string; index: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = crosswalk.regions.find((region) => region.id === selectedId) ?? null;
  const sourceId = crosswalk[side];
  const selectedCamera = cameras.find((camera) => camera.source_id === sourceId);
  const simulated = Boolean(cameraStatus?.simulation_enabled);
  const previewReady = simulated
    ? Boolean(cameraStatus?.frame_available)
    : Boolean(sourceId && selectedCamera?.stream_connected && cameraStatus?.active_source_id === sourceId && !cameraStatus?.stale);
  const previewName = simulated ? "One shared simulated camera" : sourceId ?? "No camera assigned";
  const polygon = (region: CrosswalkRegion) => region.vertices.map(([x, y]) => x + "," + y).join(" ");

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
    setSelectedId(remaining[0]?.id ?? null);
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
    const vertices = structuredClone(region.vertices);
    vertices[drag.index] = [x, y];
    updateRegion(region.id, { vertices });
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
          <p className="placeholder-copy">Four draggable vertices per region. The geometry belongs to this crosswalk and is shared by both camera slots.</p>
        </div>
        <button type="button" onClick={onClose}>Back to crosswalks</button>
      </div>
      <div className="crosswalk-region-layout">
        <aside className="panel compact-panel crosswalk-region-tools">
          <div className="panel-header">
            <h3>Regions</h3>
            <span className="status-pill muted">{crosswalk.regions.length} / {MAX_REGIONS}</span>
          </div>
          <div className="crosswalk-region-list">
            {crosswalk.regions.map((region) => (
              <button
                type="button" key={region.id}
                className={selected?.id === region.id ? "active" : ""}
                onClick={() => setSelectedId(region.id)}
              >{region.label}</button>
            ))}
            {crosswalk.regions.length === 0 && <p className="small-note">No regions yet.</p>}
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
          <span className="status-pill">{simulated ? "Simulation • one camera" : "Physical camera"}</span>
          {!simulated && (
            <>
              <label>Camera side
                <select value={side} onChange={(event) => setSide(event.target.value as Side)}>
                  <option value="camera_side_a_id">Side A</option>
                  <option value="camera_side_b_id">Side B</option>
                </select>
              </label>
              <button type="button" onClick={() => void previewPhysicalCamera()}
                disabled={busy || changingMode || !selectedCamera}>
                Select camera for preview
              </button>
            </>
          )}
          <button type="button" onClick={() => void toggleSimulation()} disabled={busy || changingMode}>
            {simulated ? "Stop simulation" : "Use simulation camera"}
          </button>
          <p className="small-note">Simulation uses the application's single shared camera and pauses physical input. No second simulated camera is created.</p>
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
              ? <img key={previewName} src={liveCameraMjpegUrl()} alt={previewName} className="crosswalk-region-camera" />
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
              {crosswalk.regions.map((region) => (
                <g key={region.id}>
                  <polygon
                    points={polygon(region)}
                    className={selected?.id === region.id ? "crosswalk-region-polygon is-selected" : "crosswalk-region-polygon"}
                  />
                  {selected?.id === region.id && region.vertices.map(([x, y], index) => (
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
          <p className="small-note">Editing coordinates: {WIDTH} × {HEIGHT}. Same coordinates are overlaid for Side A and Side B; viewpoints are not automatically calibrated. Return to Crosswalks and select Save changes to persist.</p>
        </section>
      </div>
    </div>
  );
}
