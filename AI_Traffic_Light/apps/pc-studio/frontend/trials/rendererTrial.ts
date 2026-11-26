import {RoadRenderer} from './RoadRenderer';
import * as THREE from 'three';
import {makeVehicleVisual,disposeVehicleVisual,vehicleSignature} from '../src/components/vehicleMeshes';
import type {SimulationScene} from '../src/lib/remoteCameraApi';
const host=document.getElementById('scene')!;
const result=document.getElementById('result')!;
function check(condition:unknown,message:string) {if(!condition)throw new Error(message);}
function verifyPixels(gl: WebGLRenderingContext | WebGL2RenderingContext) {
  const colors = new Set<string>();
  const pixel = new Uint8Array(4);
  for (let y = 1; y <= 9; y++) {
    for (let x = 1; x <= 9; x++) {
      gl.readPixels(Math.floor(gl.drawingBufferWidth * x / 10),
        Math.floor(gl.drawingBufferHeight * y / 10), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixel);
      colors.add([pixel[0], pixel[1], pixel[2]].map(value => Math.floor(value / 8)).join(','));
    }
  }
  check(gl.getError() === gl.NO_ERROR, 'WebGL error during pixel sampling');
  check(colors.size >= 4, 'Rendered road lacks visible color variation: ' + colors.size);
}
const snapshot:SimulationScene={source_id:'simulation_camera',frame_number:1,received_at_ms:0,width:1280,height:720,simulation_time_seconds:0,paused:true,density:'normal',signal:{phase:'vehicle_green',vehicle_go:true,pedestrian_walk:false,seconds_remaining:12},vehicles:[{id:'v1',x:200,y:265,width:140,direction:1,vehicle_type:'car',color:'#e87842'}],pedestrians:[{id:'p1',x:620,y:126,direction:1,color:'#49a8ce'}]};
try {
  const geometry=new THREE.BoxGeometry(1,1,1);
  const styles=['car','suv','van','bus'];
  const visuals=styles.map((vehicle_type,i)=>makeVehicleVisual({...snapshot.vehicles[0],vehicle_type,id:'mesh'+i,width:140+i*30},geometry));
  try {
    check(new Set(visuals.map(v=>v.signature)).size===4,'Missing vehicle variants');
    const heights=visuals.map(v=>new THREE.Box3().setFromObject(v.group).getSize(new THREE.Vector3()).y);
    check(heights.every((v,i)=>i===0||v>heights[i-1]),'Vehicle heights not distinct');
    check(visuals[3].group.children.length>visuals[0].group.children.length,'Bus windows missing');
    check(visuals[0].signature===vehicleSignature(snapshot.vehicles[0]),'Stable signature mismatch');
  } finally {for(const visual of visuals)disposeVehicleVisual(visual);geometry.dispose();}
  for(let i=0;i<2;i++) {
    let losses=0;
    const r=new RoadRenderer(host,'simulation_camera',()=>{losses++;});
    try {
      r.update(snapshot);
      r.render(-25,48,.85);
      const gl=r.renderer.getContext();
      check(gl.drawingBufferWidth>0&&gl.drawingBufferHeight>0,'No drawing buffer');
      check(r.renderer.info.render.calls>10,'Road meshes not rendered');
      verifyPixels(gl);
      r.render(0,0,1);
      check(r.renderer.info.render.calls>10,'Top view empty');
      verifyPixels(gl);
      r.update({...snapshot,source_id:'simulation_camera_b'});
      r.render(45,48,1);
      r.renderer.domElement.dispatchEvent(new Event('webglcontextlost',{cancelable:true}));
      check(losses===1,'Context loss callback not invoked');
    } finally {r.dispose();r.dispose();}
    check(host.querySelectorAll('canvas').length===0,'Leaked canvas');
  }
  const r=new RoadRenderer(host,'simulation_camera',()=>{});
  r.update({...snapshot,vehicles:styles.map((vehicle_type,i)=>({...snapshot.vehicles[0],id:'demo'+i,vehicle_type,x:i%2===0?120:820,y:i<2?265:455,width:140+i*30,direction:i<2?1:-1}))});
  r.render(-25,48,.85);
  result.textContent='MESH_RENDERER_PASS';
  window.addEventListener('pagehide',()=>r.dispose(),{once:true});
} catch(error) {result.textContent='MESH_RENDERER_FAIL: '+String(error);}
