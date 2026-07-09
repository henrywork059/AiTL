type Props = {
  title: string;
  description: string;
  bullets?: string[];
  status?: string;
};

export function PlaceholderPanel({ title, description, bullets = [], status = "template only" }: Props) {
  return (
    <section className="panel placeholder-panel">
      <div className="panel-header">
        <h2>{title}</h2>
        <span className="status-pill muted">{status}</span>
      </div>
      <p className="placeholder-copy">{description}</p>
      {bullets.length > 0 && (
        <ul className="check-list">
          {bullets.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
