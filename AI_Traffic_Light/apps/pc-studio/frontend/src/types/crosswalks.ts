export type CrosswalkVertex = [number, number];
export type CrosswalkQuadrilateral = [CrosswalkVertex, CrosswalkVertex, CrosswalkVertex, CrosswalkVertex];

export type CrosswalkRegion = {
  id: string;
  label: string;
  camera_side?: "a" | "b"; // Read older one-sided regions without reassigning them.
  vertices: CrosswalkQuadrilateral;
  vertices_by_side?: Partial<Record<"a" | "b", CrosswalkQuadrilateral>>;
};

export type Crosswalk = {
  id: string;
  label: string;
  location: string;
  camera_side_a_id: string | null;
  camera_side_b_id: string | null;
  regions: CrosswalkRegion[];
};

export type CrosswalkConfig = {
  schema_version: 1;
  crosswalks: Crosswalk[];
};
