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
const originalFetch = window.fetch;
window.fetch = async (input) => {
  const url = new URL(typeof input === "string" ? input : input instanceof URL ? input.href : input.url, location.href);
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
    flushSync(()=>root.unmount());
    check(!canvas(),"Canvas leaked after unmount");
    result.textContent="MESH_INTEGRATION_PASS";
  } catch(error){result.textContent="MESH_INTEGRATION_FAIL: "+String(error);flushSync(()=>root.unmount());}
  finally {window.fetch=originalFetch;}
}
void run();
