/** Presentation only: follow observed canonical pixels; never grant permission or extrapolate. */
export type PedestrianObservation = {id:string;x:number;y:number;direction:number;color:string};
type Scene = {source_id:string;simulation_time_seconds:number;paused:boolean;density:string;width:number;height:number;pedestrians:readonly PedestrianObservation[]};
export type PedestrianPose = {x:number;y:number;direction:number;stride:number;swing:number;walking:boolean};
type Track = {from:PedestrianPose;to:PedestrianPose;start:number;duration:number;color:string};
const MAX_BLEND_MS=450;
const STRIDE_PIXELS=34;
const neutral=(p:PedestrianObservation,stride=0):PedestrianPose=>({x:p.x,y:p.y,direction:p.direction,stride,swing:0,walking:false});
function sample(t:Track,now:number):PedestrianPose {
  const a=t.duration>0?Math.max(0,Math.min(1,(now-t.start)/t.duration)):1;
  const stride=t.from.stride+(t.to.stride-t.from.stride)*a;
  const walking=t.duration>0&&a<1&&t.to.stride>t.from.stride;
  // Taper the gait near the end of a segment; a stopped/blocked observation never walks in place.
  const fade=Math.min(1,(1-a)*5);
  return {x:t.from.x+(t.to.x-t.from.x)*a,y:t.from.y+(t.to.y-t.from.y)*a,direction:t.to.direction,
    stride,swing:walking?Math.sin(stride*2*Math.PI/STRIDE_PIXELS)*fade:0,walking};
}
export class PedestrianMotion {
  private tracks=new Map<string,Track>();
  private last:{source:string;time:number;paused:boolean;density:string}|null=null;
  clear(){this.tracks.clear();this.last=null;}
  update(scene:Scene|null,now:number){
    if(!scene||!Number.isFinite(scene.simulation_time_seconds)){this.clear();return;}
    const time=scene.simulation_time_seconds,dt=this.last?time-this.last.time:0;
    const reset=!this.last||this.last.source!==scene.source_id||this.last.density!==scene.density||dt<0||dt>1;
    const resume=Boolean(this.last?.paused&&!scene.paused);
    const next=new Map<string,Track>();
    for(const p of scene.pedestrians){
      if(!Number.isFinite(p.x)||!Number.isFinite(p.y)||![-1,1].includes(p.direction))continue;
      const prev=reset?undefined:this.tracks.get(p.id);
      const dx=prev?p.x-prev.to.x:0,dy=prev?p.y-prev.to.y:0;
      const discontinuous=Boolean(prev&&(Math.abs(dx)>scene.width/2||Math.abs(dy)>scene.height/2||
        dy*p.direction<-.5||Math.abs(dx)>1||prev.to.direction!==p.direction||prev.color!==p.color));
      const changed=Math.hypot(dx,dy)>.001;
      if(prev&&!discontinuous&&!scene.paused&&!resume&&!changed){
        // Repeated/blocked observations do not restart the gait or jump to a still-pending target.
        next.set(p.id,prev);continue;
      }
      const blend=Boolean(prev&&!discontinuous&&!scene.paused&&!resume&&dt>0&&changed);
      const from=blend?sample(prev!,now):neutral(p);
      const distance=blend?Math.hypot(p.x-from.x,p.y-from.y):0;
      const to=neutral(p,from.stride+distance);
      next.set(p.id,{from,to,start:now,duration:blend?Math.min(MAX_BLEND_MS,dt*1000):0,color:p.color});
    }
    this.tracks=next;this.last={source:scene.source_id,time,paused:scene.paused,density:scene.density};
  }
  pose(id:string,now:number){const t=this.tracks.get(id);return t?sample(t,now):undefined;}
  isAnimating(now:number){return Array.from(this.tracks.values()).some(t=>t.duration>0&&now<t.start+t.duration);}
}
