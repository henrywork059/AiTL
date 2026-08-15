import { API_BASE, inferredFrameUrl } from "../api";
import type { CameraStatus, Detection, DetectionFrame, Zone } from "../types";

type Props = {
  cameraStatus: CameraStatus | null;
  frame: DetectionFrame | null;
  detections: Detection[];
  zones: Zone[];
  showBoxes: boolean;
  showLabels: boolean;
  showZones: boolean;
};

const ZONE_REFERENCE_WIDTH = 1280;
const ZONE_REFERENCE_HEIGHT = 720;

function scaledZonePoints(zone: Zone, width: number, height: number): string {
  const scaleX = width / ZONE_REFERENCE_WIDTH;
  const scaleY = height / ZONE_REFERENCE_HEIGHT;
  return zone.polygon.map(([x, y]) => `${x * scaleX},${y * scaleY}`).join(" ");
}

export function CameraDetectionView({
  cameraStatus,
  frame,
  detections,
  zones,
  showBoxes,
  showLabels,
  showZones,
}: Props) {
  if (!cameraStatus?.frame_available) {
    return (
      <div className="live-camera-empty">
        <strong>No camera frame available</strong>
        <span>Upload a JPEG/PNG in Cameras or start simulation mode.</span>
      </div>
    );
  }

  const width = frame?.image_width ?? cameraStatus.resolution?.width ?? 1280;
  const height = frame?.image_height ?? cameraStatus.resolution?.height ?? 720;
  const imageUrl = frame?.source_frame_number
    ? inferredFrameUrl(frame.source_id, frame.source_frame_number, frame.timestamp_ms)
    : `${API_BASE}/api/camera/frame?t=${cameraStatus.frame_number}`;

  const shouldRenderOverlay = (showZones && zones.length > 0) || (frame !== null && showBoxes);

  return (
    <div className="live-camera-stage" style={{ aspectRatio: `${width} / ${height}` }}>
      <img
        className="live-camera-image"
        src={imageUrl}
        alt="Current camera frame"
      />
      {shouldRenderOverlay && (
        <svg
          className="live-detection-overlay"
          viewBox={`0 0 ${width} ${height}`}
          preserveAspectRatio="xMidYMid meet"
          aria-label="Live object detection and configured zone overlay"
        >
          {showZones && zones.map((zone) => (
            <g key={zone.id} className="live-zone-group">
              <polygon
                points={scaledZonePoints(zone, width, height)}
                className={`live-zone-polygon live-zone-${zone.type}`}
              />
              {zone.polygon[0] && (
                <text
                  className="live-zone-label"
                  x={zone.polygon[0][0] * (width / ZONE_REFERENCE_WIDTH) + 8}
                  y={zone.polygon[0][1] * (height / ZONE_REFERENCE_HEIGHT) + 22}
                >
                  {zone.label}
                </text>
              )}
            </g>
          ))}

          {frame && showBoxes && detections.map((detection) => {
            const [x1, y1, x2, y2] = detection.box_xyxy;
            const labelY = Math.max(22, y1 - 8);
            const labelWidth = Math.max(120, detection.class_name.length * 15 + 70);
            return (
              <g key={detection.id}>
                <rect
                  className={`live-detection-box live-detection-${detection.class_name}`}
                  x={x1}
                  y={y1}
                  width={x2 - x1}
                  height={y2 - y1}
                />
                {showLabels && (
                  <>
                    <rect
                      className="live-detection-label-bg"
                      x={x1}
                      y={Math.max(0, labelY - 24)}
                      width={labelWidth}
                      height={26}
                      rx={5}
                    />
                    <text className="live-detection-label" x={x1 + 7} y={labelY - 5}>
                      {detection.class_name} {(detection.confidence * 100).toFixed(0)}%
                    </text>
                  </>
                )}
              </g>
            );
          })}
        </svg>
      )}
    </div>
  );
}
