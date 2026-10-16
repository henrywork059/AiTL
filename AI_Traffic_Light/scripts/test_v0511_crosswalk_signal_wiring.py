from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def read(path):
    return (ROOT / path).read_text(encoding="utf-8")
def main():
    network = read("apps/pc-studio/frontend/src/components/CrosswalkNetworkPanel.tsx")
    routes = read("apps/pc-studio/backend/app/routes/traffic.py")
    service = read("apps/pc-studio/backend/app/services/crosswalk_signals.py")
    assert 'crosswalkSignal?.signal' in network
    assert 'fetchCrosswalkSignalNetwork()' in network
    assert '@router.get("/crosswalk-signals")' in routes
    assert 'coordination_enabled": running and conflicts_configured' in service
    assert 'movement_conflicts_configured": conflicts_configured' in service
    print("[PASS] independent signal Network/API wiring")
if __name__ == "__main__":
    main()
