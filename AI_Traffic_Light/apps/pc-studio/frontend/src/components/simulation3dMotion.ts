/** Recycled agents must not interpolate backwards across the scene. */
function isReentry(previous: number | undefined, next: number, extent: number): boolean {
  return previous !== undefined && Math.abs(next - previous) > extent / 2;
}

export const isVehicleReentry = isReentry;
export const isPedestrianReentry = isReentry;

/** Transform canonical simulation pixels into each camera's mirrored view. */
export function simulationSourcePoint(x: number, y: number, sourceId: string, width: number, height: number) {
  return {
    x: sourceId === "simulation_camera_c" || sourceId === "simulation_camera_d" ? width - x : x,
    y: sourceId === "simulation_camera_b" || sourceId === "simulation_camera_d" ? height - y : y,
  };
}
