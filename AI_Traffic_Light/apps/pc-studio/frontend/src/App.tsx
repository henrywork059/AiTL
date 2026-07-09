import { useEffect, useMemo, useState } from "react";
import { fetchMockFrame, fetchMockZones, fetchTrafficState } from "./api";
import { AppStatusBar } from "./components/AppStatusBar";
import { AppShell } from "./layout/AppShell";
import { CameraSourcesPage } from "./pages/CameraSourcesPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DatasetCapturePage } from "./pages/DatasetCapturePage";
import { DatasetReviewPage } from "./pages/DatasetReviewPage";
import { LiveAiPage } from "./pages/LiveAiPage";
import { LogsPage } from "./pages/LogsPage";
import { ModelRegistryPage } from "./pages/ModelRegistryPage";
import { SettingsPage } from "./pages/SettingsPage";
import { TrafficLogicPage } from "./pages/TrafficLogicPage";
import { TrainExportPage } from "./pages/TrainExportPage";
import { ZoneEditorPage } from "./pages/ZoneEditorPage";
import type { AppPageId } from "./types/app";
import type { DetectionFrame, TrafficState, Zone } from "./types";

export default function App() {
  const [frame, setFrame] = useState<DetectionFrame | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [traffic, setTraffic] = useState<TrafficState | null>(null);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.45);
  const [activePage, setActivePage] = useState<AppPageId>("dashboard");

  useEffect(() => {
    void fetchMockFrame().then(setFrame);
    void fetchMockZones().then(setZones);
    void fetchTrafficState().then(setTraffic);
  }, []);

  const filteredDetections = useMemo(() => {
    if (!frame) return [];
    return frame.detections.filter((detection) => detection.confidence >= confidenceThreshold);
  }, [frame, confidenceThreshold]);

  function renderPage() {
    switch (activePage) {
      case "dashboard":
        return <DashboardPage />;
      case "live_ai":
        return (
          <LiveAiPage
            frame={frame}
            zones={zones}
            traffic={traffic}
            detections={filteredDetections}
            confidenceThreshold={confidenceThreshold}
            onConfidenceChange={setConfidenceThreshold}
          />
        );
      case "camera_sources":
        return <CameraSourcesPage />;
      case "zone_editor":
        return <ZoneEditorPage />;
      case "traffic_logic":
        return <TrafficLogicPage />;
      case "dataset_capture":
        return <DatasetCapturePage />;
      case "dataset_review":
        return <DatasetReviewPage />;
      case "train_export":
        return <TrainExportPage />;
      case "model_registry":
        return <ModelRegistryPage />;
      case "settings":
        return <SettingsPage />;
      case "logs":
        return <LogsPage />;
      default:
        return <DashboardPage />;
    }
  }

  return (
    <>
      <AppShell activePage={activePage} onPageChange={setActivePage}>{renderPage()}</AppShell>
      <AppStatusBar />
    </>
  );
}
