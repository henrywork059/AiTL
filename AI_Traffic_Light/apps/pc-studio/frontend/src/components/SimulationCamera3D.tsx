import { useRef, useState, type PointerEvent, type WheelEvent } from "react";
import { fetchSimulationScene, type SimulationScene } from "../lib/remoteCameraApi";
import { useSerialPolling } from "../lib/useSerialPolling";
import "./simulationCamera3D.css";

type Props = { sourceId: string };

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

/** Read-only perspective of the actual live camera simulator; never controls its agents. */
export function SimulationCamera3D({ sourceId }: Props) {
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

  return (
    <section className="sim3d-preview" aria-label={`Interactive 3D preview of ${sourceId}`}>
      <div className="sim3d-viewport" onPointerDown={beginDrag} onPointerMove={moveDrag}
        onPointerUp={endDrag} onPointerCancel={endDrag} onWheel={changeZoom}>
        <div className="sim3d-world" aria-hidden="true" style={{
          transform: `translate(-50%, -50%) scale(${zoom}) rotateX(${pitch}deg) rotateZ(${orbit}deg)`,
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
          {scene?.vehicles.map(vehicle => (
            <div className="sim3d-car" key={vehicle.id} title={`${vehicle.vehicle_type} · ${vehicle.direction > 0 ? "eastbound" : "westbound"}`}
              style={{
                left: `${(vehicle.x + vehicle.width / 2) / sizeX * 100}%`,
                top: `${vehicle.y / sizeY * 100}%`,
                width: `${vehicle.width / sizeX * 100}%`,
                backgroundColor: vehicle.color,
                transform: `translate(-50%, -50%) translateZ(15px) rotateZ(${vehicle.direction < 0 ? 180 : 0}deg)`,
              }}>
              <div className="sim3d-car-roof" />
              <div className="sim3d-car-side" />
            </div>
          ))}
          {scene?.pedestrians.map(pedestrian => (
            <div className="sim3d-person" key={pedestrian.id} title="Simulated pedestrian" style={{
              left: `${pedestrian.x / sizeX * 100}%`,
              top: `${pedestrian.y / sizeY * 100}%`,
              backgroundColor: pedestrian.color,
            }}>
              <span />
            </div>
          ))}
        </div>
      </div>
      <div className="sim3d-head">
        <span className="sim3d-flag">3D CAMERA</span>
        <span>{CAMERA_LABEL[sourceId] ?? sourceId}</span>
        {scene?.paused && <span className="sim3d-paused">Paused</span>}
      </div>
      <div className="sim3d-actions">
        <button type="button" onClick={() => { setOrbit(initialOrbit); setPitch(48); setZoom(0.85); }}>Reset</button>
        <button type="button" onClick={() => setPitch(current => current === 0 ? 48 : 0)}>
          {pitch === 0 ? "Perspective" : "Top"}
        </button>
        <label>Zoom <input aria-label="3D camera zoom" type="range" min="0.5" max="1.35" step="0.05"
          value={zoom} onChange={event => setZoom(Number(event.target.value))} /></label>
      </div>
      <div className="sim3d-status" aria-live="off">
        {scene ? <>
          <span>Vehicle <b className={vehicleLight}>{vehicleLight}</b></span>
          <span>Pedestrian <b className={pedestrianLight}>{pedestrianLight === "green" ? "walk" : "stop"}</b></span>
          <span>{phase.replaceAll("_", " ")} · {Math.max(0, Math.ceil(scene.signal.seconds_remaining))} s</span>
          <span>{scene.vehicles.length} cars · {scene.pedestrians.length} people</span>
        </> : <span>{error ?? "Loading 3D simulation scene..."}</span>}
      </div>
      <span className="sim3d-hint">Drag to orbit · Scroll to zoom · synthetic scene</span>
    </section>
  );
}
