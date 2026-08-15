import type { DetectionFrame, TrafficState, Zone } from "./types";

// Offline/smoke fallback only. Working pages use live backend APIs when connected.
export const mockFrame: DetectionFrame = {
  frame_id: "fallback_cam_000001",
  source_id: "fallback_camera",
  image_width: 1280,
  image_height: 720,
  timestamp_ms: 0,
  detections: [
    {
      id: "fallback_person_waiting",
      class_id: 0,
      class_name: "person",
      confidence: 0.93,
      box_xyxy: [585, 70, 645, 165],
    },
    {
      id: "fallback_person_crossing",
      class_id: 0,
      class_name: "person",
      confidence: 0.88,
      box_xyxy: [625, 300, 690, 430],
    },
    {
      id: "fallback_car_left",
      class_id: 1,
      class_name: "car",
      confidence: 0.91,
      box_xyxy: [250, 350, 430, 455],
    },
    {
      id: "fallback_bus_right",
      class_id: 2,
      class_name: "bus",
      confidence: 0.84,
      box_xyxy: [860, 430, 1160, 565],
    },
  ],
};

export const mockZones: Zone[] = [
  {
    id: "ped_waiting_top",
    type: "pedestrian_waiting",
    label: "Pedestrian Waiting Zone",
    polygon: [[500, 0], [780, 0], [780, 178], [500, 178]],
  },
  {
    id: "crossing_main",
    type: "crossing",
    label: "Crossing Zone",
    polygon: [[500, 179], [780, 179], [780, 625], [500, 625]],
  },
  {
    id: "vehicle_queue_left",
    type: "vehicle_queue",
    label: "Left Vehicle Queue",
    polygon: [[0, 190], [500, 190], [500, 615], [0, 615]],
  },
  {
    id: "vehicle_queue_right",
    type: "vehicle_queue",
    label: "Right Vehicle Queue",
    polygon: [[780, 190], [1279, 190], [1279, 615], [780, 615]],
  },
];

export const mockTrafficState: TrafficState = {
  phase: "vehicle_yellow",
  pedestrians_waiting: 1,
  pedestrians_crossing: 1,
  vehicles_waiting: 2,
  decision: "fallback_only",
  decision_reason: "Backend is unavailable; this state is only a frontend fallback fixture.",
  extension_seconds: 0,
  data_source: "frontend_fallback",
  evaluated_frame_number: null,
  zone_counts: {
    ped_waiting_top: 1,
    crossing_main: 1,
    vehicle_queue_left: 1,
    vehicle_queue_right: 1,
  },
  prototype_only: true,
};
