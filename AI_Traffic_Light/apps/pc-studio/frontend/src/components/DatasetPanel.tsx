export function DatasetPanel() {
  return (
    <div className="empty-state">
      <h3>Dataset capture placeholder</h3>
      <p>
        Later this page will save raw frames, detection JSON, and labels for training.
      </p>
      <div className="placeholder-list">
        <span>Save frame</span>
        <span>Save detections</span>
        <span>Mark useful / bad</span>
        <span>Export dataset</span>
      </div>
    </div>
  );
}
