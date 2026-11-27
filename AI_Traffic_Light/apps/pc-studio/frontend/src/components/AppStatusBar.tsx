import { APP_VERSION_LABEL } from "../constants/appNavigation";
import type { ApiConnectionState } from "../types";

type Props = {
  apiState: ApiConnectionState;
  detectionCount: number;
  preview: boolean;
};

export function AppStatusBar({ apiState, detectionCount, preview }: Props) {
  return (
    <footer className="status-bar">
      <span>{APP_VERSION_LABEL}</span>
      <span>API: {apiState.status}</span>
      <span>{preview ? "Preview detections" : "Mock detections"}: {detectionCount}</span>
      <span>Public-road signal control unavailable.</span>
    </footer>
  );
}
