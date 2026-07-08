export type Detection = {
  id: string;
  class_id: number;
  class_name: string;
  confidence: number;
  box_xyxy: [number, number, number, number];
};

export type DetectionFrame = {
  frame_id: string;
  source_id: string;
  image_width: number;
  image_height: number;
  timestamp_ms: number;
  detections: Detection[];
};

export type Zone = {
  id: string;
  type: "pedestrian_waiting" | "crossing" | "vehicle_queue" | "ignore" | string;
  label: string;
  polygon: [number, number][];
};

export type TrafficState = {
  phase:
    | "vehicle_green"
    | "vehicle_yellow"
    | "pedestrian_green"
    | "pedestrian_flashing"
    | "all_red";
  pedestrians_waiting: number;
  pedestrians_crossing: number;
  vehicles_waiting: number;
  decision: string;
  decision_reason: string;
  extension_seconds: number;
};
