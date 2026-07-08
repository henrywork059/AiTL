import { useEffect, useMemo, useState } from "react";
import { fetchMockFrame, fetchMockZones, fetchTrafficState } from "./api";
import { ControlsPanel } from "./components/ControlsPanel";
import { DatasetPanel } from "./components/DatasetPanel";
import { DetectionTable } from "./components/DetectionTable";
import { LiveView } from "./components/LiveView";
import { StatusPanel } from "./components/StatusPanel";
import { TrafficLight } from "./components/TrafficLight";
import { ZonePanel } from "./components/ZonePanel";
import type { DetectionFrame, TrafficState, Zone } from "./types";

export default function App() {
  const [frame, setFrame] = useState<DetectionFrame | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [traffic, setTraffic] = useState<TrafficState | null>(null);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.45);
  const [activePage, setActivePage] = useState("live");

  useEffect(() => {
    void fetchMockFrame().then(setFrame);
    void fetchMockZones().then(setZones);
    void fetchTrafficState().then(setTraffic);
  }, []);

  const filteredDetections = useMemo(() => {
    if (!frame) return [];
    return frame.detections.filter((d) => d.confidence >= confidenceThreshold);
  }, [frame, confidenceThreshold]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">Version 1 / 0.1.0 skeleton</div>
          <h1>AI Traffic Light PC Studio</h1>
        </div>
        <nav className="tabs" aria-label="Main pages">
          {[
            ["live", "Live AI"],
            ["capture", "Dataset Capture"],
            ["train", "Train / Export"],
            ["settings", "Settings"],
          ].map(([id, label]) => (
            <button
              key={id}
              className={activePage === id ? "tab active" : "tab"}
              onClick={() => setActivePage(id)}
            >
              {label}
            </button>
          ))}
        </nav>
      </header>

      <main className="main-grid">
        <section className="panel live-panel">
          <div className="panel-header">
            <h2>{activePage === "live" ? "Live detection view" : "Placeholder page"}</h2>
            <span className="status-pill">Mock mode</span>
          </div>
          {activePage === "live" && frame ? (
            <LiveView
              frame={frame}
              detections={filteredDetections}
              zones={zones}
            />
          ) : activePage === "capture" ? (
            <DatasetPanel />
          ) : activePage === "train" ? (
            <div className="empty-state">
              <h3>Training/export placeholder</h3>
              <p>
                Later this page will configure model training, review model versions,
                and export runtime packages.
              </p>
            </div>
          ) : (
            <div className="empty-state">
              <h3>Settings placeholder</h3>
              <p>
                Later this page will manage camera sources, ESP-CAM IP addresses,
                model settings, and zone files.
              </p>
            </div>
          )}
        </section>

        <aside className="side-column">
          {traffic && <TrafficLight traffic={traffic} />}
          {traffic && <StatusPanel traffic={traffic} />}
          <ControlsPanel
            confidenceThreshold={confidenceThreshold}
            onConfidenceChange={setConfidenceThreshold}
          />
          <ZonePanel zones={zones} />
        </aside>
      </main>

      <section className="panel bottom-panel">
        <div className="panel-header">
          <h2>Detections</h2>
          <span>{filteredDetections.length} visible</span>
        </div>
        <DetectionTable detections={filteredDetections} />
      </section>
    </div>
  );
}
