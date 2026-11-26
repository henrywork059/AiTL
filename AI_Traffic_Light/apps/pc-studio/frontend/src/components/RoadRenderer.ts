/** Read-only Three.js road presentation: no polling, controller, or simulation mutation. */
import * as THREE from 'three';
import { ROAD, roadSurfaces, worldPoint, cameraPose } from './roadGeometry';
import type { SimulationScene } from '../lib/remoteCameraApi';
import { VehicleMotion, mirroredYaw } from './vehicleMotion';
import { makeVehicleVisual, disposeVehicleVisual, vehicleSignature, type VehicleVisual } from './vehicleMeshes';

export class RoadRenderer {
  readonly renderer: THREE.WebGLRenderer;
  private readonly scene = new THREE.Scene();
  private readonly camera = new THREE.PerspectiveCamera(50, 1, 1, 6000);
  private readonly materials = new Set<THREE.Material>();
  private readonly geometry = new THREE.BoxGeometry(1,1,1);
  private readonly agents = new THREE.Group();
  private readonly vehicles = new Map<string,VehicleVisual>();
  private readonly motion = new VehicleMotion();
  private viewportWidth=0;
  private viewportHeight=0;
  private readonly vehicleLamp: THREE.MeshBasicMaterial;
  private readonly pedestrianLamp: THREE.MeshBasicMaterial;
  private closed = false;
  private failed = false;
  private readonly lost = (event: Event) => {
    event.preventDefault();
    this.failed = true;
    this.onFailure();
  };

  constructor(private readonly host: HTMLElement, private readonly sourceId: string, private readonly onFailure: () => void) {
    this.renderer = new THREE.WebGLRenderer({antialias: true, alpha: false});
    try {
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      this.renderer.domElement.addEventListener('webglcontextlost', this.lost);
      this.renderer.domElement.style.width = '100%';
      this.renderer.domElement.style.height = '100%';
      this.renderer.domElement.style.display = 'block';
      this.host.appendChild(this.renderer.domElement);
      this.scene.background = new THREE.Color(0x23313c);
      this.scene.add(new THREE.HemisphereLight(0xe8f3ff,0x545c50,2));
      const sun = new THREE.DirectionalLight(0xfff5e6,2.1);
      sun.position.set(-500,900,350);
      this.scene.add(sun);
      for (const s of roadSurfaces()) {
        const p=worldPoint(s.x+s.width/2,s.y+s.height/2,this.sourceId);
        const h=s.kind==='pavement'?6:1;
        this.box(this.scene,p.x,s.elevation-h/2,p.z,s.width,h,s.height,this.material(s.color));
      }
      this.vehicleLamp=new THREE.MeshBasicMaterial({color:0xd14f43});
      this.pedestrianLamp=new THREE.MeshBasicMaterial({color:0xd14f43});
      this.materials.add(this.vehicleLamp);
      this.materials.add(this.pedestrianLamp);
      this.signal(ROAD.width*.36,ROAD.height*.26,this.vehicleLamp);
      this.signal(ROAD.width*.61,ROAD.height*.88,this.pedestrianLamp);
      this.scene.add(this.agents);
    } catch (error) {
      this.dispose();
      throw error;
    }
  }
  private material(color:number|string) {
    const mat=new THREE.MeshStandardMaterial({color,roughness:.85});
    this.materials.add(mat);
    return mat;
  }
  private box(parent:THREE.Object3D,x:number,y:number,z:number,w:number,h:number,d:number,material:THREE.Material) {
    const mesh=new THREE.Mesh(this.geometry,material);
    mesh.position.set(x,y,z);
    mesh.scale.set(w,h,d);
    parent.add(mesh);
    return mesh;
  }
  private signal(x:number,y:number,lamp:THREE.Material) {
    const p=worldPoint(x,y,this.sourceId);
    this.box(this.scene,p.x,47,p.z,9,94,9,this.material(0x74818a));
    this.box(this.scene,p.x,104,p.z,22,34,22,this.material(0x182128));
    this.box(this.scene,p.x,104,p.z,14,15,24,lamp);
    this.box(this.scene,p.x,104,p.z,24,15,14,lamp);
  }
  private clearAgents() {
    for(const child of [...this.agents.children]) {
      child.traverse(obj=>{
        if(obj instanceof THREE.Mesh) {
          const mat=obj.material;
          if(!Array.isArray(mat)&&this.materials.delete(mat)) mat.dispose();
        }
      });
      this.agents.remove(child);
    }
  }
  private clearVehicles() {
    for(const visual of this.vehicles.values())disposeVehicleVisual(visual);
    this.vehicles.clear();
    this.motion.clear();
  }
  isAnimating(now=performance.now()) {return !this.closed&&!this.failed&&this.motion.isAnimating(now);}
  update(snapshot: SimulationScene | null, now=performance.now()) {
    if(this.closed||this.failed)return;
    this.clearAgents();
    const s=snapshot?.source_id===this.sourceId?snapshot:null;
    this.vehicleLamp.color.set(s?.signal.vehicle_go?0x42dc89:s?.signal.phase==='vehicle_yellow'?0xf1c247:0xd14f43);
    this.pedestrianLamp.color.set(s?.signal.pedestrian_walk?0x42dc89:0xd14f43);
    if(!s){this.clearVehicles();return;}
    this.motion.update(s,now);
    const live=new Set<string>();
    for(const v of s.vehicles) {
      if(!this.motion.pose(v.id,now))continue;
      live.add(v.id);
      let visual=this.vehicles.get(v.id);
      if(visual&&visual.signature!==vehicleSignature(v)){disposeVehicleVisual(visual);this.vehicles.delete(v.id);visual=undefined;}
      if(!visual){visual=makeVehicleVisual(v,this.geometry);this.vehicles.set(v.id,visual);this.scene.add(visual.group);}
    }
    for(const [id,visual] of this.vehicles)if(!live.has(id)){disposeVehicleVisual(visual);this.vehicles.delete(id);}
    // Pedestrian geometry/lifecycle is unchanged until Update 25.
    for(const person of s.pedestrians) {
      const p=worldPoint(person.x,person.y,this.sourceId);
      this.box(this.agents,p.x,24,p.z,15,48,15,this.material(person.color));
    }
  }
  render(orbit:number,pitch:number,zoom:number,now=performance.now()) {
    if(this.closed||this.failed)return;
    const w=Math.max(1,this.host.clientWidth),h=Math.max(1,this.host.clientHeight);
    if(w!==this.viewportWidth||h!==this.viewportHeight){this.renderer.setSize(w,h,false);this.viewportWidth=w;this.viewportHeight=h;}
    for(const [id,visual] of this.vehicles){const pose=this.motion.pose(id,now);if(pose){const p=worldPoint(pose.x,pose.y,this.sourceId);visual.group.position.set(p.x,0,p.z);visual.group.rotation.y=mirroredYaw(pose.heading,this.sourceId);}}
    this.camera.aspect=w/h;
    const p=cameraPose(orbit,pitch,zoom);
    this.camera.position.set(p.x,p.y,p.z);
    this.camera.up.set(p.upX,0,p.upZ);
    this.camera.lookAt(0,0,0);
    this.camera.updateProjectionMatrix();
    this.renderer.render(this.scene,this.camera);
  }
  dispose() {
    if(this.closed)return;
    this.closed=true;
    this.renderer.domElement.removeEventListener('webglcontextlost',this.lost);
    this.clearAgents();
    this.clearVehicles();
    this.scene.clear();
    this.geometry.dispose();
    for(const mat of this.materials)mat.dispose();
    this.materials.clear();
    this.renderer.dispose();
    this.renderer.forceContextLoss();
    this.renderer.domElement.remove();
  }
}
