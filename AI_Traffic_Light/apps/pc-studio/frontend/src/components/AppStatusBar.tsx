import { APP_VERSION_LABEL } from "../constants/appNavigation";

export function AppStatusBar() {
  return (
    <footer className="status-bar">
      <span>{APP_VERSION_LABEL}</span>
      <span>Mode: template/mock only</span>
      <span>No real camera, AI inference, training, or traffic control is active.</span>
    </footer>
  );
}
