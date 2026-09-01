import type {
  JunctionConfig,
  JunctionLoadLevel,
  JunctionNetworkConfig,
  JunctionOverviewNode,
} from "../types/junctionNetwork";

export const JUNCTION_LOAD_LABELS: Record<JunctionLoadLevel, string> = {
  unavailable: "No live data",
  clear: "Clear",
  light: "Light",
  moderate: "Moderate",
  heavy: "Heavy",
};

export function cloneJunctionNetworkConfig(config: JunctionNetworkConfig): JunctionNetworkConfig {
  return JSON.parse(JSON.stringify(config)) as JunctionNetworkConfig;
}

export function clampNumber(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
}

export function nextJunctionNetworkId(prefix: string, existing: string[]): string {
  const root = `${prefix}_${Date.now().toString(36)}`;
  if (!existing.includes(root)) return root;
  let suffix = 2;
  while (existing.includes(`${root}_${suffix}`)) suffix += 1;
  return `${root}_${suffix}`;
}

export function junctionLoadClass(level: JunctionLoadLevel): string {
  return `junction-load junction-load-${level}`;
}

export function junctionPhaseLabel(value: string | null): string {
  if (!value) return "No live phase";
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function junctionWarningClass(severity: string): string {
  if (severity === "critical") return "junction-warning junction-warning-critical";
  if (severity === "warning") return "junction-warning junction-warning-warning";
  return "junction-warning junction-warning-info";
}

export function junctionEventClass(severity: string): string {
  if (severity === "critical") return "junction-event junction-event-critical";
  if (severity === "attention") return "junction-event junction-event-attention";
  return "junction-event junction-event-info";
}

export function fallbackJunctionNode(config: JunctionConfig, activeId: string): JunctionOverviewNode {
  return {
    id: config.id,
    label: config.label,
    enabled: config.enabled,
    active_intersection: config.id === activeId,
    position: config.position,
    source_ids: config.source_ids,
    primary_source_id: config.primary_source_id,
    signal_profile: config.signal_profile,
    cameras: [],
    camera_count: config.source_ids.length,
    reachable_camera_count: 0,
    streaming_camera_count: 0,
    live: {
      available: false,
      pipeline_source_active: false,
      source_id: null,
      source_mapping_matched: false,
      observation_provenance: "unavailable",
      phase: null,
      decision: null,
      decision_reason: null,
      evaluated_at_ms: null,
      source_timestamp_ms: null,
      vehicle: { total: 0, waiting: 0, load: "unavailable" },
      pedestrian: { total: 0, waiting: 0, crossing: 0, load: "unavailable" },
      decision_context: null,
    },
    events: [],
    warnings: [],
    warning_count: 0,
    event_count: 0,
  };
}
