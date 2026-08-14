import type { AppPageId, AppPageSummary, AppSection } from "../types/app";

export const APP_VERSION_LABEL = "0_1_3 manual labeling";

export const PAGE_DETAILS: Record<AppPageId, AppPageSummary> = {
  dashboard: {
    id: "dashboard",
    label: "Dashboard",
    shortLabel: "Dashboard",
    description: "Project overview, smoke-test state, and next development tasks.",
    status: "mock",
  },
  live_ai: {
    id: "live_ai",
    label: "Live AI View",
    shortLabel: "Live AI",
    description: "Main mock camera/detection viewer with traffic-light simulation.",
    status: "mock",
  },
  camera_sources: {
    id: "camera_sources",
    label: "Camera Sources",
    shortLabel: "Cameras",
    description: "Receive and preview frames uploaded by ESP32 or Raspberry Pi camera nodes.",
    status: "test-ready",
  },
  zone_editor: {
    id: "zone_editor",
    label: "Zone Editor",
    shortLabel: "Zones",
    description: "Create pedestrian waiting, crossing, vehicle queue, and ignore zones.",
    status: "template",
  },
  traffic_logic: {
    id: "traffic_logic",
    label: "Traffic Logic",
    shortLabel: "Logic",
    description: "Review rule-based signal decisions and safety checks.",
    status: "mock",
  },
  dataset_capture: {
    id: "dataset_capture",
    label: "Dataset Capture",
    shortLabel: "Capture",
    description: "Persist receiver or simulation images with paired metadata and quality tags.",
    status: "test-ready",
  },
  dataset_review: {
    id: "dataset_review",
    label: "Dataset Review",
    shortLabel: "Review / Label",
    description: "Browse saved frames, draw manual bounding boxes, and build the managed YOLO training dataset.",
    status: "test-ready",
  },
  train_export: {
    id: "train_export",
    label: "Train / Export",
    shortLabel: "Train",
    description: "Run optional local YOLO training from the managed or another labeled dataset; export remains planned.",
    status: "test-ready",
  },
  model_registry: {
    id: "model_registry",
    label: "Model Registry",
    shortLabel: "Models",
    description: "Compare model versions, metrics, classes, and export status.",
    status: "template",
  },
  settings: {
    id: "settings",
    label: "Settings",
    shortLabel: "Settings",
    description: "Project paths, API base URL, debug mode, and app preferences.",
    status: "template",
  },
  logs: {
    id: "logs",
    label: "Logs & Errors",
    shortLabel: "Logs",
    description: "Debug logs, error codes, request IDs, and recent app events.",
    status: "mock",
  },
};

export const APP_SECTIONS: AppSection[] = [
  {
    id: "operate",
    label: "Operate",
    pages: [PAGE_DETAILS.dashboard, PAGE_DETAILS.live_ai, PAGE_DETAILS.camera_sources],
  },
  {
    id: "traffic",
    label: "Traffic setup",
    pages: [PAGE_DETAILS.zone_editor, PAGE_DETAILS.traffic_logic],
  },
  {
    id: "data",
    label: "Data & model",
    pages: [PAGE_DETAILS.dataset_capture, PAGE_DETAILS.dataset_review, PAGE_DETAILS.train_export, PAGE_DETAILS.model_registry],
  },
  {
    id: "system",
    label: "System",
    pages: [PAGE_DETAILS.settings, PAGE_DETAILS.logs],
  },
];
