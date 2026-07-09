import { FunctionChecklist } from "../components/FunctionChecklist";
import { PlaceholderPanel } from "../components/PlaceholderPanel";

export function DatasetReviewPage() {
  return (
    <div className="page-stack">
      <PlaceholderPanel
        title="Dataset review template"
        description="This page will inspect captured frames and prepare data for future training."
        bullets={[
            "Frame browser",
            "Label/prediction comparison",
            "Class distribution",
            "Bad frame filtering",
            "Export dataset split"
        ]}
      />
      <FunctionChecklist area="Dataset" />
    </div>
  );
}
