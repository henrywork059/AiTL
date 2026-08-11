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
  onRefresh: () => void;
  refreshing: boolean;
};

export function LiveAiPage({
  frame,
  zones,
  traffic,
  detections,
  confidenceThreshold,
  onConfidenceChange,
  onRefresh,
  refreshing,
}: Props) {
  return (
    <div className="live-layout">
      <section className="panel live-panel">
        <div className="panel-header">
          <div>
            <h2>Live detection canvas</h2>
            <p className="placeholder-copy">Mock road scene rendered from API/fallback JSON. This is not a real camera stream yet.</p>
          </div>
          <span className="status-pill">mock frame</span>
        </div>
        {frame ? <LiveView frame={frame} detections={detections} zones={zones} /> : <p>Loading mock frame...</p>}
      </section>

      <aside className="side-column">
        {traffic && <TrafficLight traffic={traffic} />}
        {traffic && <StatusPanel traffic={traffic} />}
        <ControlsPanel
          confidenceThreshold={confidenceThreshold}
          onConfidenceChange={onConfidenceChange}
          onRefresh={onRefresh}
          refreshing={refreshing}
        />
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
