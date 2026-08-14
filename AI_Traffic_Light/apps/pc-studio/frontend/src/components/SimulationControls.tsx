import { useState, type ChangeEvent } from "react";
import { setCameraSimulationSettings } from "../api";
import type { CameraStatus, SimulationDensity } from "../types";
import "./simulationControls.css";

type Props = {
  status: CameraStatus | null;
  onStatusChange: (status: CameraStatus) => void;
};

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Simulation setting update failed.";
}

export function SimulationControls({ status, onStatusChange }: Props) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function updateSettings(input: { density?: SimulationDensity; paused?: boolean }) {
    setSaving(true);
    setError(null);
    try {
      onStatusChange(await setCameraSimulationSettings(input));
    } catch (nextError) {
      setError(errorMessage(nextError));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="simulation-controls">
      <div className="simulation-control-grid">
        <label>
          Scene density
          <select
            value={status?.simulation_density ?? "normal"}
            onChange={(event: ChangeEvent<HTMLSelectElement>) => void updateSettings({ density: event.target.value as SimulationDensity })}
            disabled={saving || !status}
          >
            <option value="light">Light</option>
            <option value="normal">Normal</option>
            <option value="busy">Busy</option>
          </select>
        </label>
        <button
          onClick={() => void updateSettings({ paused: !status?.simulation_paused })}
          disabled={saving || !status?.simulation_enabled}
          title={status?.simulation_enabled ? "Freeze or resume the current synthetic scene." : "Start simulation mode first."}
        >
          {saving
            ? "Updating..."
            : status?.simulation_paused
              ? "Resume scene"
              : "Pause scene"}
        </button>
      </div>
      <p className="small-note">
        Density changes the synthetic pedestrian/vehicle population. Pause freezes one frame for inspection or capture.
      </p>
      {error && <p className="error-message">{error}</p>}
    </div>
  );
}
