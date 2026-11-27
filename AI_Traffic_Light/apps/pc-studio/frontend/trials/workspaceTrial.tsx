import {createRoot} from "react-dom/client";
import {flushSync} from "react-dom";
import {AppShell} from "../src/layout/AppShell";
import {DashboardPage} from "../src/pages/DashboardPage";
import {CameraDiagnosticsPage} from "../src/pages/CameraDiagnosticsPage";
import {CrosswalkNetworkPanel} from "../src/components/CrosswalkNetworkPanel";
import {ModelRegistryPage} from "../src/pages/ModelRegistryPage";
import {fallbackRuntimeSettings} from "../src/api";
import type {AppPageId} from "../src/types/app";
import type {CrosswalkConfig} from "../src/types/crosswalks";
import "../src/styles.css";

const page=new URLSearchParams(location.search).get("page")??"dashboard";
const routes:Record<string,AppPageId>={dashboard:"dashboard",diagnostics:"camera_diagnostics",network:"junction_network",models:"model_registry"};
const fixture:CrosswalkConfig={schema_version:1,crosswalks:["North crossing","South crossing"].map((label,i)=>({id:"crossing_"+i,label,location:"Synthetic fixture",camera_side_a_id:null,camera_side_b_id:null,regions:[]}))};
const model={model_id:"fixture_model",model_path:"outputs/training/fixture_model/weights/best.pt",modified_at_ms:0,size_bytes:1048576,is_active:false,is_default:true,is_latest:true};
window.fetch=async input=>{
  const path=new URL(typeof input==="string"?input:input instanceof URL?input.href:input.url,location.href).pathname;
  let data:unknown;
  if(path==="/api/camera/remote/status")data={cameras:[],active_source_id:null};
  else if(path==="/api/models")data={total:1,models:[model],default_model_id:model.model_id,active_model_id:null};
  else if(path==="/api/inference/status")data={model_loaded:false,backend_available:true,active_model_id:null};
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
  const content=page==="diagnostics"?<CameraDiagnosticsPage/>:page==="network"?<CrosswalkNetworkPanel config={fixture} overview={null} onSaved={()=>{}} onRefresh={async()=>{}} simulationEnabled={false}/>:page==="models"?<ModelRegistryPage runtimeSettings={fallbackRuntimeSettings} onSettingsChange={()=>{}}/>:<DashboardPage health={null} smokeStatus={null} cameraStatus={null} apiState={apiState} onRefresh={()=>{}} refreshing={false} onNavigate={id=>{selected=id;}}/>;
  flushSync(()=>root.render(<AppShell activePage={routes[page]} apiState={apiState} cameraStatus={null} onPageChange={id=>{selected=id;}} showSimulationTools={false} onSimulationToolsToggle={()=>{}}>{content}</AppShell>));
  for(let i=0;i<20;i++){if(page!=="models"||document.body.textContent?.includes("fixture_model"))break;await pause();}
  await pause();
  const mobile=innerWidth<=760;
  check(getComputedStyle(document.querySelector(".workspace-mobile-picker")!).display!=="none"===mobile,"Responsive navigation mismatch");
  check(document.documentElement.scrollWidth<=innerWidth+1,"Page-level horizontal overflow");
  if(page==="dashboard"){const b=[...document.querySelectorAll("button")].find(x=>x.textContent==="Open cameras");b?.click();check(selected==="camera_settings","Dashboard action");}
  if(page==="diagnostics"){const b=[...document.querySelectorAll("button")].find(x=>x.textContent==="Diagnose camera");check(b?.disabled,"No camera must prevent diagnostics");}
  if(page==="network"){const s=document.querySelector<HTMLSelectElement>(".workspace-network-controls select")!;s.value="crossing_1";s.dispatchEvent(new Event("change",{bubbles:true}));await pause();check(document.querySelector(".crossing-network-node.is-selected")?.textContent?.includes("South crossing"),"Crossing selection");}
  if(page==="models"){check(document.body.textContent?.includes("fixture_model"),"Fixture model missing");const search=document.querySelector<HTMLInputElement>("input[type=search]")!;const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value")!.set!;setter.call(search,"not_present");search.dispatchEvent(new Event("input",{bubbles:true}));await pause();check(document.body.textContent?.includes("No matching models."),"Model filtering");setter.call(search,"");search.dispatchEvent(new Event("input",{bubbles:true}));await pause();check(document.body.textContent?.includes("fixture_model"),"Filter restoration");}
  result.textContent="MESH_WORKSPACE_PASS · synthetic API fixture";
}
void main().catch(error=>{result.textContent="MESH_WORKSPACE_FAIL: "+String(error);});
