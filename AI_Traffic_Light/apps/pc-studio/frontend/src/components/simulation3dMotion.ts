/** Recycled agents must not interpolate backwards across the scene. */
function isReentry(previous: number | undefined, next: number, extent: number): boolean {
  return previous !== undefined && Math.abs(next - previous) > extent / 2;
}

export const isVehicleReentry = isReentry;
export const isPedestrianReentry = isReentry;
