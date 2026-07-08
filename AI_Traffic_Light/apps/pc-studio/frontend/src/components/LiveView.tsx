import type { Detection, DetectionFrame, Zone } from "../types";

type Props = {
  frame: DetectionFrame;
  detections: Detection[];
  zones: Zone[];
};

function polygonPoints(zone: Zone): string {
  return zone.polygon.map(([x, y]) => `${x},${y}`).join(" ");
}

export function LiveView({ frame, detections, zones }: Props) {
  return (
    <div className="live-view-wrapper">
      <svg
        className="live-view"
        viewBox={`0 0 ${frame.image_width} ${frame.image_height}`}
        role="img"
        aria-label="Mock traffic detection view"
      >
        <defs>
          <pattern id="road-lines" width="80" height="80" patternUnits="userSpaceOnUse">
            <path d="M 0 40 H 80" className="road-line" />
          </pattern>
        </defs>

        <rect x="0" y="0" width="1280" height="720" className="sky" />
        <rect x="0" y="290" width="1280" height="430" className="road" />
        <rect x="0" y="450" width="1280" height="90" fill="url(#road-lines)" opacity="0.55" />
        <rect x="360" y="360" width="320" height="330" className="crosswalk" />

        {zones.map((zone) => (
          <g key={zone.id}>
            <polygon points={polygonPoints(zone)} className={`zone zone-${zone.type}`} />
            <text x={zone.polygon[0][0] + 10} y={zone.polygon[0][1] + 26} className="zone-label">
              {zone.label}
            </text>
          </g>
        ))}

        {detections.map((det) => {
          const [x1, y1, x2, y2] = det.box_xyxy;
          return (
            <g key={det.id}>
              <rect
                x={x1}
                y={y1}
                width={x2 - x1}
                height={y2 - y1}
                className={`box box-${det.class_name}`}
              />
              <rect x={x1} y={Math.max(0, y1 - 30)} width="170" height="28" className="box-label-bg" />
              <text x={x1 + 8} y={Math.max(20, y1 - 10)} className="box-label">
                {det.class_name} {(det.confidence * 100).toFixed(0)}%
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
