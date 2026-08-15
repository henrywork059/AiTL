import { useMemo } from "react";
import type { TrafficHistoryPoint } from "../types";

type Props = {
  points: TrafficHistoryPoint[];
};

const WIDTH = 900;
const HEIGHT = 280;
const PAD_LEFT = 48;
const PAD_RIGHT = 20;
const PAD_TOP = 18;
const PAD_BOTTOM = 42;

function timeLabel(timestampMs: number): string {
  return new Date(timestampMs).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function TrafficHistoryChart({ points }: Props) {
  const chart = useMemo(() => {
    const maxValue = Math.max(1, ...points.flatMap((point) => [point.pedestrians, point.vehicles]));
    const plotWidth = WIDTH - PAD_LEFT - PAD_RIGHT;
    const plotHeight = HEIGHT - PAD_TOP - PAD_BOTTOM;
    const firstTimestamp = points[0]?.recorded_at_ms ?? 0;
    const lastTimestamp = points[points.length - 1]?.recorded_at_ms ?? firstTimestamp;
    const timestampSpan = lastTimestamp - firstTimestamp;
    const xForTimestamp = (timestampMs: number) => timestampSpan <= 0
      ? PAD_LEFT + plotWidth / 2
      : PAD_LEFT + ((timestampMs - firstTimestamp) / timestampSpan) * plotWidth;
    const yFor = (value: number) => PAD_TOP + plotHeight - (value / maxValue) * plotHeight;
    return {
      maxValue,
      plotHeight,
      firstTimestamp,
      lastTimestamp,
      xForTimestamp,
      pedestrianPoints: points.map((point) => `${xForTimestamp(point.recorded_at_ms)},${yFor(point.pedestrians)}`).join(" "),
      vehiclePoints: points.map((point) => `${xForTimestamp(point.recorded_at_ms)},${yFor(point.vehicles)}`).join(" "),
    };
  }, [points]);

  if (points.length === 0) {
    return <div className="traffic-chart-empty">No detection-backed history samples in this time window yet.</div>;
  }

  const tickIndexes = Array.from(new Set([0, Math.floor((points.length - 1) / 2), points.length - 1]));

  return (
    <div className="traffic-chart-wrap">
      <svg className="traffic-history-chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Vehicle and pedestrian occupancy over time">
        <line x1={PAD_LEFT} y1={PAD_TOP} x2={PAD_LEFT} y2={HEIGHT - PAD_BOTTOM} className="traffic-chart-axis" />
        <line x1={PAD_LEFT} y1={HEIGHT - PAD_BOTTOM} x2={WIDTH - PAD_RIGHT} y2={HEIGHT - PAD_BOTTOM} className="traffic-chart-axis" />
        {[0, 0.5, 1].map((ratio) => {
          const y = PAD_TOP + chart.plotHeight - ratio * chart.plotHeight;
          const value = Math.round(chart.maxValue * ratio);
          return (
            <g key={ratio}>
              <line x1={PAD_LEFT} y1={y} x2={WIDTH - PAD_RIGHT} y2={y} className="traffic-chart-grid" />
              <text x={PAD_LEFT - 10} y={y + 4} textAnchor="end" className="traffic-chart-label">{value}</text>
            </g>
          );
        })}
        {tickIndexes.map((index) => {
          const point = points[index];
          const x = chart.xForTimestamp(point.recorded_at_ms);
          return <text key={index} x={x} y={HEIGHT - 14} textAnchor="middle" className="traffic-chart-label">{timeLabel(point.recorded_at_ms)}</text>;
        })}
        <polyline points={chart.vehiclePoints} className="traffic-chart-line traffic-chart-vehicles" />
        <polyline points={chart.pedestrianPoints} className="traffic-chart-line traffic-chart-pedestrians" />
      </svg>
      <div className="traffic-chart-legend">
        <span><i className="traffic-legend-line traffic-legend-vehicles" />Vehicles</span>
        <span><i className="traffic-legend-line traffic-legend-pedestrians" />Pedestrians</span>
      </div>
    </div>
  );
}
