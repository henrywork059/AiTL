"""Responsive panels and labels preserve text instead of truncating it."""
from pathlib import Path
import re

SRC = Path(__file__).resolve().parents[1] / "apps" / "pc-studio" / "frontend" / "src"


def read(path: str) -> str:
    return (SRC / path).read_text(encoding="utf-8")


def rule(css: str, selector: str) -> str:
    matches = re.findall(re.escape(selector) + r"\s*\{([^{}]*)\}", css)
    assert matches, selector
    return "\n".join(matches)


def main() -> None:
    base = read("styles/base.css")
    layout = read("styles/layout.css")
    shared = read("styles/components.css")
    junction = read("pages/junctionNetworkPage.css")
    experiments = read("pages/simulationLab.css")
    signals = read("pages/signalRules.css")

    for heading in ("h1", "h2", "h3"):
        assert "font-size: clamp(" in rule(base, heading)
    assert "overflow-wrap: anywhere;" in rule(
        base, ":where(h1, h2, h3, p, span, small, strong, code, label, button)"
    )
    assert "min-width: 0;" in rule(shared, ".panel")
    assert "flex-wrap: wrap;" in rule(shared, ".panel-header")
    assert "flex-wrap: wrap;" in rule(layout, ".page-header")
    assert "min-width: 0;" in rule(layout, ".page-header > *")
    assert "min-width: 0;" in rule(layout, ".content-frame > *,\n.page-stack > *")

    pill = rule(shared, ".status-pill,\n.status-placeholder")
    assert "justify-content: center;" in pill
    assert "text-align: center;" in pill
    assert "white-space: normal;" in pill
    assert "overflow-wrap: anywhere;" in pill
    assert "max-width: 100%;" in pill
    assert "flex-wrap: wrap;" in rule(shared, ".camera-status-list div")
    assert "font-size: clamp(" in rule(shared, ".metric-card strong")
    status = rule(shared, ".status-bar")
    assert "min-height: 40px;" in status
    assert "flex-wrap: wrap;" in status
    assert not re.search(r"(?m)^\s*height:\s*40px;", status)

    for selector in (".junction-camera-copy strong", ".junction-camera-copy small",
                     ".junction-link-row strong,\n.junction-link-row small"):
        css = rule(junction, selector)
        assert "white-space: normal;" in css, selector
        assert "overflow-wrap: anywhere;" in css, selector
        assert "text-overflow: ellipsis;" not in css, selector

    for selector in (".experiment-scenario-strip", ".experiment-tabs",
                     ".experiment-rule-list div"):
        assert "flex-wrap: wrap;" in rule(experiments, selector), selector
    scenario = rule(experiments, ".experiment-scenario-strip")
    assert "white-space: normal;" in scenario
    assert "overflow: hidden;" not in scenario
    assert "text-overflow: ellipsis;" not in rule(
        experiments, ".experiment-scenario-strip span, .experiment-scenario-strip strong"
    )
    assert ".experiment-workspace { height: auto; min-height: 0; overflow: visible; }" in experiments
    assert "@media (max-height: 700px)" in experiments
    assert "white-space: normal;" in rule(signals, ".scenario-list-copy small")

    # The translucent selected tint must leave camera pixels visible.
    crosswalk = read("pages/crosswalkRegionEditor.css")
    plain = rule(crosswalk, ".crosswalk-region-polygon")
    selected = rule(crosswalk, ".crosswalk-region-polygon.is-selected")
    assert "fill: rgba(87, 255, 237, 0.10);" in plain
    assert "fill: rgba(255, 246, 210, 0.22);" in selected
    assert "stroke: #fff5c7;" in selected and "stroke-width: 6;" in selected

    print("[PASS] Shared panels, headings, badges and buttons wrap at smaller widths")
    print("[PASS] Junction IDs, scenario descriptions and comparison labels are not ellipsized")
    print("[PASS] Short screen height can scroll full experiment content")
    print("[PASS] Selected region shows a translucent highlight and lighter outline")


if __name__ == "__main__":
    main()
