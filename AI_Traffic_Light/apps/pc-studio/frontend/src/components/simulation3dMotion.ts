/** A recycled simulator agent must reappear off-screen, not animate back across the road. */
export function isVehicleReentry(previousX: number | undefined, nextX: number, worldWidth: number): boolean {
  return previousX !== undefined && Math.abs(nextX - previousX) > worldWidth / 2;
}
