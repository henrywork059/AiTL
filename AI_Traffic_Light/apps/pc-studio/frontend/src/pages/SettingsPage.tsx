import { API_BASE } from "../api";
import { FunctionChecklist } from "../components/FunctionChecklist";
import { PlaceholderPanel } from "../components/PlaceholderPanel";
import type { ApiConnectionState, BackendHealth } from "../types";

type Props = {
  apiState: ApiConnectionState;
  health: BackendHealth | null;
};

export function SettingsPage({ apiState, health }: Props) {
  return (
    <div className="page-stack">
      <div className="two-column-grid">
        <PlaceholderPanel
          title="Runtime settings template"
          description="This page will manage project paths, camera settings, model settings, and debug options."
          bullets={[
            "Project root path",
            "Camera source defaults",
            "AI model path",
            "Dataset output path",
            "Logging level",
            "API base URL",
          ]}
        />
        <section className="panel">
          <div className="panel-header">
            <h2>Current local settings</h2>
            <span className="status-pill muted">read only</span>
          </div>
          <div className="settings-list">
            <div><span>Frontend API base</span><code>{API_BASE}</code></div>
            <div><span>API status</span><code>{apiState.status}</code></div>
            <div><span>Backend version</span><code>{health?.version ?? "not connected"}</code></div>
            <div><span>Safe mode</span><code>{String(health?.safe_mode ?? true)}</code></div>
          </div>
        </section>
      </div>
      <FunctionChecklist area="Debug" />
    </div>
  );
}
