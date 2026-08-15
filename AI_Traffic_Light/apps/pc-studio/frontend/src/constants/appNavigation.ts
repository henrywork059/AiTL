import type { AppPageId, AppPageSummary, AppSection } from "../types/app";

export const APP_VERSION_LABEL = "0_2_0 camera-aligned zones + capture lifecycle";

export const PAGE_DETAILS: Record<AppPageId, AppPageSummary> = {
  dashboard: { id: "dashboard", label: "Dashboard", shortLabel: "Dashboard", description: "Current project version, smoke checks, implemented functions, and explicit prototype boundaries.", status: "test-ready" },
  live_ai: { id: "live_ai", label: "Live AI View", shortLabel: "Live AI", description: "Preview receiver or simulation frames with trained-model detections, persisted zone overlays, and a compact simulated traffic signal.", status: "test-ready" },
  camera_sources: { id: "camera_sources", label: "Camera Sources", shortLabel: "Cameras", description: "Receive device frames or run the controllable PC traffic simulation with density and pause controls.", status: "test-ready" },
  zone_editor: { id: "zone_editor", label: "Zone Editor", shortLabel: "Zones", description: "Create, edit, persist, and reset traffic zones directly over the current camera/simulation feed.", status: "test-ready" },
  traffic_logic: { id: "traffic_logic", label: "Traffic Logic", shortLabel: "Logic", description: "Evaluate live trained-model detections against configured zones and show simulation-only phase recommendations.", status: "test-ready" },
  dataset_capture: { id: "dataset_capture", label: "Dataset Capture", shortLabel: "Capture", description: "Persist receiver or simulation images with paired metadata and quality tags, and delete unwanted captures.", status: "test-ready" },
  dataset_review: { id: "dataset_review", label: "Dataset Review", shortLabel: "Review / Label", description: "Browse or delete saved frames, draw manual bounding boxes, and build the managed YOLO training dataset.", status: "test-ready" },
  train_export: { id: "train_export", label: "Train / Export", shortLabel: "Train", description: "Run local YOLO training with convergence monitoring and automatic early stopping; export remains planned.", status: "test-ready" },
  model_registry: { id: "model_registry", label: "Model Registry", shortLabel: "Models", description: "Review local trained models, set a default model, load a chosen model, and delete outdated runs.", status: "test-ready" },
  settings: { id: "settings", label: "Settings", shortLabel: "Settings", description: "Persist active viewer, training, inference, and backend logging preferences.", status: "test-ready" },
  logs: { id: "logs", label: "Logs & Errors", shortLabel: "Logs", description: "Inspect recent real backend logs, error codes, request IDs, and module scope.", status: "test-ready" },
};

export const APP_SECTIONS: AppSection[] = [
  { id: "operate", label: "Operate", pages: [PAGE_DETAILS.dashboard, PAGE_DETAILS.live_ai, PAGE_DETAILS.camera_sources] },
  { id: "traffic", label: "Traffic setup", pages: [PAGE_DETAILS.zone_editor, PAGE_DETAILS.traffic_logic] },
  { id: "data", label: "Data & model", pages: [PAGE_DETAILS.dataset_capture, PAGE_DETAILS.dataset_review, PAGE_DETAILS.train_export, PAGE_DETAILS.model_registry] },
  { id: "system", label: "System", pages: [PAGE_DETAILS.settings, PAGE_DETAILS.logs] },
];
