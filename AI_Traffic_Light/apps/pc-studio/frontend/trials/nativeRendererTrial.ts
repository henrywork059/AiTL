import {NativeRoadRenderer} from "../src/components/NativeRoadRenderer";
import type {NativeProjectionScene} from "../src/lib/remoteCameraApi";
const host=document.getElementById("scene")!,result=document.getElementById("result")!,source=document.getElementById("source")!;
const actual=new URLSearchParams(location.search).get("actual")==="1";
const fixture:NativeProjectionScene={schema_version:1,provenance:"synthetic_sumo_projection",generation:1,seed:42,tick:100,time_s:20,width:1280,height:720,pixels_per_m:3.2,
  lanes:[
    {id:"ew",kind:"road",points:[[300,360],[980,360]],width_px:26},
    {id:"ns",kind:"road",points:[[640,24],[640,696]],width_px:26},
    {id:"walk1",kind:"walk",points:[[300,342],[610,342]],width_px:6},
    {id:"walk2",kind:"walk",points:[[610,342],[610,24]],width_px:6},
    {id:"cross1",kind:"crossing",points:[[610,342],[610,378]],width_px:7},
  ],agents:[
    {id:"sumo:vehicle:v0",kind:"vehicle",x:590,y:360,road_id:"WC",speed_m_s:2},
    {id:"sumo:vehicle:v1",kind:"vehicle",x:720,y:360,road_id:"EC",speed_m_s:3},
    {id:"sumo:pedestrian:p0",kind:"pedestrian",x:610,y:350,road_id:":C_c0",speed_m_s:.65}
  ]};
async function run(){
  try{
    let scene=fixture;
    if(actual){
      const response=await fetch("./native-scene.json",{cache:"no-store"});
      if(!response.ok)throw Error("Actual native capture scene missing");
      scene=await response.json() as NativeProjectionScene;
      if(scene.provenance!=="synthetic_sumo_projection"||scene.coordinate_space!=="native_projection_v1"||
         !scene.layout_id||!scene.agents.length||!scene.lanes.length)throw Error("Actual scene identity invalid");
    }
    const renderer=new NativeRoadRenderer(host,"simulation_camera",()=>{result.textContent="MESH_NATIVE_RENDERER_FAIL: context loss";});
    renderer.update(scene);renderer.render(false);
    renderer.render(false,performance.now(),true);
    if(renderer.renderer.info.render.triangles<=0)throw Error("Native detail draw missing");
    renderer.render(false);
    if(renderer.renderer.info.render.triangles<=0||renderer.renderer.info.render.calls<=0)throw Error("No WebGL draw");
    const triangles=renderer.renderer.info.render.triangles;
    renderer.update({...scene,generation:scene.generation-1,agents:[],lanes:[]});
    renderer.render(false);
    if(renderer.renderer.info.render.triangles!==triangles)throw Error("Retired generation replaced active scene");
    if(new URLSearchParams(location.search).get("detail")==="1")renderer.render(false,performance.now(),true);
    source.textContent=(actual?"Executed SUMO capture":"Illustrative native scene fixture")+
      ` · seed ${scene.seed} · ${scene.time_s.toFixed(1)} s · ${scene.agents.length} agents`;
    result.textContent="MESH_NATIVE_RENDERER_PASS";
    window.addEventListener("pagehide",()=>renderer.dispose(),{once:true});
  }catch(error){result.textContent="MESH_NATIVE_RENDERER_FAIL: "+String(error);}
}
void run();
