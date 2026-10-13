export type CrosswalkVertex = [number, number];

export type CrosswalkRegion = {
  id: string;
  label: string;
  vertices: [CrosswalkVertex, CrosswalkVertex, CrosswalkVertex, CrosswalkVertex];
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
