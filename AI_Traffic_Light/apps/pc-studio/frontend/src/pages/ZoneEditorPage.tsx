import { FunctionChecklist } from "../components/FunctionChecklist";
import { PlaceholderPanel } from "../components/PlaceholderPanel";

export function ZoneEditorPage() {
  return (
    <div className="page-stack">
      <PlaceholderPanel
        title="Zone editor template"
        description="This page will draw and edit traffic zones on top of a reference frame."
        bullets={[
            "Pedestrian waiting zones",
            "Crossing zones",
            "Vehicle queue zones",
            "Ignore zones",
            "Save/load zone configuration"
        ]}
      />
      <FunctionChecklist area="Zones" />
    </div>
  );
}
