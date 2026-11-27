import * as THREE from "three";
import type { PedestrianObservation } from "./pedestrianMotion";
export type PedestrianVisual={group:THREE.Group;materials:THREE.Material[];arms:THREE.Group[];legs:THREE.Group[];color:string};
/** Volumetric procedural figure, local +X facing forward. Shared geometry, owned materials. */
export function makePedestrianVisual(p:PedestrianObservation,box:THREE.BoxGeometry,round:THREE.SphereGeometry):PedestrianVisual {
  const group=new THREE.Group();group.name=p.id;
  const materials:THREE.Material[]=[];
  const mat=(color:number|string)=>{const m=new THREE.MeshStandardMaterial({color,roughness:.8});materials.push(m);return m;};
  const clothing=mat(p.color),skin=mat(0xc89c79),pants=mat(0x35445b),shoe=mat(0x232932),hair=mat(0x40312b);
  const part=(parent:THREE.Object3D,geometry:THREE.BufferGeometry,m:THREE.Material,x:number,y:number,z:number,w:number,h:number,d:number)=>{
    const mesh=new THREE.Mesh(geometry,m);mesh.position.set(x,y,z);mesh.scale.set(w,h,d);parent.add(mesh);
  };
  part(group,box,clothing,0,32,0,10,19,17);
  part(group,box,skin,0,43,0,5,5,6);
  part(group,round,skin,0,49,0,6,7,6);
  part(group,round,hair,-1,52,0,6,4,6);
  const arms:THREE.Group[]=[],legs:THREE.Group[]=[];
  for(const side of [-1,1]){
    const arm=new THREE.Group();arm.position.set(0,39,side*10);group.add(arm);arms.push(arm);
    part(arm,box,clothing,0,-6,0,5,12,5);part(arm,box,skin,0,-14,0,4,6,4);
    const leg=new THREE.Group();leg.position.set(0,23,side*4.5);group.add(leg);legs.push(leg);
    part(leg,box,pants,0,-10,0,6,20,7);part(leg,box,shoe,2,-21,0,10,4,7);
  }
  return {group,materials,arms,legs,color:p.color};
}
export function setPedestrianGait(v:PedestrianVisual,swing:number){
  for(let i=0;i<2;i++){
    const angle=(i===0?1:-1)*swing;
    v.legs[i].rotation.z=angle*.38;v.arms[i].rotation.z=-angle*.32;
  }
}
export function disposePedestrianVisual(v:PedestrianVisual){v.group.removeFromParent();for(const m of v.materials)m.dispose();}
