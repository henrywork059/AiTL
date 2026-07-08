type Props = {
  confidenceThreshold: number;
  onConfidenceChange: (value: number) => void;
};

export function ControlsPanel({ confidenceThreshold, onConfidenceChange }: Props) {
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
        <button>Start mock</button>
        <button>Capture frame</button>
      </div>
      <p className="small-note">Buttons are placeholders in version 1.</p>
    </section>
  );
}
