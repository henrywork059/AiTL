export type Crosswalk = {
  id: string;
  label: string;
  location: string;
  camera_side_a_id: string | null;
  camera_side_b_id: string | null;
};

export type CrosswalkConfig = {
  schema_version: 1;
  crosswalks: Crosswalk[];
};
