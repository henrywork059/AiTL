/** Presentation-only interpolation in canonical synthetic camera pixels. No extrapolation. */
export type VehicleObservation = { id: string; visit?:number; x: number; y: number; width: number; direction: number; vehicle_type: string; color: string };
type Scene = { observation?:{epoch:string;generation:number}; source_id: string; simulation_time_seconds: number; paused: boolean; density: string; width: number; height: number; vehicles: readonly VehicleObservation[] };
export type VehiclePose = { x: number; y: number; heading: number };
type Track = { from: VehiclePose; to: VehiclePose; start: number; duration: number; observation: VehicleObservation };
const MAX_BLEND_MS = 450;
const MAX_CONTINUOUS_GAP_S = 1;
const directionHeading = (direction: number) => direction < 0 ? Math.PI : 0;
const center = (v: VehicleObservation) => ({ x: v.x + v.width / 2, y: v.y });
const sameShape = (a: VehicleObservation,b: VehicleObservation) =>
  a.width === b.width && a.vehicle_type === b.vehicle_type && a.color === b.color;
const angleDelta = (a: number,b: number) => Math.atan2(Math.sin(b-a),Math.cos(b-a));
function sample(track: Track, now: number): VehiclePose {
  const t = track.duration > 0 ? Math.max(0,Math.min(1,(now-track.start)/track.duration)) : 1;
  return { x: track.from.x+(track.to.x-track.from.x)*t, y: track.from.y+(track.to.y-track.from.y)*t,
    heading: track.from.heading+angleDelta(track.from.heading,track.to.heading)*t };
}
/** Local +X model axis transformed into each mirrored camera's world heading. */
export function mirroredYaw(heading: number, source: string) {
  const x = Math.cos(heading)*(source==="simulation_camera_c"||source==="simulation_camera_d"?-1:1);
  const z = Math.sin(heading)*(source==="simulation_camera_b"||source==="simulation_camera_d"?-1:1);
  return Math.atan2(-z,x);
}
export class VehicleMotion {
  private tracks = new Map<string,Track>();
  private last: {scope:string;source: string; time: number; paused: boolean; density: string} | null = null;
  clear() { this.tracks.clear(); this.last=null; }
  update(scene: Scene | null, now: number) {
    if (!scene || !Number.isFinite(scene.simulation_time_seconds)) { this.clear(); return; }
    const time=scene.simulation_time_seconds;
    const dt=this.last?time-this.last.time:0;
    const scope=scene.observation?scene.observation.epoch+':'+scene.observation.generation:'';
    const reset=!this.last||this.last.scope!==scope||this.last.source!==scene.source_id||this.last.density!==scene.density||dt<0||dt>MAX_CONTINUOUS_GAP_S;
    const resume=Boolean(this.last?.paused&&!scene.paused);
    const next=new Map<string,Track>();
    for(const v of scene.vehicles) {
      if(!Number.isFinite(v.x)||!Number.isFinite(v.y)||!Number.isFinite(v.width)||v.width<=0)continue;
      const previous=reset?undefined:this.tracks.get(v.id);
      const p=center(v);
      const dx=previous?p.x-previous.to.x:0,dy=previous?p.y-previous.to.y:0;
      // Backend IDs are recycled slots. Large jumps or backwards straight motion must not traverse the road.
      const discontinuous=Boolean(previous&&(Math.abs(dx)>scene.width/2||Math.abs(dy)>scene.height/2||
        (Math.abs(dy)<1 && dx*v.direction < -1)||previous.observation.visit!==v.visit||!sameShape(previous.observation,v)));
      const changed=Math.abs(dx)>0.001||Math.abs(dy)>0.001;
      const heading=previous&&!discontinuous&&changed?Math.atan2(dy,dx):
        previous&&!discontinuous&&v.direction===previous.observation.direction?previous.to.heading:directionHeading(v.direction);
      const to={...p,heading};
      if(previous&&!discontinuous&&!scene.paused&&!resume&&dt===0&&!changed) {
        next.set(v.id,previous); continue;
      }
      const blend=Boolean(previous&&!discontinuous&&!scene.paused&&!resume&&dt>0&&changed);
      next.set(v.id,{from:blend?sample(previous!,now):to,to,start:now,duration:blend?Math.min(MAX_BLEND_MS,dt*1000):0,observation:v});
    }
    this.tracks=next;
    this.last={scope,source:scene.source_id,time,paused:scene.paused,density:scene.density};
  }
  pose(id: string, now: number) { const t=this.tracks.get(id);return t?sample(t,now):undefined; }
  isAnimating(now: number) { return Array.from(this.tracks.values()).some(t=>t.duration>0&&now<t.start+t.duration); }
}
