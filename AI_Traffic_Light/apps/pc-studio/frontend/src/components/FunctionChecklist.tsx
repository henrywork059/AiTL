import { FUNCTION_REGISTRY } from "../constants/functionRegistry";
import type { FunctionItem } from "../types/app";

type Props = {
  area?: string;
  limit?: number;
};

function statusText(item: FunctionItem) {
  if (item.status === "implemented") return "available";
  if (item.status === "later") return "later";
  if (item.status === "planned") return "planned";
  return "placeholder";
}

export function FunctionChecklist({ area, limit }: Props) {
  const items = FUNCTION_REGISTRY.filter((item) => !area || item.area === area).slice(0, limit ?? undefined);

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>{area ? `${area} capabilities` : "Prototype capabilities"}</h2>
          <p className="placeholder-copy">Current implementation status for this area.</p>
        </div>
        <span className="status-pill muted">{items.length} items</span>
      </div>
      <div className="function-list">
        {items.map((item) => (
          <article className="function-item" key={item.id}>
            <div>
              <strong>{item.label}</strong>
              <p>{item.description}</p>
              <code>{item.id}</code>
            </div>
            <span className={`status-pill status-${item.status}`}>{statusText(item)}</span>
          </article>
        ))}
      </div>
    </section>
  );
}
