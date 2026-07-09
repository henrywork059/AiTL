import { ControlsPanel } from "../components/ControlsPanel";
import { DetectionTable } from "../components/DetectionTable";
import { LiveView } from "../components/LiveView";
import { StatusPanel } from "../components/StatusPanel";
import { TrafficLight } from "../components/TrafficLight";
import { ZonePanel } from "../components/ZonePanel";
import type { DetectionFrame, TrafficState, Zone, Detection } from "../types";

type Props = {
  frame: DetectionFrame | null;
  zones: Zone[];
  traffic: TrafficState | null;
  detections: Detection[];
  confidenceThreshold: number;
  onConfidenceChange: (value: number) => void;
};

export function LiveAiPage({
  frame,
  zones,
  traffic,
  detections,
  confidenceThreshold,
  onConfidenceChange,
}: Props) {
  return (
    <div className="live-layout">
      <section className="panel live-panel">
        <div className="panel-header">
          <h2>Live detection canvas</h2>
          <span className="status-pill">mock frame</span>
        </div>
        {frame ? <LiveView frame={frame} detections={detections} zones={zones} /> : <p>Loading mock frame...</p>}
      </section>

      <aside className="side-column">
        {traffic && <TrafficLight traffic={traffic} />}
        {traffic && <StatusPanel traffic={traffic} />}
        <ControlsPanel confidenceThreshold={confidenceThreshold} onConfidenceChange={onConfidenceChange} />
        <ZonePanel zones={zones} />
      </aside>

      <section className="panel bottom-panel full-span">
        <div className="panel-header">
          <h2>Detection result table</h2>
          <span>{detections.length} visible</span>
        </div>
        <DetectionTable detections={detections} />
      </section>
    </div>
  );
}
