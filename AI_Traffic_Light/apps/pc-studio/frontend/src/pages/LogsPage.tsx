import { FunctionChecklist } from "../components/FunctionChecklist";
import { PlaceholderPanel } from "../components/PlaceholderPanel";

export function LogsPage() {
  return (
    <div className="page-stack">
      <PlaceholderPanel
        title="Logs and errors template"
        description="This page will show debug logs, request IDs, and project error codes."
        bullets={[
            "Recent events",
            "Error-code filter",
            "Request ID lookup",
            "Backend/frontend log scopes",
            "Copy debug report"
        ]}
      />
      <FunctionChecklist area="Debug" />
    </div>
  );
}
