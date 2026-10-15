import type { ScenarioSignalStatus } from "../types/signalScenarios";

type Props = {
  signal: ScenarioSignalStatus | null;
  available: boolean;
  adjacentNotice: string | null;
};

export function CrosswalkSignalIndicators({ signal, available, adjacentNotice }: Props) {
  const state = available && signal ? signal.phase : null;
  const vehicle = state === "vehicle_green" ? "green" : state === "vehicle_yellow" ? "amber"
    : state ? "red" : "unknown";
  const pedestrian = state === "pedestrian_green" ? "walk"
    : state === "pedestrian_flashing" ? "clear" : state ? "stop" : "unknown";
  const adjustment = available && signal?.winning_scenario_label
    ? signal.winning_scenario_label : null;
  return <>
    <div className="crossing-signal-side crossing-signal-vehicle" aria-label={"Vehicle signal: " + vehicle}
      title={"Vehicle " + vehicle}>
      <strong>V</strong>
      {(["red", "amber", "green"] as const).map((color) => <i key={color}
        className={"crossing-signal-lamp crossing-signal-lamp-" + color + (vehicle === color ? " is-lit" : "")} />)}
    </div>
    <div className="crossing-signal-side crossing-signal-pedestrian" aria-label={"Pedestrian signal: " + pedestrian}
      title={"Pedestrian " + pedestrian}>
      <strong>P</strong>
      <i className={"crossing-signal-lamp crossing-signal-lamp-red" + (pedestrian === "stop" ? " is-lit" : "")} />
      <i className={"crossing-signal-lamp crossing-signal-lamp-green" + (pedestrian === "walk" ? " is-lit" : "")} />
      <i className={"crossing-signal-lamp crossing-signal-lamp-amber" + (pedestrian === "clear" ? " is-lit" : "")} />
    </div>
    <div className="crossing-signal-summary">
      <small>{available && signal
        ? "Simulation signals: vehicle " + vehicle + " / pedestrian " + pedestrian + " · " +
          Math.ceil(signal.seconds_remaining) + "s remaining"
        : "No verified crosswalk signal (not controlled)"}</small>
      {adjustment && <small>Adjustment request: {adjustment}{signal?.dry_run ? " (dry run)" : ""}</small>}
      {adjacentNotice && <small>{adjacentNotice}</small>}
    </div>
  </>;
}
