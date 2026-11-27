"""Shared normalized gate report; separate from legacy per-visit semantics."""
from __future__ import annotations
from app.services.simulation_gate_metrics import STEP_S


def normalized_report_metrics(timeline,summary,episodes):
    """Report shape shared with legacy distributions, not legacy metric parity.

    Keep censored waits separate; legacy uses different blocked-motion/visit
    semantics. Never relabel these normalized observations as legacy metrics.
    """
    from app.services.simulation_experiments import _distribution, _queue_distribution
    duration=len(timeline)*STEP_S
    queues={}
    waiting={}
    for kind in ("vehicle","pedestrian"):
        values=[row[kind+"_queue"] for row in timeline]
        ep=episodes[kind]
        observed=sum(values)*STEP_S
        if (abs(observed-ep["observed_agent_seconds"])>1e-6 or
            abs(observed-summary[kind+"_wait_agent_s"])>1e-6):
            raise ValueError("Normalized wait integral mismatch")
        waiting[kind]={"completed":_distribution(ep["completed_seconds"]),
                       "censored_observed":_distribution(ep["censored_observed_seconds"]),
                       "observed_agent_seconds":round(observed,6)}
        queues[kind]=_queue_distribution(values,observed,sum(v>0 for v in values)*STEP_S,duration)
    return {"metric_contract":"normalized_physical_service_gate_v1","production_experiment_parity":False,
            "duration_seconds":round(duration,6),"waiting":waiting,"queues":queues,
            "throughput":{"vehicle_passages":summary["vehicle_passages"],"pedestrian_crossings":summary["pedestrian_crossings"],
                          "vehicle_per_minute":round(summary["vehicle_passages"]*60/duration,2) if duration else 0.,
                          "pedestrian_per_minute":round(summary["pedestrian_crossings"]*60/duration,2) if duration else 0.},
            "censored_pedestrian_visits":summary["censored_pedestrian_visits"]}
