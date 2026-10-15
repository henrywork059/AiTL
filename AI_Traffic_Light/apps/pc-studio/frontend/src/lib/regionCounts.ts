import type { Detection, Zone } from "../types";
import type { CrosswalkConfig } from "../types/crosswalks";

export function cameraRegions(config: CrosswalkConfig | null, sourceId: string): Zone[] {
  if (!config) return [];
  for (const crossing of config.crosswalks) {
    const side = crossing.camera_side_a_id === sourceId ? "a" : crossing.camera_side_b_id === sourceId ? "b" : null;
    if (!side) continue;
    return crossing.regions
      .filter((region) => !region.camera_side || region.camera_side === side)
      .map((region) => ({
        id: region.id, label: region.label, type: "counting_region" as const,
        polygon: region.vertices_by_side?.[side] ?? region.vertices,
      }));
  }
  return [];
}

export function pointInRegion([x, y]: [number, number], polygon: [number, number][]): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i], [xj, yj] = polygon[j];
    if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

export function regionClassCounts(
  regions: Zone[], detections: Detection[], imageWidth: number, imageHeight: number,
): Record<string, Record<string, number>> {
  const counts = Object.fromEntries(regions.map((region) => [region.id, {} as Record<string, number>]));
  for (const detection of detections) {
    // Bottom-center acts as the object's ground-contact point.
    const [x1, , x2, y2] = detection.box_xyxy;
    const point: [number, number] = [(x1 + x2) * 0.5 * 1280 / imageWidth, y2 * 720 / imageHeight];
    // Assign once for this camera if edited regions overlap.
    const region = regions.find((item) => pointInRegion(point, item.polygon));
    if (region) counts[region.id][detection.class_name] = (counts[region.id][detection.class_name] ?? 0) + 1;
  }
  return counts;
}
