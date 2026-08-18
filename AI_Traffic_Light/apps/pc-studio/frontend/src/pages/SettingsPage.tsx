import { useEffect, useState } from "react";
import { API_BASE, fetchRuntimeSettings, saveRuntimeSettings } from "../api";
import { FunctionChecklist } from "../components/FunctionChecklist";
import type { ApiConnectionState, BackendHealth, RuntimeSettings } from "../types";
import "./settingsPage.css";

type Props = {
  apiState: ApiConnectionState;
  health: BackendHealth | null;
  settings: RuntimeSettings;
  onSettingsChange: (settings: RuntimeSettings) => void;
};

export function SettingsPage({ apiState, health, settings, onSettingsChange }: Props) {
  const [draft, setDraft] = useState<RuntimeSettings>(settings);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => setDraft(settings), [settings]);

  useEffect(() => {
    void fetchRuntimeSettings().then((next) => {
      setDraft(next);
      onSettingsChange(next);
    }).catch(() => undefined);
  }, [onSettingsChange]);

  async function save() {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const next = await saveRuntimeSettings(draft);
      setDraft(next);
      onSettingsChange(next);
      setMessage("Settings saved and applied.");
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Settings could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page-stack">
      <div className="two-column-grid">
        <section className="panel training-form">
          <div className="panel-header">
            <div>
              <h2>Runtime defaults</h2>
              <p className="placeholder-copy">These values are stored by the backend and reused after restart.</p>
            </div>
            <span className="status-pill status-info">persistent</span>
          </div>
          <div className="form-grid">
            <label>Default inference confidence
              <input
                type="number"
                min={0.01}
                max={1}
                step={0.01}
                value={draft.default_confidence}
                onChange={(event) => setDraft({ ...draft, default_confidence: Number(event.target.value) })}
              />
            </label>
            <label>Camera status refresh interval (ms)
              <input
                type="number"
                min={250}
                max={5000}
                step={50}
                value={draft.live_poll_interval_ms}
                onChange={(event) => setDraft({ ...draft, live_poll_interval_ms: Number(event.target.value) })}
              />
            </label>
            <label>Training early-stop patience
              <input
                type="number"
                min={1}
                max={100}
                value={draft.training_patience}
                onChange={(event) => setDraft({ ...draft, training_patience: Number(event.target.value) })}
              />
            </label>
            <label>Backend logging level
              <select value={draft.log_level} onChange={(event) => setDraft({ ...draft, log_level: event.target.value as RuntimeSettings["log_level"] })}>
                <option value="DEBUG">DEBUG — diagnostic detail</option>
                <option value="INFO">INFO — normal operation</option>
                <option value="WARNING">WARNING — warnings and errors</option>
                <option value="ERROR">ERROR — errors only</option>
              </select>
            </label>
          </div>
          <p className="small-note">Confidence affects the default detection threshold. The camera refresh interval controls status polling, not model inference speed.</p>
          <button className="primary" type="button" onClick={() => void save()} disabled={saving}>{saving ? "Saving..." : "Save settings"}</button>
          {message && <p className="success-message">{message}</p>}
          {error && <p className="error-message">{error}</p>}
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Applied environment</h2>
              <p className="placeholder-copy">Current connection and backend values in use by this session.</p>
            </div>
            <span className="status-pill muted">local</span>
          </div>
          <div className="settings-list">
            <div><span>API base</span><code>{API_BASE}</code></div>
            <div><span>Connection</span><code>{apiState.status}</code></div>
            <div><span>Backend version</span><code>{health?.version ?? "not connected"}</code></div>
            <div><span>Safe mode</span><code>{String(health?.safe_mode ?? true)}</code></div>
            <div><span>Inference confidence</span><code>{Math.round(settings.default_confidence * 100)}%</code></div>
            <div><span>Camera refresh</span><code>{settings.live_poll_interval_ms} ms</code></div>
          </div>
          <p className="small-note">The API base URL remains a Vite environment/build setting. This page changes only backend-persisted runtime defaults.</p>
        </section>
      </div>
      <FunctionChecklist area="Debug" />
    </div>
  );
}
