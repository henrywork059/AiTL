import { FunctionChecklist } from "../components/FunctionChecklist";
import { PlaceholderPanel } from "../components/PlaceholderPanel";

export function ModelRegistryPage() {
  return (
    <div className="page-stack">
      <PlaceholderPanel
        title="Model registry template"
        description="This page will compare model versions and deployment readiness."
        bullets={[
            "Model list",
            "Class list",
            "Metrics summary",
            "Export status",
            "Active model selection"
        ]}
      />
      <FunctionChecklist area="Model" />
    </div>
  );
}
