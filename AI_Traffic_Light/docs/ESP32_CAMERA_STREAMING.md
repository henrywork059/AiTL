# ESP32-CAM integration

## Recommended V032 path

Use the stock Arduino ESP32 CameraWebServer example as the first hardware baseline.

The ESP32-CAM needs only its Wi-Fi credentials. It does **not** need the PC IP.

After reset, Serial Monitor at 115200 should print:

```text
Camera Ready! Use 'http://192.168.x.x' to connect
```

Use that ESP IP in PC Studio → Camera Sources.

## Endpoints used by AiTL

For an ESP at `192.168.1.87`:

```text
Still JPEG:
http://192.168.1.87/capture

MJPEG:
http://192.168.1.87:81/stream
```

V032 uses repeated `/capture` requests for the backend processing pipeline and may use `:81/stream` for direct Camera Sources preview.

## PC Studio workflow

1. Start AiTL PC Studio.
2. Open Camera Sources.
3. Enter the ESP IP only, for example `192.168.1.87`.
4. Keep source ID as `esp32_cam_01` unless you need a different identity.
5. Press Connect.
6. Confirm status is connected and frames increase.
7. Open Live AI / Dataset Capture / Zone Editor as required.

## Network requirements

The PC and ESP must be on the same reachable private LAN.

Accepted camera ranges:

```text
10.0.0.0/8
172.16.0.0/12
192.168.0.0/16
```

Hostnames and public IP addresses are intentionally not accepted by the V032 remote camera puller.

## Simulation

Simulation remains available. Starting simulation pauses ESP snapshot ingestion without deleting the configured ESP address. Stopping simulation resumes ESP ingestion.

## Legacy push compatibility

The older device-camera transport remains supported:

```http
POST /api/camera/frame?source_id=<camera_id>
Content-Type: image/jpeg

<raw JPEG bytes>
```

That mode requires the camera node to know the PC address. V032's preferred first-test path is PC → ESP pull because it matches the already-working Arduino CameraWebServer example.

## Multi-camera limitation

The current backend keeps one latest non-simulation camera frame. V032 adds source identity and connection structure but does not yet provide simultaneous independent frame buffers for several live ESP cameras.

## Safety boundary

This camera path is for a local/student prototype and model-junction demonstration. It does not connect AiTL to public-road traffic-signal infrastructure.
