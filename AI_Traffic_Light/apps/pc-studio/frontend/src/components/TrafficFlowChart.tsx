import { useMemo } from "react";
import type { TrafficFlowBucket } from "../types";

type Props = {
  buckets: TrafficFlowBucket[];
  series?: "passages" | "regions";
};

const WIDTH = 900;
const HEIGHT = 280;
const PAD_LEFT = 48;
const PAD_RIGHT = 20;
const PAD_TOP = 18;
const PAD_BOTTOM = 42;

function timeLabel(timestampMs: number): string {
  return new Date(timestampMs).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function TrafficFlowChart({ buckets, series = "passages" }: Props) {
  const chart = useMemo(() => {
    const valuesFor = (bucket: TrafficFlowBucket) => series === "regions"
      ? [bucket.region_entries, bucket.region_exits]
      : [bucket.vehicles, bucket.pedestrians];
    const maxValue = Math.max(1, ...buckets.flatMap(valuesFor));
    const plotWidth = WIDTH - PAD_LEFT - PAD_RIGHT;
    const plotHeight = HEIGHT - PAD_TOP - PAD_BOTTOM;
    const firstTimestamp = buckets[0]?.bucket_start_ms ?? 0;
    const lastTimestamp = buckets[buckets.length - 1]?.bucket_start_ms ?? firstTimestamp;
    const timestampSpan = lastTimestamp - firstTimestamp;
    const xForTimestamp = (timestampMs: number) => timestampSpan <= 0
      ? PAD_LEFT + plotWidth / 2
      : PAD_LEFT + ((timestampMs - firstTimestamp) / timestampSpan) * plotWidth;
    const yFor = (value: number) => PAD_TOP + plotHeight - (value / maxValue) * plotHeight;
    return {
      maxValue,
      plotHeight,
      xForTimestamp,
      firstPoints: buckets.map((bucket) => `${xForTimestamp(bucket.bucket_start_ms)},${yFor(series === "regions" ? bucket.region_entries : bucket.vehicles)}`).join(" "),
      secondPoints: buckets.map((bucket) => `${xForTimestamp(bucket.bucket_start_ms)},${yFor(series === "regions" ? bucket.region_exits : bucket.pedestrians)}`).join(" "),
    };
  }, [buckets, series]);

  if (buckets.length === 0) {
    return <div className="traffic-chart-empty">{series === "regions" ? "No tracked region events in this time window yet." : "No tracked line-crossing events in this time window yet."}</div>;
  }

  const tickIndexes = Array.from(new Set([0, Math.floor((buckets.length - 1) / 2), buckets.length - 1]));

  return (
    <div className="traffic-chart-wrap">
      <svg className="traffic-history-chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={series === "regions" ? "Tracked region entries and exits per minute" : "Unique tracked vehicle and pedestrian passages per minute"}>
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
          const bucket = buckets[index];
          const x = chart.xForTimestamp(bucket.bucket_start_ms);
          return <text key={index} x={x} y={HEIGHT - 14} textAnchor="middle" className="traffic-chart-label">{timeLabel(bucket.bucket_start_ms)}</text>;
        })}
        <polyline points={chart.firstPoints} className="traffic-chart-line traffic-chart-vehicles" />
        <polyline points={chart.secondPoints} className="traffic-chart-line traffic-chart-pedestrians" />
      </svg>
      <div className="traffic-chart-legend">
        <span><i className="traffic-legend-line traffic-legend-vehicles" />{series === "regions" ? "Region entries/min" : "Unique vehicle passages/min"}</span>
        <span><i className="traffic-legend-line traffic-legend-pedestrians" />{series === "regions" ? "Region exits/min" : "Unique pedestrian passages/min"}</span>
      </div>
    </div>
  );
}
