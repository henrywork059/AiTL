import { useEffect, useMemo, useState } from "react";
import type { MouseEvent } from "react";
import { API_BASE, fetchActiveZones, resetActiveZones, saveActiveZones } from "../api";
import { FunctionChecklist } from "../components/FunctionChecklist";
import type { CameraStatus, Zone, ZoneStatus, ZoneType } from "../types";
import "./zoneEditor.css";

const ZONE_TYPES: ZoneType[] = ["pedestrian_waiting", "crossing", "vehicle_queue", "ignore"];
const WIDTH = 1280;
const HEIGHT = 720;

type Props = {
  cameraStatus: CameraStatus | null;
};

function clonePoints(points: [number, number][]): [number, number][] {
  return points.map(([x, y]) => [x, y]);
}

export function ZoneEditorPage({ cameraStatus }: Props) {
  const [status, setStatus] = useState<ZoneStatus | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [zoneId, setZoneId] = useState("");
  const [label, setLabel] = useState("");
  const [zoneType, setZoneType] = useState<ZoneType>("crossing");
  const [points, setPoints] = useState<[number, number][]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function loadZones() {
    const next = await fetchActiveZones();
    setStatus(next);
    setZones(next.zones);
    if (next.zones.length > 0) selectZone(next.zones[0]);
  }

  useEffect(() => {
    void loadZones().catch((nextError) => setError(nextError instanceof Error ? nextError.message : "Zones could not be loaded."));
  }, []);

  const selectedZone = useMemo(() => zones.find((zone) => zone.id === selectedId) ?? null, [zones, selectedId]);

  function selectZone(zone: Zone) {
    setSelectedId(zone.id);
    setZoneId(zone.id);
    setLabel(zone.label);
    setZoneType(zone.type);
    setPoints(clonePoints(zone.polygon));
    setMessage(null);
    setError(null);
  }

  function newZone() {
    const candidate = `zone_${zones.length + 1}`;
    setSelectedId(null);
    setZoneId(candidate);
    setLabel("New Zone");
    setZoneType("crossing");
    setPoints([]);
    setMessage("Click the reference canvas to add at least three polygon points.");
    setError(null);
  }

  function canvasClick(event: MouseEvent<SVGSVGElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = Math.round(((event.clientX - rect.left) / rect.width) * WIDTH);
    const y = Math.round(((event.clientY - rect.top) / rect.height) * HEIGHT);
    setPoints((current) => [...current, [Math.max(0, Math.min(WIDTH - 1, x)), Math.max(0, Math.min(HEIGHT - 1, y))]]);
  }

  function applyDraft() {
    const cleanId = zoneId.trim();
    const cleanLabel = label.trim();
    if (!cleanId || !/^[A-Za-z0-9_-]{1,64}$/.test(cleanId)) {
      setError("Zone ID must use 1-64 letters, numbers, underscores, or dashes.");
      return;
    }
    if (!cleanLabel || points.length < 3) {
      setError("Give the zone a label and at least three polygon points.");
      return;
    }
    if (zones.some((zone) => zone.id === cleanId && zone.id !== selectedId)) {
      setError("That zone ID is already in use.");
      return;
    }
    const next: Zone = { id: cleanId, label: cleanLabel, type: zoneType, polygon: clonePoints(points) };
    setZones((current) => selectedId
      ? current.map((zone) => zone.id === selectedId ? next : zone)
      : [...current, next]);
    setSelectedId(cleanId);
    setMessage("Draft applied locally. Use Save zones to persist it.");
    setError(null);
  }

  function deleteDraft() {
    if (!selectedId) {
      newZone();
      return;
    }
    const remaining = zones.filter((zone) => zone.id !== selectedId);
    setZones(remaining);
    if (remaining[0]) selectZone(remaining[0]);
    else newZone();
    setMessage("Zone removed locally. Use Save zones to persist the change.");
  }

  async function persistZones() {
    setSaving(true);
    setError(null);
    try {
      const next = await saveActiveZones(zones);
      setStatus(next);
      setZones(next.zones);
      setMessage(`Saved ${next.zones.length} zones to ${next.config_path}.`);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Zone configuration could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function restoreDefaults() {
    if (!window.confirm("Replace the current zone configuration with the built-in simulation reference zones?")) return;
    setSaving(true);
    setError(null);
    try {
      const next = await resetActiveZones();
      setStatus(next);
      setZones(next.zones);
      if (next.zones[0]) selectZone(next.zones[0]);
      setMessage("Reference zones restored and persisted.");
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Default zones could not be restored.");
    } finally {
      setSaving(false);
    }
  }

  const cameraUrl = cameraStatus?.frame_available
    ? `${API_BASE}/api/camera/frame?t=${cameraStatus.frame_number}`
    : null;


  return (
    <div className="page-stack">
      <div className="zone-editor-layout">
        <section className="panel zone-canvas-panel">
          <div className="panel-header">
            <div>
              <h2>Camera-aligned zone editor</h2>
              <p className="placeholder-copy">Draw zones directly over the current receiver or simulation camera feed.</p>
            </div>
            <span className="status-pill">{cameraStatus?.frame_available ? `${cameraStatus.origin ?? "camera"} frame ${cameraStatus.frame_number}` : "no camera frame"}</span>
          </div>

          <svg className="zone-editor-canvas" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} onClick={canvasClick} role="img" aria-label="Editable traffic zone reference canvas">
            {cameraUrl ? (
              <image
                href={cameraUrl}
                x="0"
                y="0"
                width={WIDTH}
                height={HEIGHT}
                preserveAspectRatio="none"
                className="zone-camera-image"
              />
            ) : (
              <>
                <rect x="0" y="0" width={WIDTH} height={HEIGHT} className="zone-camera-empty" />
                <text x={WIDTH / 2} y={HEIGHT / 2} textAnchor="middle" className="zone-camera-empty-text">
                  Start simulation or provide a camera frame to align zones.
                </text>
              </>
            )}
            {zones.map((zone) => (
              <polygon
                key={zone.id}
                points={zone.polygon.map(([x, y]) => `${x},${y}`).join(" ")}
                className={`zone-editor-polygon zone-editor-${zone.type} ${zone.id === selectedId ? "zone-editor-selected" : ""}`}
              />
            ))}
            {points.length >= 2 && <polyline points={points.map(([x, y]) => `${x},${y}`).join(" ")} className="zone-draft-line" />}
            {points.map(([x, y], index) => <circle key={`${x}-${y}-${index}`} cx={x} cy={y} r="9" className="zone-draft-point" />)}
          </svg>
          <p className="small-note">The camera image is mapped into the 1280 × 720 zone reference coordinates. Saved zones use the same scaling in Traffic Logic and Live AI.</p>
        </section>

        <aside className="side-column">
          <section className="panel compact-panel zone-editor-form">
            <div className="panel-header"><h2>Zone draft</h2><button type="button" onClick={newZone}>New zone</button></div>
            <label>Zone ID<input value={zoneId} onChange={(event) => setZoneId(event.target.value)} /></label>
            <label>Label<input value={label} onChange={(event) => setLabel(event.target.value)} /></label>
            <label>Type
              <select value={zoneType} onChange={(event) => setZoneType(event.target.value as ZoneType)}>
                {ZONE_TYPES.map((type) => <option key={type} value={type}>{type.split("_").join(" ")}</option>)}
              </select>
            </label>
            <div className="camera-status-list training-status-list">
              <div><span>Points</span><strong>{points.length}</strong></div>
              <div><span>Selected</span><strong>{selectedZone?.id ?? "new draft"}</strong></div>
            </div>
            <div className="button-row wrap-row">
              <button type="button" onClick={() => setPoints((current) => current.slice(0, -1))} disabled={points.length === 0}>Undo point</button>
              <button type="button" onClick={() => setPoints([])} disabled={points.length === 0}>Clear</button>
              <button type="button" onClick={applyDraft}>Apply draft</button>
              <button type="button" onClick={deleteDraft}>Delete</button>
            </div>
          </section>

          <section className="panel compact-panel">
            <div className="panel-header"><h2>Configured zones</h2><span>{zones.length}</span></div>
            <div className="zone-selector-list">
              {zones.map((zone) => (
                <button type="button" key={zone.id} className={zone.id === selectedId ? "active" : ""} onClick={() => selectZone(zone)}>
                  <strong>{zone.label}</strong><span>{zone.type.split("_").join(" ")}</span>
                </button>
              ))}
            </div>
            <div className="button-row wrap-row">
              <button type="button" onClick={() => void persistZones()} disabled={saving || !status?.editable}>{saving ? "Saving..." : "Save zones"}</button>
              <button type="button" onClick={() => void restoreDefaults()} disabled={saving || !status?.editable}>Reset defaults</button>
            </div>
            {message && <p className="success-message">{message}</p>}
            {error && <p className="error-message">{error}</p>}
          </section>
        </aside>
      </div>
      <FunctionChecklist area="Zones" />
    </div>
  );
}
