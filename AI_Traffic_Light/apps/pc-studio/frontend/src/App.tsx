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
import { useSerialPolling } from "./lib/useSerialPolling";
import { CameraDiagnosticsPage } from "./pages/CameraDiagnosticsPage";
import { CameraSettingsPage, CameraSourcesPage } from "./pages/CameraSourcesPage";
import { CrosswalksPage } from "./pages/CrosswalksPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DatasetCapturePage } from "./pages/DatasetCapturePage";
import { DatasetReviewPage } from "./pages/DatasetReviewPage";
import { JunctionNetworkPage } from "./pages/JunctionNetworkPage";
import { LiveAiPage } from "./pages/LiveAiPage";
import { LogsPage } from "./pages/LogsPage";
import { ModelRegistryPage } from "./pages/ModelRegistryPage";
import { SimulationLabPage } from "./pages/SimulationLabPage";
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

const CAMERA_POLL_PAGES: AppPageId[] = ["camera_sources", "camera_settings", "crosswalks", "junction_network", "dataset_capture", "zone_editor", "live_ai"];

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
  const [showSimulationTools, setShowSimulationTools] = useState(false);
  const [apiState, setApiState] = useState<ApiConnectionState>({
    status: "checking",
    message: "Checking backend connection...",
  });
  const [refreshing, setRefreshing] = useState(false);
  const [changingCameraMode, setChangingCameraMode] = useState(false);
  const runtimeInitialized = useRef(false);
  const refreshInFlightRef = useRef<Promise<void> | null>(null);
  const cameraModeGenerationRef = useRef(0);

  const refreshAllOnce = useCallback(async () => {
    const cameraModeGeneration = cameraModeGenerationRef.current;
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
      if (cameraModeGeneration === cameraModeGenerationRef.current) {
        setCameraStatus(nextCameraStatus);
      }
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

  // Keep one manual/startup refresh in flight across repeated clicks and StrictMode effects.
  const refreshAll = useCallback((): Promise<void> => {
    if (refreshInFlightRef.current) return refreshInFlightRef.current;
    const pending = refreshAllOnce().finally(() => {
      if (refreshInFlightRef.current === pending) refreshInFlightRef.current = null;
    });
    refreshInFlightRef.current = pending;
    return pending;
  }, [refreshAllOnce]);

  useEffect(() => {
    void refreshAll();
  }, [refreshAll]);

  const pollCameraStatus = useCallback(async () => {
    const generation = cameraModeGenerationRef.current;
    const status = await fetchCameraStatus();
    if (generation === cameraModeGenerationRef.current) setCameraStatus(status);
  }, []);

  const pollLiveContext = useCallback(async () => {
    const [nextTraffic, nextZones] = await Promise.all([fetchTrafficState(), fetchActiveZones()]);
    setTraffic(nextTraffic);
    setZones(nextZones.zones);
  }, []);

  const { waitForIdle: waitForCameraStatusIdle } = useSerialPolling(
    pollCameraStatus,
    activePage === "live_ai" ? runtimeSettings.live_poll_interval_ms : 1000,
    { enabled: CAMERA_POLL_PAGES.includes(activePage) && !changingCameraMode, immediate: true },
  );

  useSerialPolling(
    pollLiveContext,
    1000,
    { enabled: activePage === "live_ai", immediate: true },
  );

  const changeCameraSimulation = useCallback(async (enabled: boolean) => {
    cameraModeGenerationRef.current += 1;
    setChangingCameraMode(true);
    try {
      await waitForCameraStatusIdle();
      setCameraStatus(await setCameraSimulation(enabled));
    } finally {
      // Discard any bulk refresh that began before or during the transition.
      cameraModeGenerationRef.current += 1;
      setChangingCameraMode(false);
    }
  }, [waitForCameraStatusIdle]);

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
            zones={zones}
            cameraStatus={cameraStatus}
            onRefresh={refreshAll}
            refreshing={refreshing}
            onDetectionCountChange={setLiveDetectionCount}
          />
        );
      case "camera_sources":
        return (
          <CameraSourcesPage
            showSimulationTools={showSimulationTools}
            status={cameraStatus}
            onSimulationChange={changeCameraSimulation}
            onStatusChange={setCameraStatus}
            changingMode={changingCameraMode}
          />
        );
      case "camera_settings":
        return (
          <CameraSettingsPage
            showSimulationTools={showSimulationTools}
            status={cameraStatus}
            onSimulationChange={changeCameraSimulation}
            onStatusChange={setCameraStatus}
            changingMode={changingCameraMode}
          />
        );
      case "camera_diagnostics":
        return <CameraDiagnosticsPage />;
      case "junction_network":
        return (
          <JunctionNetworkPage
            showSimulationTools={showSimulationTools}
            cameraStatus={cameraStatus}
            changingMode={changingCameraMode}
            onSimulationChange={changeCameraSimulation}
          />
        );
      case "crosswalks":
        return (
          <CrosswalksPage
            showSimulationTools={showSimulationTools}
            cameraStatus={cameraStatus}
            changingMode={changingCameraMode}
            onSimulationChange={changeCameraSimulation}
            onCameraStatusChange={setCameraStatus}
          />
        );
      case "zone_editor":
        return <ZoneEditorPage cameraStatus={cameraStatus} />;
      case "traffic_logic":
        return <TrafficLogicPage />;
      case "traffic_analytics":
        return <TrafficAnalyticsPage />;
      case "simulation_lab":
        return showSimulationTools ? <SimulationLabPage /> : null;
      case "dataset_capture":
        return <DatasetCapturePage cameraStatus={cameraStatus} />;
      case "dataset_review":
        return <DatasetReviewPage />;
      case "train_export":
        return <TrainExportPage />;
      case "model_registry":
        return <ModelRegistryPage runtimeSettings={runtimeSettings} onSettingsChange={applyRuntimeSettings} />;
      case "logs":
        return <LogsPage logs={recentLogs} apiState={apiState} onLogsChange={setRecentLogs} />;
      default:
        return <DashboardPage health={health} smokeStatus={smokeStatus} apiState={apiState} onRefresh={refreshAll} refreshing={refreshing} />;
    }
  }

  const toggleSimulationTools = () => {
    if (showSimulationTools && activePage === "simulation_lab") setActivePage("dashboard");
    setShowSimulationTools((current) => !current);
  };

  const statusBarDetectionCount = activePage === "live_ai" ? liveDetectionCount : filteredDetections.length;

  return (
    <>
      <AppShell activePage={activePage} onPageChange={setActivePage} showSimulationTools={showSimulationTools} onSimulationToolsToggle={toggleSimulationTools}>{renderPage()}</AppShell>
      <AppStatusBar apiState={apiState} detectionCount={statusBarDetectionCount} />
    </>
  );
}
