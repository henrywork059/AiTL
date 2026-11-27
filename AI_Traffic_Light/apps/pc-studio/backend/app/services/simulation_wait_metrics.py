"""Evaluation-only blocked-motion reporting, with explicit units and censoring."""
from __future__ import annotations
import math
from app.services.simulation_gate_metrics import STEP_S


def blocked_motion(displacement, desired_displacement, tolerance, committed):
    """Legacy blocked-motion predicate; caller supplies consistent units."""
    return abs(displacement)+tolerance < abs(desired_displacement) and not committed


class NativeApproachWait:
    """Legacy-inspired, NOT legacy-equivalent queue/episode measurement.

    Native vehicle desired speed is the declared slot speed, so acceleration
    or car following can count as delay before the protected gate. The 0.05
    legacy pixel tolerance is converted by the existing 11 px/m speed ratio
    only (not physical calibration). Pedestrians: stationary within 0.5 m
    of the observed route gate entry. Missing/discontinuous visits and horizon
    are censored. Neither diagnostic feeds control.
    """
    def __init__(self):
        self.tick=0
        self.active={}
        self.completed={"vehicle":[],"pedestrian":[]}
        self.censored={"vehicle":[],"pedestrian":[]}
        self.samples={"vehicle":[],"pedestrian":[]}

    def sample(self,tick,before,after,rows,trips):
        if tick!=self.tick+1:
            raise ValueError("Nonconsecutive native wait sample")
        previous={a.id:a for a in before}
        observed={a.id:a for a in after}
        queued={}
        continuous=set()
        distances={}
        for ident,a in observed.items():
            old=previous.get(ident)
            if old is None or old.kind!=a.kind:
                continue
            trip=trips[a.engine_id]
            displacement=math.hypot(a.x_m-old.x_m,a.y_m-old.y_m)
            if displacement>max(trip.desired_speed,old.speed_m_s,a.speed_m_s)*STEP_S+.05:
                continue
            continuous.add(ident)
            distances[ident]=displacement
        for row in rows:
            if row.ident not in continuous:
                continue
            a=observed[row.ident]
            old=previous[row.ident]
            trip=trips[a.engine_id]
            displacement=distances[row.ident]
            if row.progress>=0:
                continue
            if a.kind=="vehicle":
                # Both samples are on the incoming external lane. Never count
                # a body already committed to the gate, or an outgoing vehicle.
                is_waiting=(old.road_id==a.road_id==trip.path[0].road_id and
                    blocked_motion(displacement,trip.desired_speed*STEP_S,.05/11,False))
            else:
                is_waiting=(-row.progress*row.span<=.5 and displacement/STEP_S<=.1)
            if is_waiting:
                queued[row.ident]=a.kind
        # Leaving a service gate while still observed is an ended wait.
        # A lost or discontinuous journey cannot manufacture completion.
        for ident,(kind,count) in self.active.items():
            if ident not in queued:
                (self.completed if ident in continuous else self.censored)[kind].append(count)
        self.active={ident:(kind,self.active.get(ident,(kind,0))[1]+1)
                     for ident,kind in queued.items()}
        self.tick=tick
        counts={kind:sum(v==kind for v in queued.values()) for kind in self.samples}
        for kind,value in counts.items():
            self.samples[kind].append(value)
        return {"legacy_inspired_"+kind+"_queue":value for kind,value in counts.items()}

    def report(self):
        from app.services.simulation_experiments import _distribution,_queue_distribution
        result={}
        for kind,values in self.samples.items():
            finished=self.completed[kind]
            censored=self.censored[kind]+[n for k,n in self.active.values() if k==kind]
            total=sum(values)
            if sum(finished)+sum(censored)!=total:
                raise ValueError("Native approach wait integral mismatch")
            result[kind]={"completed_seconds":[round(n*STEP_S,6) for n in finished],
                "censored_observed_seconds":[round(n*STEP_S,6) for n in censored],
                "completed":_distribution([n*STEP_S for n in finished]),
                "censored_observed":_distribution([n*STEP_S for n in censored]),
                "observed_agent_seconds":round(total*STEP_S,6),
                "queue":_queue_distribution(values,total*STEP_S,sum(v>0 for v in values)*STEP_S,self.tick*STEP_S)}
        return {"contract":"native_legacy_inspired_approach_wait_v1","step_s":STEP_S,
            "vehicle_displacement_tolerance_m":.05/11,"pedestrian_entry_distance_m":.5,
            "pedestrian_stationary_speed_m_s":.1,"native_acceleration_may_count_as_delay":True,
            "production_experiment_parity":False,"physical_output_allowed":False,"waiting":result}
