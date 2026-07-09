import { FunctionChecklist } from "../components/FunctionChecklist";
import { MetricStrip } from "../components/MetricStrip";
import { PlaceholderPanel } from "../components/PlaceholderPanel";

export function DashboardPage() {
  return (
    <div className="page-stack">
      <MetricStrip
        metrics={[
          { label: "Project stage", value: "0_0_4", note: "layout template" },
          { label: "Main pages", value: 11, note: "to confirm" },
          { label: "Real AI", value: "off", note: "placeholder" },
          { label: "Traffic control", value: "sim only", note: "safe mode" },
        ]}
      />
      <div className="two-column-grid">
        <PlaceholderPanel
          title="Current goal"
          description="Confirm the planned PC Studio app pages, function boundaries, and GUI layout before implementing real object detection or camera streaming."
          bullets={[
            "Keep the app modular and easy to debug.",
            "Use fake/mock data until the layout is confirmed.",
            "Do not connect to real traffic-light control.",
          ]}
        />
        <PlaceholderPanel
          title="Next implementation order"
          description="After this layout is accepted, implement one function at a time."
          bullets={[
            "camera/video source preview",
            "pretrained detection on one frame",
            "zone-based counting",
            "traffic-light simulation",
          ]}
        />
      </div>
      <FunctionChecklist limit={8} />
    </div>
  );
}
