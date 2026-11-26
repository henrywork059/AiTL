import * as THREE from "three";
import type { VehicleObservation } from "./vehicleMotion";

const STYLES = {
  car: {depth:58,height:22,cabin:0.48,cabinHeight:17,cabinOffset:-0.04,windows:2},
  suv: {depth:64,height:27,cabin:0.67,cabinHeight:23,cabinOffset:-0.06,windows:2},
  van: {depth:70,height:30,cabin:0.84,cabinHeight:28,cabinOffset:-0.03,windows:1},
  bus: {depth:78,height:37,cabin:0.91,cabinHeight:35,cabinOffset:0,windows:5},
};
export type VehicleVisual = { group: THREE.Group; materials: THREE.Material[]; signature: string };
export const vehicleSignature = (v: VehicleObservation) => JSON.stringify([v.vehicle_type,v.width,v.color]);
/** Geometry is shared by the renderer; each vehicle owns and disposes its own materials. Front is +X. */
export function makeVehicleVisual(v: VehicleObservation, geometry: THREE.BoxGeometry): VehicleVisual {
  const style=STYLES[v.vehicle_type as keyof typeof STYLES]??STYLES.car;
  const group=new THREE.Group();
  group.name=v.id;
  const materials: THREE.Material[]=[];
  const material=(color:number|string,roughness=.7)=>{
    const m=new THREE.MeshStandardMaterial({color,roughness});materials.push(m);return m;
  };
  const body=material(v.color),glass=material(0x28495f,.3),tire=material(0x15191d),rim=material(0x89949d),
    white=material(0xfff0ca),red=material(0xb92f36),trim=material(0x28313a);
  const box=(x:number,y:number,z:number,w:number,h:number,d:number,m:THREE.Material)=>{
    const mesh=new THREE.Mesh(geometry,m);mesh.position.set(x,y,z);mesh.scale.set(w,h,d);group.add(mesh);
  };
  const length=v.width,depth=style.depth,base=style.height,roof=style.cabinHeight,cabin=length*style.cabin,offset=length*style.cabinOffset;
  box(0,base/2+9,0,length,base,depth,body);
  box(offset,base+9+roof/2,0,cabin,roof,depth*.87,body);
  // Front/rear windshield panels and separate side windows; no external assets.
  box(offset+cabin/2+.5,base+9+roof*.55,0,1,roof*.62,depth*.78,glass);
  box(offset-cabin/2-.5,base+9+roof*.55,0,1,roof*.62,depth*.78,glass);
  for(let i=0;i<style.windows;i++){
    const x=offset-cabin/2+cabin*(i+.5)/style.windows;
    for(const side of [-1,1])box(x,base+9+roof*.55,side*(depth*.435+.5),cabin/style.windows*.76,roof*.56,1,glass);
  }
  for(const x of [-length*.31,length*.31])for(const side of [-1,1]){
    box(x,8,side*depth*.47,Math.min(24,length*.16),16,11,tire);
    box(x,8,side*(depth*.47+6),Math.min(12,length*.08),9,2,rim);
  }
  for(const side of [-1,1]){
    box(length/2+.5,base*.72+9,side*depth*.33,1,7,depth*.22,white);
    box(-length/2-.5,base*.72+9,side*depth*.33,1,7,depth*.22,red);
  }
  box(length/2+.5,12,0,2,5,depth*.7,trim);
  return {group,materials,signature:vehicleSignature(v)};
}
export function disposeVehicleVisual(visual: VehicleVisual) {
  visual.group.removeFromParent();for(const material of visual.materials)material.dispose();
}
