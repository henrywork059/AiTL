import { FunctionChecklist } from "../components/FunctionChecklist";
import { PlaceholderPanel } from "../components/PlaceholderPanel";

export function CameraSourcesPage() {
  return (
    <div className="page-stack">
      <PlaceholderPanel
        title="Camera source template"
        description="This page will manage webcam, video-file, ESP-CAM MJPEG, and future IP-camera inputs."
        bullets={[
            "Add/edit source cards",
            "Preview selected source",
            "Show FPS, resolution, latency, and connection state"
        ]}
      />
      <FunctionChecklist area="Camera" />
    </div>
  );
}
