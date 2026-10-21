import { useRef, useState, type PointerEvent, type WheelEvent } from "react";
import type { Detection, Zone } from "../types";
import { fetchSimulationScene, type SimulationScene } from "../lib/remoteCameraApi";
import { useSerialPolling } from "../lib/useSerialPolling";
import "./simulationCamera3D.css";

type Props = {
  sourceId: string;
  editing?: boolean;
  detections?: Detection[];
  zones?: Zone[];
  showBoxes?: boolean;
  showLabels?: boolean;
  showRegions?: boolean;
  frameWidth?: number;
  frameHeight?: number;
};

const CAMERA_LABEL: Record<string, string> = {
  simulation_camera: "Camera A",
  simulation_camera_b: "Camera B",
  simulation_camera_c: "Camera C",
  simulation_camera_d: "Camera D",
};

const INITIAL_ORBIT: Record<string, number> = {
  simulation_camera: -25,
  simulation_camera_b: 155,
  simulation_camera_c: 25,
  simulation_camera_d: -155,
};
const clamp = (value: number, low: number, high: number) => Math.min(high, Math.max(low, value));

/** Source images B/C/D are mirror transforms of the canonical A coordinates. */
function sourcePoint(x: number, y: number, sourceId: string, width: number, height: number) {
  return {
    x: sourceId === "simulation_camera_c" || sourceId === "simulation_camera_d" ? width - x : x,
    y: sourceId === "simulation_camera_b" || sourceId === "simulation_camera_d" ? height - y : y,
  };
}

/** Read-only perspective of the actual live camera simulator; never controls its agents. */
export function SimulationCamera3D({
  sourceId, editing = false, detections = [], zones = [],
  showBoxes = true, showLabels = true, showRegions = true,
  frameWidth = 1280, frameHeight = 720,
}: Props) {
  const initialOrbit = INITIAL_ORBIT[sourceId] ?? -25;
  const [scene, setScene] = useState<SimulationScene | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [orbit, setOrbit] = useState(initialOrbit);
  const [pitch, setPitch] = useState(48);
  const [zoom, setZoom] = useState(0.85);
  const drag = useRef<{ x: number; y: number; orbit: number; pitch: number } | null>(null);

  useSerialPolling(async () => {
    const next = await fetchSimulationScene(sourceId);
    setScene(next);
    setError(null);
  }, 450, {
    restartKey: sourceId,
    onError: (reason) => {
      setScene(null);
      setError(reason instanceof Error ? reason.message : "3D simulation preview unavailable.");
    },
  });

  function beginDrag(event: PointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return;
    drag.current = { x: event.clientX, y: event.clientY, orbit, pitch };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function moveDrag(event: PointerEvent<HTMLDivElement>) {
    if (!drag.current) return;
    setOrbit(drag.current.orbit + (event.clientX - drag.current.x) * 0.45);
    setPitch(clamp(drag.current.pitch - (event.clientY - drag.current.y) * 0.4, 0, 75));
  }

  function endDrag(event: PointerEvent<HTMLDivElement>) {
    drag.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function changeZoom(event: WheelEvent<HTMLDivElement>) {
    event.preventDefault();
    setZoom(current => clamp(current - Math.sign(event.deltaY) * 0.08, 0.5, 1.35));
  }

  const sizeX = scene?.width ?? 1280;
  const sizeY = scene?.height ?? 720;
  const phase = scene?.signal.phase ?? "waiting";
  const vehicleLight = scene?.signal.vehicle_go ? "green" : phase === "vehicle_yellow" ? "amber" : "red";
  const pedestrianLight = scene?.signal.pedestrian_walk ? "green" : "red";
  const isFlippedX = sourceId === "simulation_camera_c" || sourceId === "simulation_camera_d";
  const hasOverlay = !editing && ((showRegions && zones.length > 0) || (showBoxes && detections.length > 0));
  const normalizedFrameWidth = frameWidth > 0 ? frameWidth : sizeX;
  const normalizedFrameHeight = frameHeight > 0 ? frameHeight : sizeY;

  return (
    <section className={`sim3d-preview${editing ? " is-editor" : ""}`} aria-label={`Interactive 3D preview of ${sourceId}`}>
      <div className="sim3d-viewport" onPointerDown={editing ? undefined : beginDrag} onPointerMove={editing ? undefined : moveDrag}
        onPointerUp={editing ? undefined : endDrag} onPointerCancel={editing ? undefined : endDrag} onWheel={editing ? undefined : changeZoom}>
        <div className="sim3d-world" aria-hidden="true" style={{
          transform: editing
            ? "translate(-50%, -50%) scale(1) rotateX(0deg) rotateZ(0deg)"
            : `translate(-50%, -50%) scale(${zoom}) rotateX(${pitch}deg) rotateZ(${orbit}deg)`,
        }}>
          <div className="sim3d-ground" />
          <div className="sim3d-road" />
          <div className="sim3d-lane sim3d-lane-upper" />
          <div className="sim3d-lane sim3d-lane-lower" />
          <div className="sim3d-crossing" />
          {Array.from({ length: 9 }, (_, i) => (
            <div className="sim3d-stripe" key={i} style={{ top: `${(205 + i * 46) / 720 * 100}%` }} />
          ))}
          <div className="sim3d-stop sim3d-stop-left" />
          <div className="sim3d-stop sim3d-stop-right" />
          <div className="sim3d-pole sim3d-vehicle-pole"><span className={vehicleLight} /></div>
          <div className="sim3d-pole sim3d-person-pole"><span className={pedestrianLight} /></div>
          {scene?.vehicles.map(vehicle => {
            const leftEdge = sourcePoint(vehicle.x, vehicle.y, sourceId, sizeX, sizeY);
            const centerX = isFlippedX ? leftEdge.x - vehicle.width / 2 : leftEdge.x + vehicle.width / 2;
            return <div className="sim3d-car" key={vehicle.id} title={`${vehicle.vehicle_type} · ${vehicle.direction > 0 ? "eastbound" : "westbound"}`}
              style={{
                left: `${centerX / sizeX * 100}%`,
                top: `${leftEdge.y / sizeY * 100}%`,
                width: `${vehicle.width / sizeX * 100}%`,
                backgroundColor: vehicle.color,
                transform: `translate(-50%, -50%) translateZ(15px) rotateZ(${(isFlippedX ? -vehicle.direction : vehicle.direction) < 0 ? 180 : 0}deg)`,
              }}>
              <div className="sim3d-car-roof" />
              <div className="sim3d-car-side" />
            </div>;
          })}
          {scene?.pedestrians.map(pedestrian => {
            const point = sourcePoint(pedestrian.x, pedestrian.y, sourceId, sizeX, sizeY);
            return <div className="sim3d-person" key={pedestrian.id} title="Simulated pedestrian" style={{
              left: `${point.x / sizeX * 100}%`,
              top: `${point.y / sizeY * 100}%`,
              backgroundColor: pedestrian.color,
            }}>
              <span />
            </div>;
          })}
          {hasOverlay && (
            <svg className="sim3d-world-overlay" viewBox={`0 0 ${sizeX} ${sizeY}`}
              preserveAspectRatio="none" aria-hidden="true">
              {showRegions && zones.map(zone => {
                const points = zone.polygon.map(([x, y]) => `${x / 1280 * sizeX},${y / 720 * sizeY}`).join(" ");
                return <g key={zone.id} className="sim3d-region">
                  {zone.type === "counting_line"
                    ? <polyline points={points} fill="none" strokeDasharray="12 8" />
                    : <polygon points={points} />}
                  {showLabels && zone.polygon[0] && <text
                    x={zone.polygon[0][0] / 1280 * sizeX + 8}
                    y={zone.polygon[0][1] / 720 * sizeY + 18}>{zone.label}</text>}
                </g>;
              })}
              {showBoxes && detections.map(detection => {
                const [x1, y1, x2, y2] = detection.box_xyxy;
                const x = x1 / normalizedFrameWidth * sizeX;
                const y = y1 / normalizedFrameHeight * sizeY;
                const w = (x2 - x1) / normalizedFrameWidth * sizeX;
                const h = (y2 - y1) / normalizedFrameHeight * sizeY;
                return <g key={detection.id} className="sim3d-detection">
                  <rect x={x} y={y} width={w} height={h} />
                  {showLabels && <text x={x + 6} y={Math.max(18, y - 8)}>
                    {`${detection.class_name} ${Math.round(detection.confidence * 100)}%`}
                  </text>}
                </g>;
              })}
            </svg>
          )}
        </div>
      </div>
      <div className="sim3d-head">
        <span className="sim3d-flag">3D CAMERA</span>
        <span>{CAMERA_LABEL[sourceId] ?? sourceId}</span>
        {scene?.paused && <span className="sim3d-paused">Paused</span>}
      </div>
      {!editing && <div className="sim3d-actions">
        <button type="button" onClick={() => { setOrbit(initialOrbit); setPitch(48); setZoom(0.85); }}>Reset</button>
        <button type="button" onClick={() => setPitch(current => current === 0 ? 48 : 0)}>
          {pitch === 0 ? "Perspective" : "Top"}
        </button>
        <label>Zoom <input aria-label="3D camera zoom" type="range" min="0.5" max="1.35" step="0.05"
          value={zoom} onChange={event => setZoom(Number(event.target.value))} /></label>
      </div>}
      <div className="sim3d-status" aria-live="off">
        {scene ? <>
          <span>Vehicle <b className={vehicleLight}>{vehicleLight}</b></span>
          <span>Pedestrian <b className={pedestrianLight}>{pedestrianLight === "green" ? "walk" : "stop"}</b></span>
          <span>{phase.replaceAll("_", " ")} · {Math.max(0, Math.ceil(scene.signal.seconds_remaining))} s</span>
          <span>{scene.vehicles.length} cars · {scene.pedestrians.length} people</span>
        </> : <span>{error ?? "Loading 3D simulation scene..."}</span>}
      </div>
      {!editing && <span className="sim3d-hint">Drag to orbit · Scroll to zoom · synthetic scene</span>}
      {editing && <span className="sim3d-hint">Aligned 3D top view · drag region vertices</span>}
    </section>
  );
}
