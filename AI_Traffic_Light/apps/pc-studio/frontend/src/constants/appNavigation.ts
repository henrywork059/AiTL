import type { AppPageId, AppPageSummary, AppSection } from "../types/app";
import { PROJECT_VERSION_LABEL } from "./projectVersion";

export const APP_VERSION_LABEL = PROJECT_VERSION_LABEL;

export const PAGE_DETAILS: Record<AppPageId, AppPageSummary> = {
  dashboard: { id: "dashboard", label: "Dashboard", shortLabel: "Overview", description: "Backend health, validation and system state.", status: "stable" },
  live_ai: { id: "live_ai", label: "AI Detection", shortLabel: "Detection", description: "Inspect live model detections, tracking and traffic state.", status: "test-ready" },
  camera_sources: { id: "camera_sources", label: "Camera Sources (Legacy)", shortLabel: "Legacy Sources", description: "Legacy camera source screen; replaced by Camera Settings.", status: "legacy" },
  camera_settings: { id: "camera_settings", label: "Camera Settings", shortLabel: "Cameras", description: "Manage physical cameras and mirrored simulation pairs.", status: "stable" },
  camera_diagnostics: { id: "camera_diagnostics", label: "Camera Diagnostics", shortLabel: "Diagnostics", description: "Test ESP camera connections and streaming performance.", status: "test-ready" },
  crosswalks: { id: "crosswalks", label: "Crosswalks", shortLabel: "Crosswalks", description: "Configure crosswalks, regions, edge labels and paired cameras.", status: "stable" },
  junction_network: { id: "junction_network", label: "Junction Network", shortLabel: "Junctions", description: "Arrange junctions, assign cameras and connect numbered edges.", status: "test-ready" },
  zones: { id: "zones", label: "Zones", shortLabel: "Zones", description: "Zone workspace.", status: "test-ready" },
  zone_editor: { id: "zone_editor", label: "Zone Editor (Legacy)", shortLabel: "Legacy Zones", description: "Legacy zone editor; replaced by Zones.", status: "legacy" },
  traffic_logic: { id: "traffic_logic", label: "Signal Control", shortLabel: "Signal Control", description: "Configure signal scenarios, timing and decision rules.", status: "test-ready" },
  traffic_analytics: { id: "traffic_analytics", label: "Traffic Analytics", shortLabel: "Analytics", description: "Review measured occupancy and tracked traffic flow.", status: "test-ready" },
  simulation_lab: { id: "simulation_lab", label: "Simulation Experiments", shortLabel: "Experiments", description: "Compare signal policies in repeatable simulations.", status: "test-ready" },
  dataset_capture: { id: "dataset_capture", label: "Dataset Capture", shortLabel: "Capture", description: "Capture images and associated metadata.", status: "test-ready" },
  dataset_review: { id: "dataset_review", label: "Dataset Review", shortLabel: "Review", description: "Review, label and organize captured data.", status: "test-ready" },
  train_export: { id: "train_export", label: "Model Training", shortLabel: "Training", description: "Train local models and review training metrics.", status: "test-ready" },
  model_registry: { id: "model_registry", label: "Model Registry", shortLabel: "Models", description: "Inspect and select local trained models.", status: "test-ready" },
  settings: { id: "settings", label: "Settings", shortLabel: "Settings", description: "Manage application defaults.", status: "test-ready" },
  logs: { id: "logs", label: "System Logs", shortLabel: "Logs", description: "Inspect backend events, errors and request IDs.", status: "test-ready" },
};

export const APP_SECTIONS: AppSection[] = [
  { id: "operate", label: "Operate", pages: [PAGE_DETAILS.dashboard, PAGE_DETAILS.live_ai, PAGE_DETAILS.camera_settings, PAGE_DETAILS.camera_diagnostics] },
  { id: "traffic", label: "Traffic", pages: [PAGE_DETAILS.junction_network, PAGE_DETAILS.crosswalks, PAGE_DETAILS.zones, PAGE_DETAILS.traffic_logic, PAGE_DETAILS.traffic_analytics, PAGE_DETAILS.simulation_lab] },
  { id: "data", label: "Data & models", pages: [PAGE_DETAILS.dataset_capture, PAGE_DETAILS.dataset_review, PAGE_DETAILS.train_export, PAGE_DETAILS.model_registry] },
  { id: "system", label: "System", pages: [PAGE_DETAILS.settings, PAGE_DETAILS.logs] },
];
