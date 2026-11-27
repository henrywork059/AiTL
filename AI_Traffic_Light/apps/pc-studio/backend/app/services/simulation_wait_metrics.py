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



class LegacyWaitSamples:
    """Observe the existing legacy blocked/curb predicates at actual substeps.

    Keep the original historical metrics (which include open waits) unchanged.
    This report separates sampled completed and censored episodes and integrates
    queues on the exact same dt; no claim that native motion matches legacy.
    """
    def __init__(self):
        self.active={}
        self.completed={"vehicle":[],"pedestrian":[]}
        self.censored={"vehicle":[],"pedestrian":[]}
        self.integrals={"vehicle":0.,"pedestrian":0.}
        self.occupied={"vehicle":0.,"pedestrian":0.}
        self.duration=0.
        self.steps=0

    def sample(self,dt,queued,retired):
        if not math.isfinite(dt) or dt<=0:
            raise ValueError("Invalid legacy wait step")
        # The reported queue still includes any final queued sample before a
        # respawn. Retire the old visit after that sample, not as a completion.
        for key,seconds in self.active.items():
            if key not in queued:
                target=self.censored if key in retired else self.completed
                target[key[0]].append(seconds)
        self.active={key:self.active.get(key,0.)+dt for key in queued}
        for key in retired:
            if key in self.active:
                self.censored[key[0]].append(self.active.pop(key))
        for kind in self.integrals:
            count=sum(key[0]==kind for key in queued)
            self.integrals[kind]+=count*dt
            self.occupied[kind]+=dt if count else 0.
        self.duration+=dt
        self.steps+=1

    def report(self):
        from app.services.simulation_experiments import _distribution
        result={}
        for kind in self.integrals:
            completed=self.completed[kind]
            censored=self.censored[kind]+[v for k,v in self.active.items() if k[0]==kind]
            if not math.isclose(sum(completed)+sum(censored),self.integrals[kind],abs_tol=1e-6):
                raise ValueError("Legacy substep queue integral mismatch")
            result[kind]={"completed_seconds":[round(v,6) for v in completed],
                "censored_observed_seconds":[round(v,6) for v in censored],
                "completed":_distribution(completed),"censored_observed":_distribution(censored),
                "observed_agent_seconds":round(self.integrals[kind],6),
                "occupied_seconds":round(self.occupied[kind],6)}
        return {"contract":"legacy_actual_substep_wait_v1","duration_seconds":round(self.duration,6),
                "samples":self.steps,"waiting":result,"production_experiment_parity":False}
