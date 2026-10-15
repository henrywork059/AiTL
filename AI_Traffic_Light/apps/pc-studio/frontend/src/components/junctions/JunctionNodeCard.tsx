import type { PointerEvent as ReactPointerEvent } from "react";
import { JUNCTION_EDGES, JUNCTION_EDGE_LABELS } from "../../types/junctionNetwork";
import type { JunctionConfig, JunctionEdge, JunctionOverviewNode } from "../../types/junctionNetwork";
import {
  JUNCTION_LOAD_LABELS,
  junctionLoadClass,
  junctionPhaseLabel,
} from "../../lib/junctionNetworkView";

type JunctionNodeCardProps = {
  config: JunctionConfig;
  node: JunctionOverviewNode;
  active: boolean;
  selected: boolean;
  onSelect: (id: string) => void;
  selectedEdge: JunctionEdge | null;
  onSelectEdge: (id: string, edge: JunctionEdge) => void;
  onBeginDrag: (id: string, event: ReactPointerEvent<HTMLButtonElement>) => void;
};

export function JunctionNodeCard({
  config,
  node,
  active,
  selected,
  onSelect,
  selectedEdge,
  onSelectEdge,
  onBeginDrag,
}: JunctionNodeCardProps) {
  const online = node.reachable_camera_count > 0 || node.live.available;

  return (
    <article
      className={`junction-node ${selected ? "junction-node-selected" : ""} ${node.warning_count ? "junction-node-warning" : ""} ${config.enabled ? "" : "junction-node-disabled"}`}
      style={{ left: `${config.position.x}%`, top: `${config.position.y}%` }}
      onClick={() => onSelect(config.id)}
    >
      <button
        className="junction-drag-handle"
        type="button"
        onPointerDown={(event) => onBeginDrag(config.id, event)}
        title="Drag junction"
      >
        <span className={`junction-node-state ${online ? "junction-node-state-online" : ""}`} />
        <span className="junction-node-heading">
          <span className="junction-node-title-row">
            <strong>{config.label}</strong>
            {active && <span className="junction-active-mark">ACTIVE</span>}
          </span>
          <span className="junction-node-id">{config.id}</span>
        </span>
        <span className="junction-drag-symbol">•••</span>
      </button>
      <div className="junction-node-edge-layout">
        <div className="junction-node-body">
          <div className="junction-node-loads">
            <span className={junctionLoadClass(node.live.vehicle.load)}>
              V {JUNCTION_LOAD_LABELS[node.live.vehicle.load]}
            </span>
            <span className={junctionLoadClass(node.live.pedestrian.load)}>
              P {JUNCTION_LOAD_LABELS[node.live.pedestrian.load]}
            </span>
          </div>
          <div className="junction-node-meta">
            <span>{node.camera_count} camera{node.camera_count === 1 ? "" : "s"}</span>
            <span>{junctionPhaseLabel(node.live.phase)}</span>
          </div>
          <div className="junction-node-alerts">
            {node.event_count > 0 && <span className="junction-node-event-count">{node.event_count} event</span>}
            {node.warning_count > 0 && <span className="junction-node-warning-count">{node.warning_count} warning</span>}
          </div>
        </div>
        {JUNCTION_EDGES.map((edge) => (
          <button
            key={edge}
            type="button"
            className={`junction-edge-tag junction-edge-${edge}${config.crosswalk_edges[edge] ? " is-linked" : ""}${selectedEdge === edge ? " is-selected" : ""}`}
            aria-label={`Edge ${JUNCTION_EDGE_LABELS[edge]} of ${config.label}: ${config.crosswalk_edges[edge] ?? "unassigned"}. Select edge to assign a crosswalk`}
            aria-pressed={selected && selectedEdge === edge}
            title={`Edge ${JUNCTION_EDGE_LABELS[edge]} · ${config.crosswalk_edges[edge] ?? "No crosswalk"}`}
            onClick={(event) => {
              event.stopPropagation();
              onSelectEdge(config.id, edge);
            }}
          >
            {JUNCTION_EDGE_LABELS[edge]}
          </button>
        ))}
      </div>
    </article>
  );
}
