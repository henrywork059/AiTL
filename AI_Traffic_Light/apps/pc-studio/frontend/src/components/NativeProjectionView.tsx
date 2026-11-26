import { useRef, useState } from "react";
import { fetchNativeProjection, type NativeProjectionScene } from "../lib/remoteCameraApi";
import { useSerialPolling } from "../lib/useSerialPolling";

const SOURCE_TRANSFORM: Record<string, string> = {
  simulation_camera: "",
  simulation_camera_b: "translate(0 719) scale(1 -1)",
  simulation_camera_c: "translate(1279 0) scale(-1 1)",
  simulation_camera_d: "translate(1279 719) scale(-1 -1)",
};

/** Diagnostic native coordinates only; no legacy overlays or capture controls. */
export function NativeProjectionView({sourceId}: {sourceId: string}) {
  const [scene, setScene] = useState<NativeProjectionScene | null>(null);
  const [status, setStatus] = useState("Loading native preview");
  const latest = useRef({generation: -1, tick: -1});
  useSerialPolling(async ({signal, isCurrent}) => {
    const response = await fetchNativeProjection(signal);
    if (!isCurrent()) return;
    if (response.provenance !== "synthetic_sumo_projection") {
      setScene(null); setStatus("Invalid native provenance"); return;
    }
    const generation = response.generation;
    if (generation !== undefined && generation < latest.current.generation) return;
    if (generation !== undefined && generation > latest.current.generation) {
      latest.current = {generation, tick: -1};
    }
    if (response.status !== "running" || !response.snapshot) {
      setScene(null);
      setStatus(response.status === "disabled" ? "Native preview disabled on server" : "Native preview: " + response.status);
      return;
    }
    const next = response.snapshot;
    if (next.provenance !== response.provenance || next.generation !== generation ||
        next.schema_version !== 1 || next.width !== 1280 || next.height !== 720 ||
        !Number.isSafeInteger(next.tick) || next.tick < 0 || !Number.isSafeInteger(generation)) {
      setScene(null); setStatus("Invalid native scene"); return;
    }
    if (next.tick < latest.current.tick) return;
    latest.current = {generation: next.generation, tick: next.tick};
    setScene(next);
    setStatus("Native simulation · read-only");
  }, 500, {restartKey: sourceId, onError: () => {setScene(null); setStatus("Native preview unavailable");}});
  return <div className="native-projection-view" data-native-status={scene ? "running" : "unavailable"}>
    {scene && <svg viewBox="0 0 1280 720" role="img" aria-label="Synthetic native SUMO road and agents"
      data-native-generation={scene.generation} data-native-tick={scene.tick}>
      <rect width="1280" height="720" fill="#1d2125"/>
      <g transform={SOURCE_TRANSFORM[sourceId] ?? ""} key={scene.generation}>
        {(["road","walk","crossing"] as const).flatMap(kind => scene.lanes.filter(lane => lane.kind === kind).map(lane =>
          <polyline key={lane.id} data-native-lane={lane.id}
            points={lane.points.map(p => p.join(",")).join(" ")} fill="none"
            stroke={kind === "road" ? "#56504b" : kind === "walk" ? "#8e8982" : "#e1e1e1"}
            strokeWidth={lane.width_px} strokeLinejoin="round" strokeLinecap="round"/>))}
        {scene.agents.map(agent => <circle key={agent.id} data-native-agent={agent.id}
          cx={agent.x} cy={agent.y} r={agent.kind === "vehicle" ? 4 : 3}
          fill={agent.kind === "vehicle" ? "#41aaff" : "#f5dc41"}/>)}
      </g>
    </svg>}
    <span role="status">{status}{scene ? ` · ${scene.time_s.toFixed(1)} s · ${scene.agents.length} agents` : ""}</span>
  </div>;
}
