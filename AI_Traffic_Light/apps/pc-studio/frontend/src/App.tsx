import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchHealth,
  fetchCameraStatus,
  fetchMockFrame,
  fetchMockZones,
  fetchRecentLogs,
  fetchSmokeStatus,
  fetchTrafficState,
  setCameraSimulation,
} from "./api";
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
import type {
  ApiConnectionState,
  BackendHealth,
  CameraStatus,
  DetectionFrame,
  RecentLog,
  SmokeStatus,
  TrafficState,
  Zone,
} from "./types";

export default function App() {
  const [frame, setFrame] = useState<DetectionFrame | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [traffic, setTraffic] = useState<TrafficState | null>(null);
  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [smokeStatus, setSmokeStatus] = useState<SmokeStatus | null>(null);
  const [recentLogs, setRecentLogs] = useState<RecentLog[]>([]);
  const [cameraStatus, setCameraStatus] = useState<CameraStatus | null>(null);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.1);
  const [liveDetectionCount, setLiveDetectionCount] = useState(0);
  const [activePage, setActivePage] = useState<AppPageId>("dashboard");
  const [apiState, setApiState] = useState<ApiConnectionState>({
    status: "checking",
    message: "Checking backend connection...",
  });
  const [refreshing, setRefreshing] = useState(false);
  const [changingCameraMode, setChangingCameraMode] = useState(false);

  const refreshAll = useCallback(async () => {
    setRefreshing(true);
    setApiState({ status: "checking", message: "Refreshing API data..." });

    try {
      const [nextHealth, nextSmoke, nextFrame, nextZones, nextTraffic, nextLogs, nextCameraStatus] = await Promise.all([
        fetchHealth(),
        fetchSmokeStatus(),
        fetchMockFrame(),
        fetchMockZones(),
        fetchTrafficState(),
        fetchRecentLogs(),
        fetchCameraStatus(),
      ]);

      setHealth(nextHealth);
      setSmokeStatus(nextSmoke);
      setFrame(nextFrame);
      setZones(nextZones);
      setTraffic(nextTraffic);
      setRecentLogs(nextLogs);
      setCameraStatus(nextCameraStatus);

      const fallbackMode = nextHealth.mode.includes("fallback") || nextSmoke.mode.includes("fallback");
      setApiState({
        status: fallbackMode ? "fallback" : "connected",
        message: fallbackMode
          ? "Backend not connected. Frontend fallback mock data is active."
          : "Backend connected. API data loaded successfully.",
        checkedAt: new Date().toLocaleTimeString(),
      });
    } catch (error) {
      setApiState({
        status: "failed",
        message: error instanceof Error ? error.message : "Unknown refresh failure.",
        checkedAt: new Date().toLocaleTimeString(),
      });
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void refreshAll();
  }, [refreshAll]);

  useEffect(() => {
    if (!["camera_sources", "dataset_capture", "live_ai"].includes(activePage)) return undefined;

    const refreshCamera = async () => setCameraStatus(await fetchCameraStatus());
    void refreshCamera();
    const timerId = window.setInterval(() => void refreshCamera(), activePage === "live_ai" ? 500 : 1000);
    return () => window.clearInterval(timerId);
  }, [activePage]);

  const changeCameraSimulation = useCallback(async (enabled: boolean) => {
    setChangingCameraMode(true);
    try {
      setCameraStatus(await setCameraSimulation(enabled));
    } finally {
      setChangingCameraMode(false);
    }
  }, []);

  const filteredDetections = useMemo(() => {
    if (!frame) return [];
    return frame.detections.filter((detection) => detection.confidence >= confidenceThreshold);
  }, [frame, confidenceThreshold]);

  function renderPage() {
    switch (activePage) {
      case "dashboard":
        return (
          <DashboardPage
            health={health}
            smokeStatus={smokeStatus}
            apiState={apiState}
            onRefresh={refreshAll}
            refreshing={refreshing}
          />
        );
      case "live_ai":
        return (
          <LiveAiPage
            mockFrame={frame}
            zones={zones}
            traffic={traffic}
            mockDetections={filteredDetections}
            cameraStatus={cameraStatus}
            confidenceThreshold={confidenceThreshold}
            onConfidenceChange={setConfidenceThreshold}
            onRefresh={refreshAll}
            refreshing={refreshing}
            onDetectionCountChange={setLiveDetectionCount}
          />
        );
      case "camera_sources":
        return (
          <CameraSourcesPage
            status={cameraStatus}
            onSimulationChange={changeCameraSimulation}
            changingMode={changingCameraMode}
          />
        );
      case "zone_editor":
        return <ZoneEditorPage />;
      case "traffic_logic":
        return <TrafficLogicPage traffic={traffic} smokeStatus={smokeStatus} />;
      case "dataset_capture":
        return <DatasetCapturePage cameraStatus={cameraStatus} />;
      case "dataset_review":
        return <DatasetReviewPage />;
      case "train_export":
        return <TrainExportPage />;
      case "model_registry":
        return <ModelRegistryPage />;
      case "settings":
        return <SettingsPage apiState={apiState} health={health} />;
      case "logs":
        return <LogsPage logs={recentLogs} apiState={apiState} onRefresh={refreshAll} refreshing={refreshing} />;
      default:
        return <DashboardPage health={health} smokeStatus={smokeStatus} apiState={apiState} onRefresh={refreshAll} refreshing={refreshing} />;
    }
  }

  const statusBarDetectionCount = activePage === "live_ai" ? liveDetectionCount : filteredDetections.length;

  return (
    <>
      <AppShell activePage={activePage} onPageChange={setActivePage}>{renderPage()}</AppShell>
      <AppStatusBar apiState={apiState} detectionCount={statusBarDetectionCount} />
    </>
  );
}
