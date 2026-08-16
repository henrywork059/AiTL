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
    "/api/traffic/signal-rules",
    "/api/traffic/signal-status",
    "/api/traffic/signal-rules/history?limit=10",
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
            if endpoint == "/api/traffic/signal-rules" and ok:
                data = payload.get("data", {})
                if data.get("schema_version") != 1 or data.get("active_profile") not in data.get("profiles", {}):
                    failures.append("signal-rules: invalid schema/profile response")
            if endpoint == "/api/traffic/signal-status" and ok:
                data = payload.get("data", {})
                if not data.get("prototype_only") or data.get("mode") not in {"fixed", "adaptive", "test"}:
                    failures.append("signal-status: missing prototype/mode contract")
        except urllib.error.URLError as exc:
            print(f"[FAIL] {endpoint} -> {exc}")
            failures.append(f"{endpoint}: {exc}")
        except Exception as exc:
            print(f"[FAIL] {endpoint} -> {exc}")
            failures.append(f"{endpoint}: {exc}")

    if len(set(observed_versions.values())) > 1:
        failures.append(f"version endpoints disagree: {observed_versions}")

    for path, prefix, label in [
        ("/api/traffic/history/export.csv?minutes=1&limit=10", "recorded_at_ms,", "traffic history CSV"),
        ("/api/traffic/flow/export.csv?minutes=1&limit=10", "event_id,", "traffic flow CSV"),
    ]:
        try:
            csv_text, headers = fetch_text(path)
            ok = csv_text.startswith(prefix) and bool(headers.get("x-request-id"))
            print(f"[{'PASS' if ok else 'FAIL'}] {path.split('?')[0]}")
            if not csv_text.startswith(prefix):
                failures.append(f"{label}: missing expected header row")
            if not headers.get("x-request-id"):
                failures.append(f"{label}: missing X-Request-ID")
        except Exception as exc:
            print(f"[FAIL] {path.split('?')[0]} -> {exc}")
            failures.append(f"{label}: {exc}")

    print()
    if failures:
        print("Smoke test failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"Smoke test passed for {expected_version}. Core occupancy/tracking/flow/signal-rule APIs, request IDs, and version surfaces responded consistently.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
