import { createRoot } from "react-dom/client";
import { flushSync } from "react-dom";
import { SimulationCamera3D } from "../src/components/SimulationCamera3D";
import type { SimulationScene } from "../src/lib/remoteCameraApi";
import type { Zone } from "../src/types";

const host = document.getElementById("root")!;
const result = document.getElementById("result")!;
const root = createRoot(host);
const zones: Zone[] = [{ id: "z1", type: "crossing", label: "Crossing", polygon: [[520,179],[760,179],[760,625],[520,625]] }];
const sample: SimulationScene = {source_id:"simulation_camera",frame_number:1,received_at_ms:0,width:1280,height:720,simulation_time_seconds:0,paused:true,density:"normal",signal:{phase:"vehicle_green",vehicle_go:true,pedestrian_walk:false,seconds_remaining:12},vehicles:[{id:"v1",x:200,y:265,width:140,direction:1,vehicle_type:"car",color:"#e87842"}],pedestrians:[{id:"p1",x:620,y:126,direction:1,color:"#49a8ce"}]};
let generation = 1;
let nativeTick = 1;
let nativeStatus = "running";
let nativeCalls = 0;
let evalGeneration=0,evalTick=0,evalRunning=false,evalPaused=false,evalCalls=0;
const layoutId="b".repeat(64);
const originalFetch = window.fetch;
window.fetch = async (input,init) => {
  const url = new URL(typeof input === "string" ? input : input instanceof URL ? input.href : input.url, location.href);
  if(url.pathname.startsWith("/api/camera/simulation/native-evaluation")){
    evalCalls++;
    const command=url.pathname.split("/").pop();
    if(init?.method==="POST"){
      const body=JSON.parse(String(init.body));
      if(body.generation!==evalGeneration||body.epoch!=="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")throw Error("Wrong evaluation identity");
      if(command==="region"){
        if(body.layout_id!==layoutId||body.coordinate_space!=="native_projection_v1"||body.tick!==evalTick||body.polygon.length!==4)throw Error("Wrong region identity");
        return new Response(JSON.stringify({ok:true,data:{counts:{vehicle:0,pedestrian:1},agent_ids:["p0"],epoch:body.epoch,generation:evalGeneration,tick:evalTick,source_id:body.source_id,layout_id:layoutId,persisted:false}}),{headers:{"Content-Type":"application/json"}});
      }
      if(command==="start"){evalGeneration++;evalTick=0;evalRunning=true;evalPaused=false;}
      if(command==="step"){if(evalPaused||body.tick!==evalTick)throw Error("Wrong step");evalTick+=body.steps;}
      if(command==="pause"){evalPaused=body.paused;}
      if(command==="stop"){evalGeneration++;evalRunning=false;}
    }
    return new Response(JSON.stringify({ok:true,data:{status:evalRunning?"running":"idle",provenance:"synthetic_sumo_projection",epoch:"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",generation:evalGeneration,mode:"fixed",density:"normal",max_ticks:2500,native_only:true,physical_output_allowed:false,
      snapshot:evalRunning?{schema_version:1,provenance:"synthetic_sumo_projection",generation:evalGeneration,tick:evalTick,time_s:evalTick/5,width:1280,height:720,paused:evalPaused,pixels_per_m:3.2,coordinate_space:"native_projection_v1",layout_id:layoutId,legacy_editor_compatible:false,lanes:[{id:"eval-road",kind:"road",points:[[20,100],[1000,100]],width_px:12}],agents:[{id:"sumo:pedestrian:p0",kind:"pedestrian",x:100+evalTick,y:100,road_id:"WC",speed_m_s:.65}]}:null}}),{headers:{"Content-Type":"application/json"}});
  }
  if (url.pathname === "/api/camera/simulation/native-projection") {
    nativeCalls++;
    if (url.searchParams.get("format") !== "scene") throw new Error("Unexpected native format");
    return new Response(JSON.stringify({ok:true,data:{status:nativeStatus,provenance:"synthetic_sumo_projection",generation,
      snapshot:nativeStatus==="running"?{schema_version:1,provenance:"synthetic_sumo_projection",generation,tick:nativeTick,
        time_s:nativeTick/5,width:1280,height:720,lanes:[{id:"native-road",kind:"road",points:[[20,100],[1000,100]],width_px:12}],
        agents:[{id:"sumo:vehicle:v1",kind:"vehicle",x:100+nativeTick,y:100,road_id:"WC",speed_m_s:2}]}:null}}),
      {headers:{"Content-Type":"application/json"}});
  }
  if (url.pathname !== "/api/camera/simulation/scene") throw new Error("Unexpected trial request: " + url.pathname);
  return new Response(JSON.stringify({ok:true,data:{...sample,source_id:url.searchParams.get("source_id")}}),{headers:{"Content-Type":"application/json"}});
};
const check = (condition:unknown,message:string) => { if(!condition) throw new Error(message); };
const wait = async (predicate:()=>boolean,message:string) => {
  for(let i=0;i<100;i++){if(predicate())return;await new Promise(resolve=>setTimeout(resolve,20));}
  throw new Error(message);
};
const mode = () => host.querySelector("[data-renderer]")?.getAttribute("data-renderer");
const canvas = () => host.querySelector("canvas");
const button = (label:string) => Array.from(host.querySelectorAll("button")).find(b=>b.textContent===label);
const mount = (sourceId="simulation_camera",editing=false,overlay=false) =>
  flushSync(()=>root.render(<SimulationCamera3D sourceId={sourceId} editing={editing} zones={overlay?zones:[]} />));
async function run(){
  try{
    mount();
    await wait(()=>Boolean(button("Three.js preview")&&!button("Three.js preview")!.disabled),"Scene did not load");
    check(mode()==="legacy"&&!canvas(),"Default must be legacy");
    button("Three.js preview")!.click();
    await wait(()=>mode()==="three"&&Boolean(canvas()),"Three.js did not mount");
    const first=canvas();
    button("Top")!.click();
    await wait(()=>Boolean(button("Perspective")),"Top view control failed");
    mount("simulation_camera_b");
    await wait(()=>mode()==="three"&&Boolean(canvas())&&canvas()!==first,"Camera switch did not replace renderer");
    mount("simulation_camera_b",true);
    check(mode()==="legacy"&&!canvas()&&Boolean(host.querySelector(".sim3d-world")),"Editor did not preserve legacy source plane");
    mount("simulation_camera_b",false,true);
    check(mode()==="legacy"&&!canvas()&&Boolean(host.querySelector(".sim3d-world-overlay polygon")),"Overlay fallback failed");
    mount("simulation_camera_b");
    await wait(()=>mode()==="three"&&Boolean(canvas()),"Three.js did not resume");
    canvas()!.dispatchEvent(new Event("webglcontextlost",{cancelable:true}));
    await wait(()=>mode()==="legacy"&&!canvas()&&Boolean(button("Retry Three.js")),"Context loss did not recover");
    button("Retry Three.js")!.click();
    await wait(()=>mode()==="three"&&Boolean(canvas()),"Retry did not restore canvas");
    button("Legacy view")!.click();
    await wait(()=>mode()==="legacy"&&!canvas(),"Manual rollback failed");
    check(nativeCalls===0,"Native requested without opt-in");
    button("Native SUMO preview")!.click();
    const agent=()=>host.querySelector("[data-native-agent]");
    await wait(()=>mode()==="native"&&Boolean(agent()),"Native preview did not mount");
    const firstAgent=agent();
    nativeTick=2;
    await wait(()=>host.querySelector("[data-native-tick='2']")!==null,"Native tick did not update");
    check(agent()===firstAgent,"Native identity did not persist");
    nativeTick=1;
    const before=nativeCalls;
    await wait(()=>nativeCalls>before,"Native poll did not occur");
    await new Promise(resolve=>setTimeout(resolve,30));
    check(Boolean(host.querySelector("[data-native-tick='2']")),"Older tick replaced scene");
    generation=2; nativeTick=0;
    await wait(()=>Boolean(host.querySelector("[data-native-generation='2']")),"Generation reset failed");
    check(agent()!==firstAgent,"Generation retained old DOM agent");
    generation=1; nativeTick=99;
    const oldGenerationCall=nativeCalls;
    await wait(()=>nativeCalls>oldGenerationCall,"Old generation poll missing");
    await new Promise(resolve=>setTimeout(resolve,30));
    check(Boolean(host.querySelector("[data-native-generation='2']")),"Older generation replaced scene");
    generation=2; nativeTick=0;
    for(const [sid,transform] of [["simulation_camera",""],["simulation_camera_b","translate(0 719) scale(1 -1)"],["simulation_camera_c","translate(1279 0) scale(-1 1)"],["simulation_camera_d","translate(1279 719) scale(-1 -1)"]]){
      mount(sid);
      await wait(()=>host.querySelector("[data-native-lane]")?.parentElement?.getAttribute("transform")===transform,"Native camera transform failed");
    }
    button("Native 3D")!.click();
    await wait(()=>Boolean(host.querySelector("canvas[data-native-webgl]")),"Native volumetric view did not mount");
    const nativeCanvas=host.querySelector("canvas[data-native-webgl]");
    nativeTick=1;
    const native3dCalls=nativeCalls;
    await wait(()=>nativeCalls>native3dCalls,"Native 3D poll did not occur");
    check(host.querySelector("canvas[data-native-webgl]")===nativeCanvas,"Native 3D canvas remounted within generation");
    nativeCanvas!.dispatchEvent(new Event("webglcontextlost",{cancelable:true}));
    await wait(()=>Boolean(agent())&&!host.querySelector("canvas[data-native-webgl]"),"Native WebGL loss did not fall back");
    nativeStatus="unavailable";
    await wait(()=>!agent()&&Boolean(host.querySelector("[data-native-status='unavailable']")),"Unavailable native retained agents");
    button("Exit native preview")!.click();
    await wait(()=>mode()==="legacy","Native rollback failed");
    const retiredCalls=nativeCalls;
    await new Promise(resolve=>setTimeout(resolve,650));
    check(nativeCalls===retiredCalls,"Native poll continued after exit");
    nativeStatus="running";
    button("Native SUMO preview")!.click();
    await wait(()=>Boolean(agent()),"Native retry failed");
    button("Standalone evaluation")!.click();
    await wait(()=>Boolean(button("Start evaluation")),"Standalone controls not loaded");
    button("Start evaluation")!.click();
    await wait(()=>Boolean(button("Advance 5 s")&&!button("Advance 5 s")!.disabled),"Standalone start failed");
    button("Advance 5 s")!.click();
    await wait(()=>Boolean(host.querySelector("[data-native-tick='25']")),"Standalone step failed");
    await wait(()=>Boolean(button("Play evaluation")&&!button("Play evaluation")!.disabled),"Standalone playback unavailable");
    button("Play evaluation")!.click();
    await wait(()=>evalTick>=27,"Native playback did not advance");
    button("Stop playback")!.click();
    await wait(()=>Boolean(button("Play evaluation")),"Playback stop failed");
    await new Promise(resolve=>setTimeout(resolve,250));
    const stoppedTick=evalTick;
    await new Promise(resolve=>setTimeout(resolve,650));
    check(evalTick===stoppedTick,"Native playback continued after stop");
    await wait(()=>Boolean(button("Pause evaluation")&&!button("Pause evaluation")!.disabled),"Standalone pause unavailable");
    button("Pause evaluation")!.click();
    await wait(()=>Boolean(button("Resume evaluation")&&button("Advance 5 s")!.disabled),"Standalone pause failed");
    await wait(()=>Boolean(button("Draft region")&&!button("Draft region")!.disabled),"Native draft unavailable");
    button("Draft region")!.click();
    await wait(()=>Boolean(host.querySelector("[data-native-region-editor]")),"Native draft did not open");
    const editor=host.querySelector("[data-native-region-editor]") as SVGSVGElement;
    for(const [i,p] of [[100,100],[300,100],[300,300],[100,300]].entries()){
      const screen=new DOMPoint(p[0],p[1]).matrixTransform(editor.getScreenCTM()!);
      editor.dispatchEvent(new PointerEvent("pointerdown",{bubbles:true,clientX:screen.x,clientY:screen.y,pointerId:1}));
      await wait(()=>editor.querySelectorAll("circle").length===i+1,"Draft vertex not recorded");
    }
    button("Evaluate draft")!.click();
    await wait(()=>Boolean(host.textContent?.includes("Vehicles 0 · Pedestrians 1")),"Native draft result missing");
    button("Close draft")!.click();
    await wait(()=>!host.querySelector("[data-native-region-editor]"),"Native draft retirement failed");
    await wait(()=>Boolean(button("Stop evaluation")&&!button("Stop evaluation")!.disabled),"Standalone stop unavailable");
    button("Stop evaluation")!.click();
    await wait(()=>!agent()&&Boolean(button("Start evaluation")),"Standalone stop failed");
    button("Shadow preview")!.click();
    await wait(()=>Boolean(agent()),"Shadow rollback failed");
    const evalRetired=evalCalls;
    mount("simulation_camera_d",true);
    check(mode()==="legacy"&&!agent()&&Boolean(host.querySelector(".sim3d-world")),"Native editor fallback failed");
    const editorCalls=nativeCalls;
    await new Promise(resolve=>setTimeout(resolve,650));
    check(nativeCalls===editorCalls,"Native poll continued in editor");
    check(evalCalls===evalRetired,"Standalone poll continued after rollback");
    // Reopen and leave while actively playing; retire both command and poll scope.
    mount("simulation_camera");
    await wait(()=>Boolean(button("Native SUMO preview")&&!button("Native SUMO preview")!.disabled),"Native preview unavailable after editor");
    button("Native SUMO preview")!.click();
    await wait(()=>Boolean(button("Standalone evaluation")),"Standalone selector missing");
    button("Standalone evaluation")!.click();
    await wait(()=>Boolean(button("Start evaluation")),"Standalone restart missing");
    button("Start evaluation")!.click();
    await wait(()=>Boolean(button("Play evaluation")&&!button("Play evaluation")!.disabled),"Restart play unavailable");
    button("Play evaluation")!.click();
    await wait(()=>evalTick>=2,"Restart playback failed");
    mount("simulation_camera",true);
    await new Promise(resolve=>setTimeout(resolve,250));
    const retiredTick=evalTick,retiredEvalCalls=evalCalls;
    await new Promise(resolve=>setTimeout(resolve,650));
    check(evalTick===retiredTick&&evalCalls===retiredEvalCalls,"Playback or polling survived editor rollback");
    flushSync(()=>root.unmount());
    check(!canvas(),"Canvas leaked after unmount");
    result.textContent="MESH_INTEGRATION_PASS";
  } catch(error){result.textContent="MESH_INTEGRATION_FAIL: "+String(error);flushSync(()=>root.unmount());}
  finally {window.fetch=originalFetch;}
}
void run();
