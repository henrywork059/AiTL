import { FunctionChecklist } from "../components/FunctionChecklist";
import { PlaceholderPanel } from "../components/PlaceholderPanel";

export function TrafficLogicPage() {
  return (
    <div className="page-stack">
      <PlaceholderPanel
        title="Traffic logic template"
        description="This page will define the rule-based traffic-light decision system."
        bullets={[
            "Minimum/maximum green time",
            "Pedestrian crossing safety extension",
            "Vehicle queue extension",
            "All-red safety interval",
            "Decision explanation log"
        ]}
      />
      <FunctionChecklist area="Traffic logic" />
    </div>
  );
}
