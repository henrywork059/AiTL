type Props = {
  confidenceThreshold: number;
  onConfidenceChange: (value: number) => void;
  onRefresh: () => void;
  refreshing: boolean;
};

export function ControlsPanel({ confidenceThreshold, onConfidenceChange, onRefresh, refreshing }: Props) {
  return (
    <section className="panel compact-panel">
      <div className="panel-header">
        <h2>Controls</h2>
      </div>
      <label className="control-label">
        Confidence threshold: {(confidenceThreshold * 100).toFixed(0)}%
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={confidenceThreshold}
          onChange={(event) => onConfidenceChange(Number(event.target.value))}
        />
      </label>
      <div className="button-row">
        <button onClick={onRefresh} disabled={refreshing}>{refreshing ? "Refreshing..." : "Reload mock data"}</button>
        <button disabled>Capture frame</button>
      </div>
      <p className="small-note">Reload is active. Capture is a placeholder until dataset saving is implemented.</p>
    </section>
  );
}
