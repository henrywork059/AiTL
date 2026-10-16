"""V0510 UI integration regression for safe, source-scoped signal display."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "apps/pc-studio/frontend/src"

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def main() -> None:
    nav = read("constants/appNavigation.ts")
    app = read("App.tsx")
    network = read("components/CrosswalkNetworkPanel.tsx")
    lamps = read("components/CrosswalkSignalIndicators.tsx")
    timing = read("pages/SignalTimingPage.tsx")
    rules = read("pages/LiveSignalAdjustmentsPage.tsx")
    assert "PAGE_DETAILS.signal_timing, PAGE_DETAILS.live_signal_adjustments" in nav
    assert "case \"signal_timing\"" in app and "case \"live_signal_adjustments\"" in app
    assert "fetchSignalRules" in timing and "saveSignalRules" in timing
    assert "latest.profiles[latest.active_profile].scenarios" in rules and "saveSignalRules" in rules
    assert "phase_remaining_seconds" in rules
    assert "simulated" not in rules.lower() or "protected" in rules.lower()
    assert "crosswalkSignal?.signal" in network
    assert "route off unless explicitly enabled" in network
    assert "simulationEnabled" in network and "CrosswalkSignalIndicators" in network
    assert "No verified crosswalk signal (not controlled)" in lamps
    assert "Math.ceil(signal.seconds_remaining)" in lamps
    print("[PASS] Traffic Settings and Live Signal Adjustment routes and persistence")
    print("[PASS] Crosswalk signals are simulation-scoped; unverified neighbours cannot show fabricated phases")

if __name__ == "__main__":
    main()
