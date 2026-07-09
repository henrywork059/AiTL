import { FunctionChecklist } from "../components/FunctionChecklist";
import { PlaceholderPanel } from "../components/PlaceholderPanel";

export function TrainExportPage() {
  return (
    <div className="page-stack">
      <PlaceholderPanel
        title="Train / export template"
        description="This page will later configure training runs and export deployment packages."
        bullets={[
            "Select dataset",
            "Select base model",
            "Set epochs/image size/batch",
            "View training progress",
            "Export runtime package"
        ]}
      />
      <FunctionChecklist area="Training" />
    </div>
  );
}
