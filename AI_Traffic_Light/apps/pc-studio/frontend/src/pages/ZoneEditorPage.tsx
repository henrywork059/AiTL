import { useEffect, useMemo, useState } from "react";
import type { MouseEvent } from "react";
import { API_BASE, fetchActiveZones, resetActiveZones, saveActiveZones } from "../api";
import { FunctionChecklist } from "../components/FunctionChecklist";
import type { CameraStatus, Zone, ZoneStatus, ZoneType } from "../types";
import "./zoneEditor.css";

const ZONE_TYPES: ZoneType[] = ["pedestrian_waiting", "crossing", "vehicle_queue", "counting_region", "counting_line", "ignore"];
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
    setZoneType("counting_region");
    setPoints([]);
    setMessage("Create a polygon by clicking the frame. Counting lines use exactly two points.");
    setError(null);
  }

  function canvasClick(event: MouseEvent<SVGSVGElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = Math.round(((event.clientX - rect.left) / rect.width) * WIDTH);
    const y = Math.round(((event.clientY - rect.top) / rect.height) * HEIGHT);
    const nextPoint: [number, number] = [Math.max(0, Math.min(WIDTH - 1, x)), Math.max(0, Math.min(HEIGHT - 1, y))];
    setPoints((current) => zoneType === "counting_line" && current.length >= 2 ? current : [...current, nextPoint]);
  }

  function applyDraft() {
    const cleanId = zoneId.trim();
    const cleanLabel = label.trim();
    if (!cleanId || !/^[A-Za-z0-9_-]{1,64}$/.test(cleanId)) {
      setError("Zone ID must use 1-64 letters, numbers, underscores, or dashes.");
      return;
    }
    const validGeometry = zoneType === "counting_line" ? points.length === 2 : points.length >= 3;
    if (!cleanLabel || !validGeometry) {
      setError(zoneType === "counting_line"
        ? "Enter a label and define exactly two line points."
        : "Enter a label and define at least three polygon points.");
      return;
    }
    if (zoneType === "counting_line" && points[0][0] === points[1][0] && points[0][1] === points[1][1]) {
      setError("A counting line must use two different points.");
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
    setMessage("Draft applied locally. Save zones to write the complete configuration.");
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
    setMessage("Zone removed from the draft. Save zones to persist the change.");
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
    if (!window.confirm("Replace the current zone configuration with the built-in reference zones?")) return;
    setSaving(true);
    setError(null);
    try {
      const next = await resetActiveZones();
      setStatus(next);
      setZones(next.zones);
      if (next.zones[0]) selectZone(next.zones[0]);
      setMessage("Reference zones restored.");
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
              <h2>Zones & counting geometry</h2>
              <p className="placeholder-copy">Draw geometry against the current frame. Decision zones support signal analysis; counting regions and lines provide analytics.</p>
            </div>
            <span className={`status-pill ${cameraStatus?.frame_available ? "status-implemented" : "status-planned"}`}>
              {cameraStatus?.frame_available ? `${cameraStatus.origin ?? "camera"} · frame ${cameraStatus.frame_number}` : "frame required"}
            </span>
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
                  Start simulation or provide a camera frame before aligning zones.
                </text>
              </>
            )}
            {zones.map((zone) => zone.type === "counting_line" && zone.polygon.length === 2 ? (
              <line
                key={zone.id}
                x1={zone.polygon[0][0]}
                y1={zone.polygon[0][1]}
                x2={zone.polygon[1][0]}
                y2={zone.polygon[1][1]}
                className={`zone-editor-line zone-editor-counting_line ${zone.id === selectedId ? "zone-editor-selected-line" : ""}`}
              />
            ) : (
              <polygon
                key={zone.id}
                points={zone.polygon.map(([x, y]) => `${x},${y}`).join(" ")}
                className={`zone-editor-polygon zone-editor-${zone.type} ${zone.id === selectedId ? "zone-editor-selected" : ""}`}
              />
            ))}
            {points.length >= 2 && <polyline points={points.map(([x, y]) => `${x},${y}`).join(" ")} className="zone-draft-line" />}
            {points.map(([x, y], index) => <circle key={`${x}-${y}-${index}`} cx={x} cy={y} r="9" className="zone-draft-point" />)}
          </svg>
          <p className="small-note">Coordinates are stored in the 1280 × 720 reference frame. Counting regions produce occupancy and entry/exit/dwell events; counting lines produce directional passage events. Analytics geometry does not change the simulated signal policy.</p>
        </section>

        <aside className="side-column">
          <section className="panel compact-panel zone-editor-form">
            <div className="panel-header"><h2>Geometry draft</h2><button type="button" onClick={newZone}>New</button></div>
            <label>Zone ID<input value={zoneId} onChange={(event) => setZoneId(event.target.value)} /></label>
            <label>Display label<input value={label} onChange={(event) => setLabel(event.target.value)} /></label>
            <label>Type
              <select value={zoneType} onChange={(event) => {
                const nextType = event.target.value as ZoneType;
                setZoneType(nextType);
                if (nextType === "counting_line") setPoints((current) => current.slice(0, 2));
              }}>
                {ZONE_TYPES.map((type) => <option key={type} value={type}>{type.split("_").join(" ")}</option>)}
              </select>
            </label>
            <div className="camera-status-list training-status-list">
              <div><span>Draft points</span><strong>{points.length}</strong></div>
              <div><span>Selected</span><strong>{selectedZone?.id ?? "new draft"}</strong></div>
            </div>
            <div className="button-row wrap-row">
              <button type="button" onClick={() => setPoints((current) => current.slice(0, -1))} disabled={points.length === 0}>Undo point</button>
              <button type="button" onClick={() => setPoints([])} disabled={points.length === 0}>Clear points</button>
              <button className="primary" type="button" onClick={applyDraft}>Apply draft</button>
              <button className="danger" type="button" onClick={deleteDraft}>Remove draft</button>
            </div>
          </section>

          <section className="panel compact-panel">
            <div className="panel-header"><h2>Saved configuration</h2><span className="status-pill muted">{zones.length} zones</span></div>
            <div className="zone-selector-list">
              {zones.map((zone) => (
                <button type="button" key={zone.id} className={zone.id === selectedId ? "active" : ""} onClick={() => selectZone(zone)}>
                  <strong>{zone.label}</strong><span>{zone.type.split("_").join(" ")}</span>
                </button>
              ))}
            </div>
            <div className="button-row wrap-row">
              <button className="primary" type="button" onClick={() => void persistZones()} disabled={saving || !status?.editable}>{saving ? "Saving..." : "Save zones"}</button>
              <button type="button" onClick={() => void restoreDefaults()} disabled={saving || !status?.editable}>Restore defaults</button>
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
