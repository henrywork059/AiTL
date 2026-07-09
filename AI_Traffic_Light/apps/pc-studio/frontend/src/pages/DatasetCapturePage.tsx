import { FunctionChecklist } from "../components/FunctionChecklist";
import { PlaceholderPanel } from "../components/PlaceholderPanel";

export function DatasetCapturePage() {
  return (
    <div className="page-stack">
      <PlaceholderPanel
        title="Dataset capture template"
        description="This page will save frames, predictions, labels, and frame-quality notes."
        bullets={[
            "Manual capture",
            "Timed capture",
            "Save raw frame + metadata",
            "Tag useful/bad frame",
            "Export capture session"
        ]}
      />
      <FunctionChecklist area="Dataset" />
    </div>
  );
}
