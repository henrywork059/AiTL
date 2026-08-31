export type AppPageId =
  | "dashboard"
  | "live_ai"
  | "camera_sources"
  | "camera_diagnostics"
  | "junction_network"
  | "zone_editor"
  | "traffic_logic"
  | "traffic_analytics"
  | "simulation_lab"
  | "dataset_capture"
  | "dataset_review"
  | "train_export"
  | "model_registry"
  | "settings"
  | "logs";

export type AppSection = {
  id: string;
  label: string;
  pages: AppPageSummary[];
};

export type AppPageSummary = {
  id: AppPageId;
  label: string;
  shortLabel: string;
  description: string;
  status: "template" | "mock" | "planned" | "test-ready";
};

export type FunctionStatus = "implemented" | "placeholder" | "planned" | "later";

export type FunctionItem = {
  id: string;
  area: string;
  label: string;
  description: string;
  status: FunctionStatus;
};
