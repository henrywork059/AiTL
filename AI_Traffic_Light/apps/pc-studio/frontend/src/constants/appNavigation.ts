import type { AppPageId, AppPageSummary, AppSection } from "../types/app";
import { PROJECT_VERSION_LABEL } from "./projectVersion";

export const APP_VERSION_LABEL = PROJECT_VERSION_LABEL;

export const PAGE_DETAILS: Record<AppPageId, AppPageSummary> = {
  dashboard: { id: "dashboard", label: "Dashboard", shortLabel: "Dashboard", description: "System health, release state, validation checks, and the capabilities available in this local prototype.", status: "test-ready" },
  live_ai: { id: "live_ai", label: "Live AI", shortLabel: "Live AI", description: "Run the selected local detection model on camera or simulation frames and inspect detections, zones, tracks, and simulated signal context.", status: "test-ready" },
  camera_sources: { id: "camera_sources", label: "Camera Sources", shortLabel: "Cameras", description: "Use the built-in traffic simulation or receive JPEG/PNG frames from a camera node on the local network.", status: "test-ready" },
  camera_diagnostics: { id: "camera_diagnostics", label: "Camera Diagnostics", shortLabel: "Camera Test", description: "Run one-click staged diagnostics against the selected ESP camera and identify the most likely failing control, Wi-Fi, direct-stream, contention, or PC Studio layer.", status: "test-ready" },
  zone_editor: { id: "zone_editor", label: "Zone Editor", shortLabel: "Zones", description: "Define traffic decision zones, analytics regions, and counting lines directly against the current camera reference frame.", status: "test-ready" },
  traffic_logic: { id: "traffic_logic", label: "Traffic Logic", shortLabel: "Logic", description: "Define ranked traffic scenarios from metrics or class counts in zones, configure protected timing, inspect the winning signal response, and review decision history.", status: "test-ready" },
  traffic_analytics: { id: "traffic_analytics", label: "Traffic Analytics", shortLabel: "Analytics", description: "Inspect sampled occupancy separately from tracked flow events, with time filters, summaries, charts, and CSV export.", status: "test-ready" },
  simulation_lab: { id: "simulation_lab", label: "Simulation Lab", shortLabel: "Experiments", description: "Run repeatable seeded Fixed-vs-Adaptive comparisons and inspect waiting, queue, throughput, signal-use, rule, and diagnostic telemetry in one workspace.", status: "test-ready" },
  dataset_capture: { id: "dataset_capture", label: "Dataset Capture", shortLabel: "Capture", description: "Save the current camera or simulation frame with session metadata, a quality tag, and an optional note.", status: "test-ready" },
  dataset_review: { id: "dataset_review", label: "Dataset Review", shortLabel: "Review / Label", description: "Review captured images, draw manual bounding boxes, remove unsuitable captures, and build the managed YOLO dataset.", status: "test-ready" },
  train_export: { id: "train_export", label: "Train / Export", shortLabel: "Train", description: "Run local YOLO training, monitor validation convergence, and use patience-based early stopping. Runtime export remains planned.", status: "test-ready" },
  model_registry: { id: "model_registry", label: "Model Registry", shortLabel: "Models", description: "Inspect local training runs, load a model for inference, choose the default model, or remove an obsolete run.", status: "test-ready" },
  settings: { id: "settings", label: "Settings", shortLabel: "Settings", description: "Configure persisted inference, polling, training, and logging defaults used by PC Studio.", status: "test-ready" },
  logs: { id: "logs", label: "Logs & Errors", shortLabel: "Logs", description: "Inspect recent backend events with severity, module scope, stable error code, and request ID context.", status: "test-ready" },
};

export const APP_SECTIONS: AppSection[] = [
  { id: "operate", label: "Operate", pages: [PAGE_DETAILS.dashboard, PAGE_DETAILS.live_ai, PAGE_DETAILS.camera_sources, PAGE_DETAILS.camera_diagnostics] },
  { id: "traffic", label: "Traffic", pages: [PAGE_DETAILS.zone_editor, PAGE_DETAILS.traffic_logic, PAGE_DETAILS.traffic_analytics, PAGE_DETAILS.simulation_lab] },
  { id: "data", label: "Data & models", pages: [PAGE_DETAILS.dataset_capture, PAGE_DETAILS.dataset_review, PAGE_DETAILS.train_export, PAGE_DETAILS.model_registry] },
  { id: "system", label: "System", pages: [PAGE_DETAILS.settings, PAGE_DETAILS.logs] },
];
