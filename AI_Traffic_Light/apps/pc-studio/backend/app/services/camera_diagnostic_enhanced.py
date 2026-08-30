from __future__ import annotations

from typing import Any

from app.services.camera_diagnostic_dispatch import camera_diagnostic_dispatch_service
from app.services.camera_transport_alternatives import run_alternative_followup


class CameraDiagnosticEnhancedService:
    """Add focused R8 transport alternatives after the established adaptive diagnostic.

    Normal production firmware behavior is unchanged. The follow-up only runs when
    the base report contains an R5 transport-benchmark report.
    """

    def _progress(self, stage: str, current_test: str) -> None:
        # CameraDiagnosticDispatchService owns the progress state used by the
        # existing /progress endpoint. This collaborator update keeps the R8
        # follow-up visible without creating a second progress store.
        camera_diagnostic_dispatch_service._set(  # noqa: SLF001 - same service boundary
            status="running",
            engine="transport_benchmark",
            stage=stage,
            current_test=current_test,
            frame_current=None,
            frame_total=None,
            detail="R8 focused alternative follow-up",
        )

    def run(self) -> dict[str, Any]:
        report = camera_diagnostic_dispatch_service.run()
        raw = report.get("transport_benchmark")
        if not isinstance(raw, dict):
            return report

        firmware = str(raw.get("firmware") or "")
        if not firmware.startswith("aitl-0_3_8-r5-transport-benchmark"):
            return report

        self._progress("R8 ALTERNATIVE FOLLOW-UP", "Deriving median real JPEG size")
        try:
            rows, analysis = run_alternative_followup(
                str(report.get("host") or raw.get("host") or ""),
                raw,
                progress=self._progress,
            )
        except Exception as exc:
            message = f"R8 alternative follow-up failed: {type(exc).__name__}: {exc}"
            report.setdefault("checks", []).append(
                {
                    "id": "alternative_transport_followup",
                    "category": "bottleneck",
                    "label": "R8 transport alternative follow-up",
                    "status": "warn",
                    "detail": message,
                    "metrics": {},
                }
            )
            report.setdefault("recommendations", []).append(
                "The focused R8 alternative follow-up did not complete; retain the R5 evidence and rerun after checking ESP reachability."
            )
            camera_diagnostic_dispatch_service._set(  # noqa: SLF001
                status="completed",
                stage="Complete",
                current_test="Diagnosis ready with R8 follow-up warning",
                detail=message,
            )
            return report

        raw_results = raw.get("results") if isinstance(raw.get("results"), list) else []
        raw_results.extend(rows)
        raw["results"] = raw_results
        raw["benchmark_revision"] = "R5 + R8 alternatives"
        raw["alternative_analysis"] = analysis
        report["alternative_analysis"] = analysis

        findings = [str(item) for item in analysis.get("findings", []) if item]
        summary_detail = "; ".join(findings[:3]) or "Focused alternative transport comparison completed."
        report.setdefault("checks", []).append(
            {
                "id": "alternative_transport_followup",
                "category": "bottleneck",
                "label": "R8 payload / receiver alternative isolation",
                "status": "pass",
                "detail": summary_detail,
                "metrics": analysis,
            }
        )

        classification = str(analysis.get("classification") or "alternative_followup_complete")
        cause_label = classification.replace("_", " ")
        causes = report.setdefault("likely_causes", [])
        if cause_label not in causes:
            causes.append(cause_label)

        next_action = str(analysis.get("next_action") or "")
        recommendations = report.setdefault("recommendations", [])
        if next_action and next_action not in recommendations:
            recommendations.insert(1 if recommendations else 0, next_action)

        bottlenecks = report.get("bottleneck_analysis")
        if isinstance(bottlenecks, dict):
            items = bottlenecks.get("findings") if isinstance(bottlenecks.get("findings"), list) else []
            items.append(
                {
                    "id": "r8_alternative_followup",
                    "layer": "transport",
                    "severity": "warning",
                    "title": f"R8 alternative isolation: {cause_label}",
                    "evidence": summary_detail,
                    "impact": "Separates payload-size scaling and PC receive-side backpressure from the already-confirmed sendmsg failure.",
                    "recommendation": next_action or "Use the exact-size and receiver-buffer evidence before changing the production transport.",
                }
            )
            bottlenecks["findings"] = items

        report["diagnostic_revision"] = "V038 R8 alternatives"
        camera_diagnostic_dispatch_service._set(  # noqa: SLF001
            status="completed",
            stage="Complete",
            current_test="Diagnosis ready",
            frame_current=None,
            frame_total=None,
            detail=f"R8 alternatives: {cause_label}",
        )
        return report

    def progress(self) -> dict[str, Any]:
        return camera_diagnostic_dispatch_service.progress()


camera_diagnostic_enhanced_service = CameraDiagnosticEnhancedService()

__all__ = ["CameraDiagnosticEnhancedService", "camera_diagnostic_enhanced_service"]
