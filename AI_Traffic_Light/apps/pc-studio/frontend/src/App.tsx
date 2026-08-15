import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  fallbackRuntimeSettings,
  fetchActiveZones,
  fetchHealth,
  fetchCameraStatus,
  fetchMockFrame,
  fetchRecentLogs,
  fetchRuntimeSettings,
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
import { TrafficAnalyticsPage } from "./pages/TrafficAnalyticsPage";
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
  RuntimeSettings,
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
  const [runtimeSettings, setRuntimeSettings] = useState<RuntimeSettings>(fallbackRuntimeSettings);
  const [confidenceThreshold, setConfidenceThreshold] = useState(fallbackRuntimeSettings.default_confidence);
  const [liveDetectionCount, setLiveDetectionCount] = useState(0);
  const [activePage, setActivePage] = useState<AppPageId>("dashboard");
  const [apiState, setApiState] = useState<ApiConnectionState>({
    status: "checking",
    message: "Checking backend connection...",
  });
  const [refreshing, setRefreshing] = useState(false);
  const [changingCameraMode, setChangingCameraMode] = useState(false);
  const runtimeInitialized = useRef(false);

  const refreshAll = useCallback(async () => {
    setRefreshing(true);
    setApiState({ status: "checking", message: "Refreshing API data..." });

    try {
      const [nextHealth, nextSmoke, nextFrame, nextZoneStatus, nextTraffic, nextLogs, nextCameraStatus, nextSettings] = await Promise.all([
        fetchHealth(),
        fetchSmokeStatus(),
        fetchMockFrame(),
        fetchActiveZones(),
        fetchTrafficState(),
        fetchRecentLogs(),
        fetchCameraStatus(),
        fetchRuntimeSettings(),
      ]);

      setHealth(nextHealth);
      setSmokeStatus(nextSmoke);
      setFrame(nextFrame);
      setZones(nextZoneStatus.zones);
      setTraffic(nextTraffic);
      setRecentLogs(nextLogs);
      setCameraStatus(nextCameraStatus);
      setRuntimeSettings(nextSettings);
      if (!runtimeInitialized.current) {
        runtimeInitialized.current = true;
        setConfidenceThreshold(nextSettings.default_confidence);
      }

      const fallbackMode = nextHealth.mode.includes("fallback") || nextSmoke.mode.includes("fallback");
      setApiState({
        status: fallbackMode ? "fallback" : "connected",
        message: fallbackMode
          ? "Backend not connected. Frontend fallback data is active."
          : "Backend connected. Live prototype APIs loaded successfully.",
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
    if (!["camera_sources", "dataset_capture", "zone_editor", "live_ai"].includes(activePage)) return undefined;

    const refreshCamera = async () => setCameraStatus(await fetchCameraStatus());
    void refreshCamera();
    const timerId = window.setInterval(
      () => void refreshCamera(),
      activePage === "live_ai" ? runtimeSettings.live_poll_interval_ms : 1000,
    );
    return () => window.clearInterval(timerId);
  }, [activePage, runtimeSettings.live_poll_interval_ms]);

  useEffect(() => {
    if (activePage !== "live_ai") return undefined;
    const refreshLiveContext = async () => {
      const [nextTraffic, nextZones] = await Promise.all([fetchTrafficState(), fetchActiveZones()]);
      setTraffic(nextTraffic);
      setZones(nextZones.zones);
    };
    void refreshLiveContext();
    const timerId = window.setInterval(() => void refreshLiveContext(), 1000);
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

  const applyRuntimeSettings = useCallback((settings: RuntimeSettings) => {
    setRuntimeSettings(settings);
    setConfidenceThreshold(settings.default_confidence);
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
            onStatusChange={setCameraStatus}
            changingMode={changingCameraMode}
          />
        );
      case "zone_editor":
        return <ZoneEditorPage cameraStatus={cameraStatus} />;
      case "traffic_logic":
        return <TrafficLogicPage />;
      case "traffic_analytics":
        return <TrafficAnalyticsPage />;
      case "dataset_capture":
        return <DatasetCapturePage cameraStatus={cameraStatus} />;
      case "dataset_review":
        return <DatasetReviewPage />;
      case "train_export":
        return <TrainExportPage />;
      case "model_registry":
        return <ModelRegistryPage />;
      case "settings":
        return <SettingsPage apiState={apiState} health={health} settings={runtimeSettings} onSettingsChange={applyRuntimeSettings} />;
      case "logs":
        return <LogsPage logs={recentLogs} apiState={apiState} onLogsChange={setRecentLogs} />;
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
