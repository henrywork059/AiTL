# Component Contracts

## DetectionViewer

Inputs:

- image/frame size
- detections in original image coordinates
- zones in original image coordinates
- confidence threshold
- selected classes

Responsibilities:

- Convert original image coordinates to display coordinates.
- Draw boxes.
- Draw zones.
- Show class labels and confidence.

## TrafficLightSimulator

Inputs:

- traffic state
- phase
- next decision
- extension seconds

Responsibilities:

- Display signal phase.
- Display traffic-light lamps.
- Display next decision.

## ZoneEditor future behavior

Inputs:

- image size
- current zones

Outputs:

- updated zone JSON

The initial skeleton does not implement the zone editor.
