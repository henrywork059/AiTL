type PreviewFrameStatus = {
  active_source_id: string | null;
  simulation_enabled: boolean;
  frame_available: boolean;
  stale: boolean;
  origin: "upload" | "simulation" | null;
  simulation_fault?: string | null;
};

/** A selected-camera label must not be paired with an inconsistent pipeline snapshot. */
export function matchesSelectedCameraFrame(
  status: PreviewFrameStatus | null,
  sourceId: string,
  kind: "esp32" | "simulation",
): boolean {
  const simulated = kind === "simulation";
  return Boolean(status && status.frame_available && !status.stale && !status.simulation_fault
    && status.active_source_id === sourceId && status.simulation_enabled === simulated
    && status.origin === (simulated ? "simulation" : "upload"));
}
