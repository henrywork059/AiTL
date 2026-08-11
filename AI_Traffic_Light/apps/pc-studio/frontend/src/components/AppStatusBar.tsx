import { APP_VERSION_LABEL } from "../constants/appNavigation";
import type { ApiConnectionState } from "../types";

type Props = {
  apiState: ApiConnectionState;
  detectionCount: number;
};

export function AppStatusBar({ apiState, detectionCount }: Props) {
  return (
    <footer className="status-bar">
      <span>{APP_VERSION_LABEL}</span>
      <span>API: {apiState.status}</span>
      <span>Visible mock detections: {detectionCount}</span>
      <span>No real camera, AI inference, training, or physical traffic control is active.</span>
    </footer>
  );
}
