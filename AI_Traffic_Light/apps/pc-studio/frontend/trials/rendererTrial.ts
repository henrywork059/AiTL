import {RoadRenderer} from './RoadRenderer';
import type {SimulationScene} from '../src/lib/remoteCameraApi';
const host=document.getElementById('scene')!;
const result=document.getElementById('result')!;
function check(condition:unknown,message:string) {if(!condition)throw new Error(message);}
const snapshot:SimulationScene={source_id:'simulation_camera',frame_number:1,received_at_ms:0,width:1280,height:720,simulation_time_seconds:0,paused:true,density:'normal',signal:{phase:'vehicle_green',vehicle_go:true,pedestrian_walk:false,seconds_remaining:12},vehicles:[{id:'v1',x:200,y:265,width:140,direction:1,vehicle_type:'car',color:'#e87842'}],pedestrians:[{id:'p1',x:620,y:126,direction:1,color:'#49a8ce'}]};
try {
  for(let i=0;i<2;i++) {
    let losses=0;
    const r=new RoadRenderer(host,'simulation_camera',()=>{losses++;});
    try {
      r.update(snapshot);
      r.render(-25,48,.85);
      const gl=r.renderer.getContext();
      check(gl.drawingBufferWidth>0&&gl.drawingBufferHeight>0,'No drawing buffer');
      check(r.renderer.info.render.calls>10,'Road meshes not rendered');
      r.render(0,0,1);
      check(r.renderer.info.render.calls>10,'Top view empty');
      r.update({...snapshot,source_id:'simulation_camera_b'});
      r.render(45,48,1);
      r.renderer.domElement.dispatchEvent(new Event('webglcontextlost',{cancelable:true}));
      check(losses===1,'Context loss callback not invoked');
    } finally {r.dispose();r.dispose();}
    check(host.querySelectorAll('canvas').length===0,'Leaked canvas');
  }
  const r=new RoadRenderer(host,'simulation_camera',()=>{});
  r.update(snapshot);
  r.render(-25,48,.85);
  result.textContent='MESH_RENDERER_PASS';
  window.addEventListener('pagehide',()=>r.dispose(),{once:true});
} catch(error) {result.textContent='MESH_RENDERER_FAIL: '+String(error);}
