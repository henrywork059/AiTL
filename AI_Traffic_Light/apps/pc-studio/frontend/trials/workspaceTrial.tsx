import {createRoot} from "react-dom/client";
import {flushSync} from "react-dom";
import {AppShell} from "../src/layout/AppShell";
import {DashboardPage} from "../src/pages/DashboardPage";
import {CameraSettingsPage} from "../src/pages/CameraSourcesPage";
import {DEFAULT_REMOTE_CAMERA_SETTINGS} from "../src/lib/remoteCameraApi";
import {CameraDiagnosticsPage} from "../src/pages/CameraDiagnosticsPage";
import {CrosswalkNetworkPanel} from "../src/components/CrosswalkNetworkPanel";
import {ModelRegistryPage} from "../src/pages/ModelRegistryPage";
import {fallbackRuntimeSettings} from "../src/api";
import type {AppPageId} from "../src/types/app";
import type {CrosswalkConfig} from "../src/types/crosswalks";
import "../src/styles.css";

const page=new URLSearchParams(location.search).get("page")??"dashboard";
const routes:Record<string,AppPageId>={dashboard:"dashboard",cameras:"camera_settings",diagnostics:"camera_diagnostics",network:"junction_network",models:"model_registry"};
const fixture:CrosswalkConfig={schema_version:1,crosswalks:["North crossing","South crossing"].map((label,i)=>({id:"crossing_"+i,label,location:"Synthetic fixture",camera_side_a_id:null,camera_side_b_id:null,regions:[]}))};
const model={model_id:"fixture_model",model_path:"outputs/training/fixture_model/weights/best.pt",modified_at_ms:0,size_bytes:1048576,is_active:false,is_default:true,is_latest:true};
let activeModel=false, modelFailure=false, savedNetwork=fixture;
let savedCount=0;
const profiles=["camera_a","camera_b"].map((source_id,i)=>({source_id,host:"192.168.1."+(80+i),kind:"esp32",selected:i===0,connected:false,streaming:false,device_reachable:false,target_fps:15,settings:DEFAULT_REMOTE_CAMERA_SETTINGS}));
window.fetch=async (input,init)=>{
  const path=new URL(typeof input==="string"?input:input instanceof URL?input.href:input.url,location.href).pathname;
  let data:unknown;
  if(path==="/api/camera/remote/status")data=page==="cameras"?{cameras:profiles,active_source_id:"camera_a",camera_count:2,max_saved_cameras:12}: {cameras:[],active_source_id:null};
  else if(path==="/api/models"){if(modelFailure)return new Response(JSON.stringify({ok:false,error:{code:"FIXTURE",message:"Model registry unavailable"}}),{status:503,headers:{"Content-Type":"application/json"}});data={total:1,models:[{...model,is_active:activeModel}],default_model_id:model.model_id,active_model_id:activeModel?model.model_id:null};}
  else if(path==="/api/inference/load"){check(JSON.parse(String(init?.body)).model_id===model.model_id,"Wrong load model");activeModel=true;data={model_loaded:true,backend_available:true,active_model_id:model.model_id};}
  else if(path==="/api/crosswalks"){if(init?.method==="PUT"){savedNetwork=JSON.parse(String(init.body)).config;savedCount++;}data=savedNetwork;}
  else if(path==="/api/inference/status")data={model_loaded:activeModel,backend_available:true,active_model_id:activeModel?model.model_id:null};
  else if(path==="/api/traffic/crosswalk-signals")data={simulation_only:true,simulation_enabled:false,hardware_actuation_enabled:false,crosswalks:{}};
  else throw Error("Unexpected fixture request "+path);
  return new Response(JSON.stringify({ok:true,data}),{headers:{"Content-Type":"application/json"}});
};
const root=createRoot(document.getElementById("root")!);
const result=document.getElementById("result")!;
const apiState={status:"connected" as const,message:"Synthetic browser fixture"};
let selected="";
const check=(ok:unknown,reason:string)=>{if(!ok)throw Error(reason);};
const pause=()=>new Promise(resolve=>setTimeout(resolve,50));
async function main(){
  const content=page==="cameras"?<CameraSettingsPage status={null} showSimulationTools={false} onSimulationChange={()=>{}} onStatusChange={()=>{}} changingMode={false}/>:page==="diagnostics"?<CameraDiagnosticsPage/>:page==="network"?<CrosswalkNetworkPanel config={fixture} overview={null} onSaved={()=>{}} onRefresh={async()=>{}} simulationEnabled={false}/>:page==="models"?<ModelRegistryPage runtimeSettings={fallbackRuntimeSettings} onSettingsChange={()=>{}}/>:<DashboardPage health={null} smokeStatus={null} cameraStatus={null} apiState={apiState} onRefresh={()=>{}} refreshing={false} onNavigate={id=>{selected=id;}}/>;
  flushSync(()=>root.render(<AppShell activePage={routes[page]} apiState={apiState} cameraStatus={null} onPageChange={id=>{selected=id;}} showSimulationTools={false} onSimulationToolsToggle={()=>{}}>{content}</AppShell>));
  for(let i=0;i<20;i++){if((page!=="models"||document.body.textContent?.includes("fixture_model"))&&(page!=="cameras"||document.body.textContent?.includes("camera_b")))break;await pause();}
  await pause();
  const mobile=innerWidth<=760;
  check(getComputedStyle(document.querySelector(".workspace-mobile-picker")!).display!=="none"===mobile,"Responsive navigation mismatch");
  check(document.documentElement.scrollWidth<=innerWidth+1,"Page-level horizontal overflow");
  if(page==="dashboard"){check(document.body.textContent?.includes("No verified checks"),"Missing validation must not appear as zero");const b=[...document.querySelectorAll("button")].find(x=>x.textContent==="Open cameras");b?.click();check(selected==="camera_settings","Dashboard action");}
  if(page==="cameras"){check(document.querySelectorAll(".camera-status-entry").length===2,"Two saved cameras missing");const start=[...document.querySelectorAll("button")].find(x=>x.textContent==="Start Stream");check(start?.disabled,"Disconnected camera start must be disabled");check(document.querySelector<HTMLDetailsElement>(".camera-fold")?.open,"Device setup collapsed");}
  if(page==="diagnostics"){const b=[...document.querySelectorAll("button")].find(x=>x.textContent==="Diagnose camera");check(b?.disabled,"No camera must prevent diagnostics");}
  if(page==="network"){const s=document.querySelector<HTMLSelectElement>(".workspace-network-controls select")!;s.value="crossing_1";s.dispatchEvent(new Event("change",{bubbles:true}));await pause();check(document.querySelector(".crossing-network-node.is-selected")?.textContent?.includes("South crossing"),"Crossing selection");const scroll=document.querySelector<HTMLElement>(".crossing-network-scroll")!;if(scroll.scrollWidth>scroll.clientWidth)check(scroll.scrollLeft>0,"Selected crossing not revealed");for(const [id,edge] of [["crossing_0","2"],["crossing_1","4"]]){document.querySelector(`[data-crosswalk-id="${id}"][data-crosswalk-edge="${edge}"]`)!.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",bubbles:true}));await pause();}const save=[...document.querySelectorAll("button")].find(b=>b.textContent==="Save network")!;check(!save.disabled,"Keyboard link did not mark draft dirty");save.click();for(let i=0;i<20&&savedCount===0;i++)await pause();check(savedCount===1&&savedNetwork.network?.links.length===1&&savedNetwork.network.links[0].source_edge==="2"&&savedNetwork.crosswalks.length===2,"Network save contract");await pause();}
  if(page==="models"){check(document.body.textContent?.includes("fixture_model"),"Fixture model missing");const search=document.querySelector<HTMLInputElement>("input[type=search]")!;const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value")!.set!;setter.call(search,"not_present");search.dispatchEvent(new Event("input",{bubbles:true}));await pause();check(document.body.textContent?.includes("No matching models."),"Model filtering");setter.call(search,"");search.dispatchEvent(new Event("input",{bubbles:true}));await pause();check(document.body.textContent?.includes("fixture_model"),"Filter restoration");const load=[...document.querySelectorAll("button")].find(b=>b.textContent==="Load model")!;load.click();for(let i=0;i<20&&!load.disabled;i++)await pause();await pause();check(activeModel&&document.querySelector(".model-list-grid")?.textContent?.includes("active"),"Model activation");modelFailure=true;const refresh=[...document.querySelectorAll("button")].find(b=>b.textContent==="Refresh")!;refresh.click();for(let i=0;i<20&&!document.body.textContent?.includes("Model registry unavailable or loading.");i++)await pause();check(document.body.textContent?.includes("Model registry unavailable or loading.")&&!document.body.textContent?.includes("No trained models were found"),"Registry error rendered as empty");modelFailure=false;[...document.querySelectorAll("button")].find(b=>b.textContent==="Refresh")?.click();for(let i=0;i<20&&!document.querySelector(".model-list-grid")?.textContent?.includes("fixture_model");i++)await pause();check(document.querySelector(".model-list-grid")?.textContent?.includes("fixture_model"),"Model recovery");}
  result.textContent="MESH_WORKSPACE_PASS · synthetic API fixture";
}
void main().catch(error=>{result.textContent="MESH_WORKSPACE_FAIL: "+String(error);});
