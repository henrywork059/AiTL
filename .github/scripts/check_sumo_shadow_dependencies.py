"""CI-only exact PyPI release advisory check; not a native DLL vulnerability audit."""
from importlib.metadata import version
import json
from urllib.request import urlopen

PACKAGES = ("eclipse-sumo", "sumo-data", "libsumo", "traci", "sumolib")
PIN = "1.28.0"

def main():
    for name in PACKAGES:
        if version(name) != PIN:
            raise RuntimeError(f"Unexpected installed version: {name}")
        with urlopen(f"https://pypi.org/pypi/{name}/{PIN}/json", timeout=15) as response:
            data = json.loads(response.read(2_000_000))
        if data["info"]["version"] != PIN or not isinstance(data["vulnerabilities"], list):
            raise RuntimeError(f"Invalid release metadata: {name}")
        active = [v for v in data["vulnerabilities"] if not v.get("withdrawn")]
        print(json.dumps({"package": name, "version": PIN, "active_advisories": active}))
        if active:
            raise RuntimeError(f"Active release advisory: {name}")

if __name__ == "__main__":
    main()
