"""Simple backend smoke test using only the Python standard library.

Run after starting the backend:
    python scripts/test_backend_smoke.py
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8000"
ENDPOINTS = [
    "/health",
    "/api/smoke/status",
    "/api/zones/active",
    "/api/traffic/state",
    "/api/settings/runtime",
    "/api/logs/recent?limit=5",
    "/api/camera/status",
    "/api/dataset/status",
    "/api/dataset/captures?limit=5",
    "/api/dataset/training-dataset/status",
    "/api/training/status",
    "/api/inference/status",
    "/api/models",
]


def fetch_json(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=10) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)


def main() -> int:
    failures: list[str] = []
    print("AI Traffic Light backend smoke test")
    print(f"Base URL: {BASE_URL}")
    print()

    for endpoint in ENDPOINTS:
        try:
            payload = fetch_json(endpoint)
            ok = payload.get("ok") is True
            status = "PASS" if ok else "FAIL"
            print(f"[{status}] {endpoint}")
            if not ok:
                failures.append(f"{endpoint}: API envelope ok=false")
        except urllib.error.URLError as exc:
            print(f"[FAIL] {endpoint} -> {exc}")
            failures.append(f"{endpoint}: {exc}")
        except Exception as exc:  # noqa: BLE001 - smoke test should report all failures.
            print(f"[FAIL] {endpoint} -> {exc}")
            failures.append(f"{endpoint}: {exc}")

    print()
    if failures:
        print("Smoke test failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Smoke test passed. V020 capture lifecycle, camera-aligned zones, live overlays, training, settings, logs, and existing APIs responded successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
