import { FunctionChecklist } from "../components/FunctionChecklist";
import { PlaceholderPanel } from "../components/PlaceholderPanel";

export function SettingsPage() {
  return (
    <div className="page-stack">
      <PlaceholderPanel
        title="Settings template"
        description="This page will control project paths, API endpoints, debug mode, and app preferences."
        bullets={[
            "API base URL",
            "Dataset path",
            "Model path",
            "Debug logging",
            "Viewer preferences"
        ]}
      />
      <FunctionChecklist area="Debug" />
    </div>
  );
}
