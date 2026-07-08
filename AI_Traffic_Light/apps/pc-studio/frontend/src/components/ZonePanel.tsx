import type { Zone } from "../types";

type Props = {
  zones: Zone[];
};

export function ZonePanel({ zones }: Props) {
  return (
    <section className="panel compact-panel">
      <div className="panel-header">
        <h2>Zones</h2>
      </div>
      <ul className="zone-list">
        {zones.map((zone) => (
          <li key={zone.id}>
            <strong>{zone.label}</strong>
            <span>{zone.type}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
