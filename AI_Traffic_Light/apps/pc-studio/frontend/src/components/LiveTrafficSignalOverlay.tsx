import type { TrafficState } from "../types";

type Props = {
  traffic: TrafficState | null;
};

export function LiveTrafficSignalOverlay({ traffic }: Props) {
  const phase = traffic?.phase ?? "all_red";
  const redOn = phase !== "vehicle_green" && phase !== "vehicle_yellow";
  const amberOn = phase === "vehicle_yellow";
  const greenOn = phase === "vehicle_green";
  const pedestrianText = phase === "pedestrian_green"
    ? "WALK"
    : phase === "pedestrian_flashing"
      ? "CLEAR"
      : "WAIT";

  return (
    <div className="live-signal-overlay" aria-label={`Simulated traffic signal: ${phase.replaceAll("_", " ")}`}>
      <div className="live-signal-head" aria-hidden="true">
        <span className={`live-signal-lamp live-signal-red ${redOn ? "active" : ""}`} />
        <span className={`live-signal-lamp live-signal-amber ${amberOn ? "active" : ""}`} />
        <span className={`live-signal-lamp live-signal-green ${greenOn ? "active" : ""}`} />
      </div>
      <div className="live-signal-copy">
        <strong>{phase.replaceAll("_", " ")}</strong>
        <span>PED {pedestrianText}</span>
      </div>
    </div>
  );
}
