type Metric = {
  label: string;
  value: string | number;
  note?: string;
};

type Props = {
  metrics: Metric[];
};

export function MetricStrip({ metrics }: Props) {
  return (
    <div className="metric-strip">
      {metrics.map((metric) => (
        <div className="metric-card" key={metric.label}>
          <span>{metric.label}</span>
          <strong>{metric.value}</strong>
          {metric.note && <em>{metric.note}</em>}
        </div>
      ))}
    </div>
  );
}
