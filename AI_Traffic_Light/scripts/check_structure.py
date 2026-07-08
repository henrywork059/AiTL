from pathlib import Path

required = [
    "apps/pc-studio/backend/app/main.py",
    "apps/pc-studio/frontend/src/App.tsx",
    "apps/device-camera/esp32-cam/src/main.cpp",
    "packages/schema/detection-frame.schema.json",
    "docs/START_HERE.md",
]

root = Path(__file__).resolve().parents[1]
missing = [path for path in required if not (root / path).exists()]

if missing:
    print("Missing files:")
    for path in missing:
        print(f"- {path}")
    raise SystemExit(1)

print("Project skeleton structure OK")
