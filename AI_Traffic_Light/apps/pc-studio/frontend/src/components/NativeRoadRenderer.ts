/** Read-only volumetric native road and agent presentation. No signal authority. */
import * as THREE from "three";
import type {NativeProjectionScene} from "../lib/remoteCameraApi";
import {makeVehicleVisual,disposeVehicleVisual,type VehicleVisual} from "./vehicleMeshes";
import {makePedestrianVisual,disposePedestrianVisual,setPedestrianGait,type PedestrianVisual} from "./pedestrianMeshes";

type Point={x:number;z:number};
type Track={kind:"vehicle"|"pedestrian";visual:VehicleVisual|PedestrianVisual;from:Point;to:Point;start:number;duration:number;heading:number};
const point=(x:number,y:number,source:string):Point=>({x:(source.endsWith("_c")||source.endsWith("_d")?1279-x:x)-640,z:(source.endsWith("_b")||source.endsWith("_d")?719-y:y)-360});
const pose=(t:Track,now:number):Point=>{const f=t.duration?Math.max(0,Math.min(1,(now-t.start)/t.duration)):1;return{x:t.from.x+(t.to.x-t.from.x)*f,z:t.from.z+(t.to.z-t.from.z)*f};};

export class NativeRoadRenderer {
  readonly renderer:THREE.WebGLRenderer;
  private scene=new THREE.Scene();
  private camera=new THREE.PerspectiveCamera(45,1,1,8000);
  private box=new THREE.BoxGeometry(1,1,1);
  private sphere=new THREE.SphereGeometry(1,10,8);
  private roadGroup=new THREE.Group();
  private mats=[0x56504b,0x8e8982,0xe1e1e1].map(color=>new THREE.MeshStandardMaterial({color,roughness:.9}));
  private tracks=new Map<string,Track>();
  private generation=-1;
  private tick=-1;
  private layoutId:string|undefined;
  private closed=false;
  private w=0;
  private h=0;
  private lost=(event:Event)=>{event.preventDefault();this.onFailure();};
  constructor(private host:HTMLElement,private source:string,private onFailure:()=>void){
    this.renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});
    try{
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
      this.renderer.domElement.style.cssText="display:block;width:100%;height:100%";
      this.renderer.domElement.dataset.nativeWebgl="true";
      this.renderer.domElement.addEventListener("webglcontextlost",this.lost);
      this.host.appendChild(this.renderer.domElement);
      this.scene.background=new THREE.Color(0x25323c);
      this.scene.add(this.roadGroup,new THREE.HemisphereLight(0xe8f3ff,0x545c50,2));
      const sun=new THREE.DirectionalLight(0xfff5e6,2.1);sun.position.set(-400,900,350);this.scene.add(sun);
    }catch(error){this.dispose();throw error;}
  }
  private remove(t:Track){
    if(t.kind==="vehicle")disposeVehicleVisual(t.visual as VehicleVisual);
    else disposePedestrianVisual(t.visual as PedestrianVisual);
  }
  private clear(){for(const t of this.tracks.values())this.remove(t);this.tracks.clear();for(const mesh of this.roadGroup.children)if(mesh instanceof THREE.InstancedMesh)mesh.dispose();this.roadGroup.clear();}
  update(s:NativeProjectionScene,now=performance.now()){
    if(this.closed||s.generation<this.generation)return;
    const reset=s.generation!==this.generation;
    if(!reset&&s.layout_id!==this.layoutId)throw new Error("Native layout changed without a generation reset");
    if(reset){
      this.clear();this.generation=s.generation;this.tick=-1;this.layoutId=s.layout_id;
      // Static road surfaces use one draw group per material; zebra bands are
      // based on the actual crossing segment, not invented signal permissions.
      const transform=new THREE.Object3D();
      for(const [index,kind] of (["road","walk","crossing"] as const).entries()){
        const matrices:THREE.Matrix4[]=[];
        for(const lane of s.lanes.filter(l=>l.kind===kind)){
          for(let i=1;i<lane.points.length;i++){
            const a=point(...lane.points[i-1],this.source),b=point(...lane.points[i],this.source);
            const dx=b.x-a.x,dz=b.z-a.z,len=Math.hypot(dx,dz);if(!len)continue;
            const count=kind==="crossing"?Math.min(24,Math.max(1,Math.round(len/Math.max(2,(s.pixels_per_m??3.2)*.8)))):1;
            for(let j=0;j<count;j++){
              const along=(j+.5)/count;
              transform.position.set(a.x+dx*along,index*.5,a.z+dz*along);
              transform.scale.set(kind==="crossing"?len/count*.55:len+lane.width_px*.08,1,lane.width_px);
              transform.rotation.set(0,-Math.atan2(dz,dx),0);transform.updateMatrix();
              matrices.push(transform.matrix.clone());
            }
          }
        }
        if(matrices.length){
          const mesh=new THREE.InstancedMesh(this.box,this.mats[index],matrices.length);
          matrices.forEach((matrix,i)=>mesh.setMatrixAt(i,matrix));
          mesh.instanceMatrix.needsUpdate=true;
          this.roadGroup.add(mesh);
        }
      }
    }
    if(s.tick<this.tick)return;
    const same=s.tick===this.tick;
    const continuous=!reset&&!same&&!s.paused&&s.tick-this.tick<=5;
    const ppm=s.pixels_per_m??3.2;
    const ids=new Set<string>();
    for(const a of s.agents){
      ids.add(a.id);
      const to=point(a.x,a.y,this.source);
      let track=this.tracks.get(a.id);
      if(track&&track.kind!==a.kind){this.remove(track);this.tracks.delete(a.id);track=undefined;}
      if(!track){
        const visual=a.kind==="vehicle"?makeVehicleVisual({id:a.id,x:0,y:0,width:145,direction:1,vehicle_type:"car",color:"#46a7dc"},this.box):
          makePedestrianVisual({id:a.id,x:0,y:0,direction:1,color:"#e5a94c"},this.box,this.sphere);
        visual.group.scale.setScalar(a.kind==="vehicle"?4.5*ppm/145:1.7*ppm/54);
        this.scene.add(visual.group);
        track={kind:a.kind,visual,from:to,to,start:now,duration:0,heading:0};
        this.tracks.set(a.id,track);
      }else if(!same||s.paused){
        const from=pose(track,now),dx=to.x-track.to.x,dz=to.z-track.to.z,distance=Math.hypot(dx,dz);
        if(distance>0.01)track.heading=-Math.atan2(dz,dx);
        track.from=continuous&&distance<=ppm*15?from:to;
        track.to=to;track.start=now;
        track.duration=continuous&&distance>0.01&&distance<=ppm*15?Math.min(450,(s.tick-this.tick)*200):0;
      }
    }
    for(const [id,t] of this.tracks)if(!ids.has(id)){this.remove(t);this.tracks.delete(id);}
    this.tick=s.tick;
  }
  isAnimating(now=performance.now()){if(this.closed)return false;for(const t of this.tracks.values())if(t.duration>0&&now<t.start+t.duration)return true;return false;}
  render(top:boolean,now=performance.now(),detail=false){
    if(this.closed)return;
    const w=Math.max(1,this.host.clientWidth),h=Math.max(1,this.host.clientHeight);
    if(w!==this.w||h!==this.h){this.renderer.setSize(w,h,false);this.w=w;this.h=h;}
    for(const t of this.tracks.values()){
      const p=pose(t,now);t.visual.group.position.set(p.x,2,p.z);t.visual.group.rotation.y=t.heading;
      if(t.kind==="pedestrian"){
        const fraction=t.duration?Math.max(0,Math.min(1,(now-t.start)/t.duration)):1;
        setPedestrianGait(t.visual as PedestrianVisual,t.duration&&fraction<1?Math.sin(fraction*Math.PI*2)*Math.min(1,Math.hypot(t.to.x-t.from.x,t.to.z-t.from.z)/2)*Math.min(1,(1-fraction)*5):0);
      }
    }
    this.camera.aspect=w/h;
    // Fit native junction more tightly, with a separate close view of crossing agents.
    const distance=(detail ? .085 : .39)*Math.max(1,1.3/this.camera.aspect);
    this.camera.position.set(0,(top?1800:1450)*distance,(top?0:1050)*distance);
    if(top)this.camera.up.set(0,0,-1);else this.camera.up.set(0,1,0);
    this.camera.lookAt(0,0,0);this.camera.updateProjectionMatrix();
    this.renderer.render(this.scene,this.camera);
  }
  dispose(){
    if(this.closed)return;this.closed=true;
    this.renderer.domElement.removeEventListener("webglcontextlost",this.lost);
    this.clear();this.scene.clear();this.box.dispose();this.sphere.dispose();for(const m of this.mats)m.dispose();
    this.renderer.dispose();this.renderer.forceContextLoss();this.renderer.domElement.remove();
  }
}
