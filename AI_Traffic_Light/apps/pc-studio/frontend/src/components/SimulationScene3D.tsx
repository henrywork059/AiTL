import { useEffect, useState } from "react";
import type { ExperimentTimelinePoint } from "../types/experiments";
import "./simulationScene3D.css";

type Props = { samples: ExperimentTimelinePoint[]; mode: "fixed" | "adaptive" };
const MAX_VISIBLE = 14;
const clamp = (value: number, low: number, high: number) => Math.max(low, Math.min(high, value));

export function SimulationScene3D({ samples, mode }: Props) {
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [angle, setAngle] = useState(-28);
  const [tilt, setTilt] = useState(58);
  const [zoom, setZoom] = useState(1);
  useEffect(() => { setIndex(0); setPlaying(false); }, [samples, mode]);
  useEffect(() => {
    if (!playing || samples.length < 2) return;
    const timer = window.setInterval(() => setIndex(current => (current + 1) % samples.length), 600);
    return () => window.clearInterval(timer);
  }, [playing, samples.length]);
  const sample = samples[clamp(index, 0, Math.max(0, samples.length - 1))];
  const phase = (sample?.phase_key || sample?.phase || "").toLowerCase();
  const vehicleGreen = phase.includes("vehicle") && phase.includes("green");
  const pedestrianGreen = phase.includes("pedestrian") && (phase.includes("walk") || phase.includes("green"));
  const vehicles = clamp(Math.floor(sample?.vehicle_queue ?? 0), 0, MAX_VISIBLE);
  const pedestrians = clamp(Math.floor(sample?.pedestrian_queue ?? 0), 0, MAX_VISIBLE);

  return <section className="scene3d-panel" aria-label="Interactive 3D simulation replay">
    <div className="scene3d-toolbar">
      <div><strong>3D junction replay</strong><small>{mode === "adaptive" ? "Adaptive" : "Fixed"} · synthetic experiment samples · illustrative positions</small></div>
      <div className="scene3d-actions">
        <button type="button" onClick={() => { setAngle(-28); setTilt(58); setZoom(1); }}>Reset view</button>
        <button type="button" onClick={() => setTilt(current => current === 0 ? 58 : 0)}>{tilt === 0 ? "Perspective" : "Top view"}</button>
        <button type="button" onClick={() => setPlaying(current => !current)} disabled={samples.length < 2}>{playing ? "Pause" : "Play"}</button>
      </div>
    </div>
    <div className="scene3d-viewport" role="img" aria-label={sample ? `3D illustrative junction at ${sample.t.toFixed(1)} seconds; vehicle queue ${sample.vehicle_queue}, pedestrian queue ${sample.pedestrian_queue}, phase ${sample.phase}` : "No simulation samples available"}>
      <div className="scene3d-world" style={{ transform: `translate(-50%, -50%) scale(${zoom}) rotateX(${tilt}deg) rotateZ(${angle}deg)` }}>
        <div className="scene3d-ground"/>
        <div className="scene3d-road"/>
        <div className="scene3d-line scene3d-line-top"/>
        <div className="scene3d-line scene3d-line-bottom"/>
        {Array.from({ length: 7 }, (_, n) => <div key={n} className="scene3d-zebra" style={{ left: `${37 + n * 4.4}%` }}/>)}
        <div className="scene3d-signal scene3d-signal-vehicle" title={`Vehicle signal: ${vehicleGreen ? "green" : "stop/clearance"}`}>
          <span className={vehicleGreen ? "green" : "red"}/>
        </div>
        <div className="scene3d-signal scene3d-signal-pedestrian" title={`Pedestrian signal: ${pedestrianGreen ? "walk" : "stop/clearance"}`}>
          <span className={pedestrianGreen ? "green" : "red"}/>
        </div>
        {Array.from({ length: vehicles }, (_, n) => <div key={`v${n}`} className="scene3d-car" style={{ left: `${9 + (n % 7) * 10}%`, top: `${n < 7 ? 42 : 54}%` }} title="Illustrative queued vehicle"><span/></div>)}
        {Array.from({ length: pedestrians }, (_, n) => <div key={`p${n}`} className="scene3d-person" style={{ left: `${12 + (n % 7) * 10}%`, top: `${n < 7 ? 22 : 76}%` }} title="Illustrative waiting pedestrian"><span/></div>)}
      </div>
      {!sample && <p className="scene3d-empty">Run or select an experiment to view its 3D replay.</p>}
    </div>
    <div className="scene3d-footer">
      <label>Orbit <input aria-label="Rotate 3D scene" type="range" min="-180" max="180" value={angle} onChange={event => setAngle(Number(event.target.value))}/></label>
      <label>Pitch <input aria-label="Tilt 3D scene" type="range" min="0" max="70" value={tilt} onChange={event => setTilt(Number(event.target.value))}/></label>
      <label>Zoom <input aria-label="Zoom 3D scene" type="range" min="0.65" max="1.4" step="0.05" value={zoom} onChange={event => setZoom(Number(event.target.value))}/></label>
      <label className="scene3d-time">Time <input aria-label="Simulation replay time" type="range" min="0" max={Math.max(0,samples.length-1)} value={clamp(index,0,Math.max(0,samples.length-1))} disabled={!samples.length} onChange={event => { setIndex(Number(event.target.value)); setPlaying(false); }}/></label>
      <div className="scene3d-readout" aria-live="off">
        <strong>{sample ? `${sample.t.toFixed(1)} s` : "—"}</strong>
        <span>{sample?.phase.replaceAll("_", " ") ?? "No phase"}</span>
        <span>Vehicles waiting: {sample?.vehicle_queue ?? "—"}</span>
        <span>Pedestrians waiting: {sample?.pedestrian_queue ?? "—"}</span>
      </div>
    </div>
    <p className="scene3d-disclaimer">3D objects are schematic representations of aggregate queue samples, not measured positions, identities, paths, or camera detections. Signal indications use recorded phase labels; traffic controllers are unchanged.</p>
  </section>;
}
