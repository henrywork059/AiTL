def get_mock_detection_frame() -> dict:
    return {
        "frame_id": "mock_cam_000001",
        "source_id": "mock_camera",
        "image_width": 1280,
        "image_height": 720,
        "timestamp_ms": 0,
        "detections": [
            {
                "id": "det_person_001",
                "class_id": 0,
                "class_name": "person",
                "confidence": 0.93,
                "box_xyxy": [130, 390, 215, 650],
            },
            {
                "id": "det_person_002",
                "class_id": 0,
                "class_name": "person",
                "confidence": 0.88,
                "box_xyxy": [245, 410, 315, 660],
            },
            {
                "id": "det_car_001",
                "class_id": 1,
                "class_name": "car",
                "confidence": 0.91,
                "box_xyxy": [700, 360, 900, 500],
            },
            {
                "id": "det_bus_001",
                "class_id": 2,
                "class_name": "bus",
                "confidence": 0.84,
                "box_xyxy": [920, 310, 1210, 520],
            },
        ],
    }


def get_mock_zones() -> list[dict]:
    return [
        {
            "id": "ped_waiting_left",
            "type": "pedestrian_waiting",
            "label": "Pedestrian Waiting Zone",
            "polygon": [[70, 380], [360, 380], [360, 690], [70, 690]],
        },
        {
            "id": "crossing_main",
            "type": "crossing",
            "label": "Crossing Zone",
            "polygon": [[360, 360], [680, 360], [680, 690], [360, 690]],
        },
        {
            "id": "vehicle_queue_right",
            "type": "vehicle_queue",
            "label": "Vehicle Queue Zone",
            "polygon": [[680, 300], [1240, 300], [1240, 560], [680, 560]],
        },
    ]
