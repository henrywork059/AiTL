from __future__ import annotations

import time
from typing import Any

from app.services.camera_architecture_diagnostics import (
    R9_FIRMWARE_PREFIX,
    camera_architecture_diagnostic_service,
)
from app.services.camera_diagnostic_dispatch import camera_diagnostic_dispatch_service
from app.services.camera_transport_alternatives import run_alternative_followup
from app.services.camera_tuning_diagnostics import (
    R10_TUNING_REVISION,
    camera_tuning_diagnostic_service,
)


class CameraDiagnosticEnhancedService:
    """Adaptive one-click camera diagnostics for production, R5/R8, R9 and R10 firmware.

    Normal production firmware behavior is unchanged. R5 firmware receives the
    established broad benchmark plus R8 payload/receiver follow-up. R9 firmware
    runs the focused server/producer-consumer/camera-free architecture isolation.
    R10 firmware keeps the R9 architecture marker but advertises tuning_revision
    R10 and runs the framebuffer/FPS/JPEG/TCP tuning matrix instead.
    """

    def _progress(self, stage: str, current_test: str) -> None:
        stage_text = str(stage)
        is_r10 = stage_text.startswith("R10")
        is_r9 = stage_text.startswith("R9")
        camera_diagnostic_dispatch_service._set(  # noqa: SLF001 - same service boundary
            status="running",
            engine="tuning_benchmark" if is_r10 else "architecture_benchmark" if is_r9 else "transport_benchmark",
            stage=stage,
            current_test=current_test,
            frame_current=None,
            frame_total=None,
            detail=(
                "R10 framebuffer / FPS / payload / TCP tuning"
                if is_r10
                else "R9 architecture bottleneck isolation"
                if is_r9
                else "R8 focused alternative follow-up"
            ),
        )

    def _probe_selected_firmware(self) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        profile = camera_diagnostic_dispatch_service._profile()  # noqa: SLF001
        if not profile:
            return None, {}
        host = str(profile.get("host") or "")
        status, payload = camera_diagnostic_dispatch_service._http(host, "/status")  # noqa: SLF001
        return profile, payload if status == 200 and isinstance(payload, dict) else {}

    def run(self) -> dict[str, Any]:
        camera_diagnostic_dispatch_service._set(  # noqa: SLF001
            status="running",
            engine="adaptive",
            stage="Preflight",
            current_test="Detect selected ESP diagnostic firmware",
            test_index=None,
            frame_current=None,
            frame_total=None,
            detail="Choose production, R5/R8 transport, R9 architecture, or R10 tuning diagnostic engine.",
            last_line=None,
            started_at_ms=int(time.time() * 1000),
            elapsed_ms=0,
            error=None,
            log_tail=[],
        )
        profile, device_status = self._probe_selected_firmware()
        firmware = str(device_status.get("firmware") or "")
        tuning_revision = str(device_status.get("tuning_revision") or "")

        if profile and firmware.startswith(R9_FIRMWARE_PREFIX) and tuning_revision == R10_TUNING_REVISION:
            self._progress("R10 PREFLIGHT", "Tuning benchmark firmware detected")
            try:
                report = camera_tuning_diagnostic_service.run(profile, progress=self._progress)
            except Exception as exc:
                message = f"R10 camera tuning diagnostic failed: {type(exc).__name__}: {exc}"
                camera_diagnostic_dispatch_service._set(  # noqa: SLF001
                    status="failed",
                    engine="tuning_benchmark",
                    stage="Failed",
                    current_test="R10 camera tuning diagnostic",
                    detail=message,
                    error=message,
                )
                raise
            camera_diagnostic_dispatch_service._set(  # noqa: SLF001
                status="completed",
                engine="tuning_benchmark",
                stage="Complete",
                current_test="R10 tuning recommendation ready",
                detail=f"R10 classification: {report.get('diagnosis_code')}",
                error=None,
            )
            report["diagnostic_revision"] = "V038 R10 tuning"
            return report

        if profile and firmware.startswith(R9_FIRMWARE_PREFIX):
            self._progress("R9 PREFLIGHT", "Architecture benchmark firmware detected")
            try:
                report = camera_architecture_diagnostic_service.run(profile, progress=self._progress)
            except Exception as exc:
                message = f"R9 architecture diagnostic failed: {type(exc).__name__}: {exc}"
                camera_diagnostic_dispatch_service._set(  # noqa: SLF001
                    status="failed",
                    engine="architecture_benchmark",
                    stage="Failed",
                    current_test="R9 architecture diagnostic",
                    detail=message,
                    error=message,
                )
                raise
            camera_diagnostic_dispatch_service._set(  # noqa: SLF001
                status="completed",
                engine="architecture_benchmark",
                stage="Complete",
                current_test="R9 architecture diagnosis ready",
                detail=f"R9 classification: {report.get('diagnosis_code')}",
                error=None,
            )
            report["diagnostic_revision"] = "V038 R9 architecture"
            return report

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
