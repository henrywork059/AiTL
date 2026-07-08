import type { TrafficState } from "../types";

type Props = {
  traffic: TrafficState;
};

export function TrafficLight({ traffic }: Props) {
  const vehicleGreen = traffic.phase === "vehicle_green";
  const vehicleYellow = traffic.phase === "vehicle_yellow";
  const pedestrianGreen = traffic.phase === "pedestrian_green";

  return (
    <section className="panel compact-panel">
      <div className="panel-header">
        <h2>Signal simulator</h2>
      </div>
      <div className="traffic-light-card">
        <div className="signal-head">
          <div className={vehicleGreen || vehicleYellow || pedestrianGreen ? "lamp red off" : "lamp red"} />
          <div className={vehicleYellow ? "lamp amber" : "lamp amber off"} />
          <div className={vehicleGreen ? "lamp green" : "lamp green off"} />
        </div>
        <div className="signal-info">
          <div className="label">Current phase</div>
          <div className="phase-text">{traffic.phase.replaceAll("_", " ")}</div>
          <div className="label">Next decision</div>
          <div className="decision-text">{traffic.decision.replaceAll("_", " ")}</div>
        </div>
      </div>
    </section>
  );
}
