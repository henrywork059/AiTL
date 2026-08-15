"""Simple backend smoke test using only the Python standard library.

Run after starting the backend:
    python scripts/test_backend_smoke.py
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8000"
ENDPOINTS = [
    "/health",
    "/api/smoke/status",
    "/api/template/pc-studio",
    "/api/zones/active",
    "/api/traffic/state",
    "/api/traffic/history?minutes=1&limit=10",
    "/api/traffic/tracks",
    "/api/traffic/flow?minutes=1&limit=10",
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
VERSION_ENDPOINTS = {"/health", "/api/smoke/status", "/api/template/pc-studio"}


def read_expected_version() -> str:
    version_path = Path(__file__).resolve().parents[1] / "VERSION"
    for line in version_path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() == "version":
            return value.strip()
    raise RuntimeError(f"No version field found in {version_path}")


def fetch_json(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=10) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)



def fetch_text(path: str) -> tuple[str, dict[str, str]]:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=10) as response:
        raw = response.read().decode("utf-8")
        headers = {key.lower(): value for key, value in response.headers.items()}
    return raw, headers


def main() -> int:
    failures: list[str] = []
    observed_versions: dict[str, str] = {}
    expected_version = read_expected_version()

    print("AI Traffic Light backend smoke test")
    print(f"Base URL: {BASE_URL}")
    print(f"Expected project version: {expected_version}")
    print()

    for endpoint in ENDPOINTS:
        try:
            payload = fetch_json(endpoint)
            ok = payload.get("ok") is True
            request_id = payload.get("meta", {}).get("request_id")
            status = "PASS" if ok and request_id else "FAIL"
            print(f"[{status}] {endpoint}")

            if not ok:
                failures.append(f"{endpoint}: API envelope ok=false")
            if not request_id:
                failures.append(f"{endpoint}: missing meta.request_id")

            if endpoint in VERSION_ENDPOINTS and ok:
                version = payload.get("data", {}).get("version")
                if not isinstance(version, str) or not version:
                    failures.append(f"{endpoint}: missing data.version")
                else:
                    observed_versions[endpoint] = version
                    if version != expected_version:
                        failures.append(f"{endpoint}: version={version!r}, expected {expected_version!r}")
        except urllib.error.URLError as exc:
            print(f"[FAIL] {endpoint} -> {exc}")
            failures.append(f"{endpoint}: {exc}")
        except Exception as exc:  # noqa: BLE001 - smoke test should report all failures.
            print(f"[FAIL] {endpoint} -> {exc}")
            failures.append(f"{endpoint}: {exc}")

    if len(set(observed_versions.values())) > 1:
        failures.append(f"version endpoints disagree: {observed_versions}")

    try:
        csv_text, csv_headers = fetch_text("/api/traffic/history/export.csv?minutes=1&limit=10")
        csv_ok = csv_text.startswith("recorded_at_ms,") and bool(csv_headers.get("x-request-id"))
        print(f"[{'PASS' if csv_ok else 'FAIL'}] /api/traffic/history/export.csv")
        if not csv_text.startswith("recorded_at_ms,"):
            failures.append("traffic history CSV export: missing expected header row")
        if not csv_headers.get("x-request-id"):
            failures.append("traffic history CSV export: missing X-Request-ID")
    except Exception as exc:  # noqa: BLE001 - smoke test should report all failures.
        print(f"[FAIL] /api/traffic/history/export.csv -> {exc}")
        failures.append(f"traffic history CSV export: {exc}")

    try:
        flow_csv, flow_headers = fetch_text("/api/traffic/flow/export.csv?minutes=1&limit=10")
        flow_ok = flow_csv.startswith("event_id,") and bool(flow_headers.get("x-request-id"))
        print(f"[{'PASS' if flow_ok else 'FAIL'}] /api/traffic/flow/export.csv")
        if not flow_csv.startswith("event_id,"):
            failures.append("traffic flow CSV export: missing expected header row")
        if not flow_headers.get("x-request-id"):
            failures.append("traffic flow CSV export: missing X-Request-ID")
    except Exception as exc:  # noqa: BLE001 - smoke test should report all failures.
        print(f"[FAIL] /api/traffic/flow/export.csv -> {exc}")
        failures.append(f"traffic flow CSV export: {exc}")

    print()
    if failures:
        print("Smoke test failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(
        f"Smoke test passed for {expected_version}. Core V022 occupancy/tracking/flow APIs, request IDs, and version surfaces responded consistently."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
