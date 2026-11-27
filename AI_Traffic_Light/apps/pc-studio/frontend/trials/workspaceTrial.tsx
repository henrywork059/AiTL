import {useState} from "react";
import type {CameraStatus} from "../src/types";
import {createRoot} from "react-dom/client";
import {flushSync} from "react-dom";
import {AppShell} from "../src/layout/AppShell";
import {DashboardPage} from "../src/pages/DashboardPage";
import {CameraSettingsPage} from "../src/pages/CameraSourcesPage";
import {DEFAULT_REMOTE_CAMERA_SETTINGS} from "../src/lib/remoteCameraApi";
import {CameraDiagnosticsPage} from "../src/pages/CameraDiagnosticsPage";
import {CrosswalkNetworkPanel} from "../src/components/CrosswalkNetworkPanel";
import {DatasetReviewPage} from "../src/pages/DatasetReviewPage";
import {ModelRegistryPage} from "../src/pages/ModelRegistryPage";
import {fetchCrosswalks} from "../src/lib/crosswalksApi";
import {fallbackRuntimeSettings} from "../src/api";
import type {AppPageId} from "../src/types/app";
import type {CrosswalkConfig} from "../src/types/crosswalks";
import "../src/styles.css";

const page=new URLSearchParams(location.search).get("page")??"dashboard";
const routes:Record<string,AppPageId>={dashboard:"dashboard",cameras:"camera_settings",diagnostics:"camera_diagnostics",network:"junction_network",models:"model_registry",review:"dataset_review"};
const fixture:CrosswalkConfig={schema_version:1,crosswalks:["North crossing","South crossing"].map((label,i)=>({id:"crossing_"+i,label,location:"Synthetic fixture",camera_side_a_id:i===0?"fixture_a":null,camera_side_b_id:null,regions:[]}))};
const model={model_id:"fixture_model",model_path:"outputs/training/fixture_model/weights/best.pt",modified_at_ms:0,size_bytes:1048576,is_active:false,is_default:true,is_latest:true};
const classes=[{id:0,name:"vehicle"}];
const captureList=["cap_a","cap_b"].map(id=>({capture_id:id,session_id:id,quality_tag:"good",origin:"synthetic",width:1280,height:720,labeled:false,label_count:0}));
const labelDocs=Object.fromEntries(captureList.map(c=>[c.capture_id,{capture_id:c.capture_id,session_id:c.session_id,image_path:"fixture",width:c.width,height:c.height,reviewed:false,updated_at_ms:null,labels:c.capture_id==="cap_a"?[{class_id:0,class_name:"vehicle",box_xyxy:[10,10,20,20]}]:[]} ]));
let labelFailure=true, imageFailure=true, labelSaves=0, imageVariant:"valid"|"wrong-size"|"invalid"="valid";
let captureBImageRequests=0;
// Encode once synchronously: canvas.toBlob callbacks can be delayed by headless virtual time.
const fixtureImage=(width=1280,height=720)=>{const canvas=document.createElement("canvas");canvas.width=width;canvas.height=height;const ctx=canvas.getContext("2d")!;ctx.fillStyle="#dae4e8";ctx.fillRect(0,0,width,height);ctx.fillStyle="#59636c";ctx.fillRect(0,250,width,220);ctx.fillStyle="#ffffff";ctx.font="32px sans-serif";ctx.fillText("Synthetic empty road fixture",40,100);const bytes=Uint8Array.from(atob(canvas.toDataURL("image/png").split(",")[1]),char=>char.charCodeAt(0));return new Blob([bytes],{type:"image/png"});};
const validFixtureImage=fixtureImage(), wrongSizeFixtureImage=fixtureImage(640,360), invalidFixtureImage=new Blob(["not an image"],{type:"image/png"});
let activeModel=false, modelFailure=false, savedNetwork=fixture;
let savedCount=0, readCount=0, selectedCamera="camera_a", failProbe=true;
const profiles=["camera_a","camera_b"].map((source_id,i)=>({source_id,host:"192.168.1."+(80+i),kind:"esp32",selected:i===0,connected:false,streaming:false,device_reachable:false,target_fps:15,settings:DEFAULT_REMOTE_CAMERA_SETTINGS,last_error:null as string|null,stream_connected:false,measured_fps:0,paused_for_simulation:false}));
const remoteState=()=>({cameras:profiles.map(p=>({...p,selected:p.source_id===selectedCamera})),active_source_id:selectedCamera,camera_count:2,max_saved_cameras:12,source_id:selectedCamera,host:profiles.find(p=>p.source_id===selectedCamera)?.host});
const fixtureError=(message:string)=>new Response(JSON.stringify({ok:false,error:{code:"FIXTURE",message}}),{status:503,headers:{"Content-Type":"application/json"}});
window.fetch=async (input,init)=>{
  const path=new URL(typeof input==="string"?input:input instanceof URL?input.href:input.url,location.href).pathname;
  let data:unknown;
  if(path==="/api/camera/remote/status")data=page==="cameras"?remoteState(): {cameras:[],active_source_id:null};
  else if(path==="/api/camera/remote/select"){selectedCamera=JSON.parse(String(init?.body)).source_id;check(profiles.some(p=>p.source_id===selectedCamera),"Wrong camera identity");data=remoteState();}
  else if(path==="/api/camera/remote/cameras"){const body=JSON.parse(String(init?.body));check(body.source_id===selectedCamera&&body.host===profiles.find(p=>p.source_id===selectedCamera)?.host,"Camera profile mismatch");data=remoteState();}
  else if(path==="/api/camera/remote/connect"){const body=JSON.parse(String(init?.body));check(body.source_id===selectedCamera,"Wrong connection target");const p=profiles.find(p=>p.source_id===selectedCamera)!;if(failProbe){p.last_error="Fixture ESP unreachable";return fixtureError(p.last_error);}p.last_error=null;p.connected=true;p.device_reachable=true;data=remoteState();}
  else if(path==="/api/camera/remote/start"||path==="/api/camera/remote/stop"){const p=profiles.find(p=>p.source_id===selectedCamera)!;check(p.connected,"Stream requested without connection");p.streaming=path.endsWith("/start");data=remoteState();}
  else if(path==="/api/camera/status")data={mode:"receiver",simulation_enabled:false,simulation_paused:false,frame_available:false,stale:true,streaming:profiles.find(p=>p.source_id===selectedCamera)?.streaming??false,active_source_id:selectedCamera,resolution:null,age_ms:null,frame_url:null};
  else if(path==="/api/dataset/captures")data={captures:captureList,total:2,classes};
  else if(path.startsWith("/api/dataset/captures/")&&path.endsWith("/image")){const id=path.split("/")[4];if(id==="cap_b"){captureBImageRequests++;if(imageFailure)return fixtureError("Fixture image unavailable");}const blob=id!=="cap_b"||imageVariant==="valid"?validFixtureImage:imageVariant==="wrong-size"?wrongSizeFixtureImage:invalidFixtureImage;return new Response(blob,{headers:{"Content-Type":"image/png"}});}
  else if(path==="/api/dataset/training-dataset/status")data={ready:false,stale:false,eligible_frame_count:0,labeled_frame_count:0,label_box_count:0,train_count:0,val_count:0,message:"Synthetic fixture",classes};
  else if(path.startsWith("/api/dataset/captures/")&&path.endsWith("/labels")){const id=path.split("/")[4];if(init?.method==="PUT"){check(id==="cap_b","Wrong capture label save");const body=JSON.parse(String(init.body));check(Array.isArray(body.labels)&&body.labels.length===0,"Old capture labels leaked");labelSaves++;labelDocs[id]={...labelDocs[id],reviewed:true,labels:body.labels};const cap=captureList.find(x=>x.capture_id===id)!;cap.labeled=true;cap.label_count=body.labels.length;}else if(id==="cap_b"&&labelFailure){await new Promise(r=>setTimeout(r,150));return fixtureError("Fixture labels unavailable");}data=labelDocs[id];}
  else if(path==="/api/models"){if(modelFailure)return new Response(JSON.stringify({ok:false,error:{code:"FIXTURE",message:"Model registry unavailable"}}),{status:503,headers:{"Content-Type":"application/json"}});data={total:1,models:[{...model,is_active:activeModel}],default_model_id:model.model_id,active_model_id:activeModel?model.model_id:null};}
  else if(path==="/api/inference/load"){check(JSON.parse(String(init?.body)).model_id===model.model_id,"Wrong load model");activeModel=true;data={model_loaded:true,backend_available:true,active_model_id:model.model_id};}
  else if(path==="/api/crosswalks"){if(init?.method==="PUT"){savedNetwork=JSON.parse(String(init.body)).config;savedCount++;}else{readCount++;}data=savedNetwork;}
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
function NetworkFixture(){
  const [config,setConfig]=useState(fixture);
  return <CrosswalkNetworkPanel config={config} overview={null} onSaved={setConfig} onRefresh={async()=>{setConfig(await fetchCrosswalks());}} simulationEnabled={false}/>;
}
function CameraFixture(){
  const [status,setStatus]=useState<CameraStatus|null>(null);
  return <CameraSettingsPage status={status} showSimulationTools={false} onSimulationChange={()=>{}} onStatusChange={setStatus} changingMode={false}/>;
}
const waitFor=async (predicate:()=>unknown,reason:string)=>{for(let i=0;i<(page==="review"?100:30);i++){if(predicate())return;await pause();}throw Error(reason+(page==="review"?"; image requests="+captureBImageRequests+"; state="+document.querySelector(".label-empty-state")?.textContent:""));};
const findButton=(label:string)=>[...document.querySelectorAll("button")].find(b=>b.textContent===label);
async function main(){
  const content=page==="cameras"?<CameraFixture/>:page==="diagnostics"?<CameraDiagnosticsPage/>:page==="network"?<NetworkFixture/>:page==="review"?<DatasetReviewPage/>:page==="models"?<ModelRegistryPage runtimeSettings={fallbackRuntimeSettings} onSettingsChange={()=>{}}/>:<DashboardPage health={null} smokeStatus={null} cameraStatus={null} apiState={apiState} onRefresh={()=>{}} refreshing={false} onNavigate={id=>{selected=id;}}/>;
  flushSync(()=>root.render(<AppShell activePage={routes[page]} apiState={apiState} cameraStatus={null} onPageChange={id=>{selected=id;}} showSimulationTools={false} onSimulationToolsToggle={()=>{}}>{content}</AppShell>));
  for(let i=0;i<20;i++){if((page!=="models"||document.body.textContent?.includes("fixture_model"))&&(page!=="cameras"||document.body.textContent?.includes("camera_b")))break;await pause();}
  await pause();
  const mobile=innerWidth<=760;
  check(getComputedStyle(document.querySelector(".workspace-mobile-picker")!).display!=="none"===mobile,"Responsive navigation mismatch");
  check(document.documentElement.scrollWidth<=innerWidth+1,"Page-level horizontal overflow");
  if(page==="dashboard"){check(document.body.textContent?.includes("No verified checks"),"Missing validation must not appear as zero");const b=[...document.querySelectorAll("button")].find(x=>x.textContent==="Open cameras");b?.click();check(selected==="camera_settings","Dashboard action");}
  if(page==="cameras"){
    check(document.querySelectorAll(".camera-status-entry").length===2,"Two saved cameras missing");
    check(findButton("Start Stream")?.disabled,"Disconnected camera start must be disabled");
    check(document.querySelector<HTMLDetailsElement>(".camera-fold")?.open,"Device setup collapsed");
    check(getComputedStyle(document.querySelector(".camera-empty-state strong")!).color==="rgb(255, 255, 255)","Media empty-state text contrast");
    [...document.querySelectorAll<HTMLButtonElement>(".camera-status-entry")].find(b=>b.textContent?.includes("camera_b"))!.click();
    await waitFor(()=>document.querySelector(".camera-status-entry.is-selected")?.textContent?.includes("camera_b")&&Boolean(findButton("Connect")&&!findButton("Connect")!.disabled),"Camera selection failed");
    findButton("Connect")!.click();
    await waitFor(()=>document.body.textContent?.includes("Saved profile retained"),"Failed probe did not retain profile");
    check(findButton("Start Stream")?.disabled,"Failed connection enabled stream");
    failProbe=false;
    await waitFor(()=>Boolean(findButton("Retry connection")&&!findButton("Retry connection")!.disabled),"Retry unavailable");
    findButton("Retry connection")!.click();
    await waitFor(()=>Boolean(findButton("Start Stream")&&!findButton("Start Stream")!.disabled),"Connected camera cannot start");
    findButton("Start Stream")!.click();
    await waitFor(()=>Boolean(findButton("Stop Stream")&&!findButton("Stop Stream")!.disabled),"Start did not enable stop");
    check(!document.querySelector("img.camera-frame"),"Unverified stream shown as fresh");
    findButton("Stop Stream")!.click();
    await waitFor(()=>Boolean(findButton("Start Stream")&&!findButton("Start Stream")!.disabled),"Stop did not restore start");
    check(!profiles[0].connected&&!profiles[0].streaming&&profiles[1].connected&&!profiles[1].streaming,"Other camera state changed");
  }
  if(page==="diagnostics"){const b=[...document.querySelectorAll("button")].find(x=>x.textContent==="Diagnose camera");check(b?.disabled,"No camera must prevent diagnostics");}
  if(page==="network"){const s=document.querySelector<HTMLSelectElement>(".workspace-network-controls select")!;s.value="crossing_1";s.dispatchEvent(new Event("change",{bubbles:true}));await pause();check(document.querySelector(".crossing-network-node.is-selected")?.textContent?.includes("South crossing"),"Crossing selection");const scroll=document.querySelector<HTMLElement>(".crossing-network-scroll")!;if(scroll.scrollWidth>scroll.clientWidth)check(scroll.scrollLeft>0,"Selected crossing not revealed");for(const [id,edge] of [["crossing_0","2"],["crossing_1","4"]]){document.querySelector(`[data-crosswalk-id="${id}"][data-crosswalk-edge="${edge}"]`)!.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",bubbles:true}));await pause();}const save=[...document.querySelectorAll("button")].find(b=>b.textContent==="Save network")!;check(!save.disabled,"Keyboard link did not mark draft dirty");save.click();for(let i=0;i<20&&savedCount===0;i++)await pause();check(savedCount===1&&savedNetwork.network?.links.length===1&&savedNetwork.network.links[0].source_edge==="2"&&savedNetwork.crosswalks.length===2,"Network save contract");await waitFor(()=>document.querySelectorAll(".crossing-network-link-row").length===1&&document.querySelectorAll(".crossing-network-links line").length===1&&save.disabled,"Saved link vanished from parent-rendered UI");const readsBeforeReload=readCount;findButton("Reload")!.click();await waitFor(()=>readCount>readsBeforeReload&&document.querySelectorAll(".crossing-network-link-row").length===1,"Reload did not retain connection");check(savedNetwork.network?.links[0].destination_edge==="4","Destination edge lost");
    const conflict=document.querySelector<HTMLInputElement>(".crossing-movement-conflicts input")!;
    conflict.click();
    await waitFor(()=>!save.disabled,"Conflict edit not dirty");
    const route=document.querySelector<HTMLSelectElement>(".crossing-emergency-route select")!;
    route.value="source_to_destination";route.dispatchEvent(new Event("change",{bubbles:true}));
    await pause();save.click();
    await waitFor(()=>savedCount===2&&save.disabled,"Link edit save failed");
    check(savedNetwork.network?.links[0].movement_conflicts?.includes("vehicle_vehicle"),"Conflict edit lost");
    check(savedNetwork.network?.links[0].emergency_route==="source_to_destination","Route edit lost");
    check(savedNetwork.crosswalks[0].camera_side_a_id==="fixture_a","Saved camera assignment overwritten");
    document.querySelector<HTMLButtonElement>(".crossing-network-link-row button")!.click();
    await waitFor(()=>!save.disabled,"Remove link not dirty");save.click();
    await waitFor(()=>savedCount===3&&save.disabled&&!document.querySelector(".crossing-network-link-row"),"Link removal not retained");
    check(savedNetwork.network?.links.length===0&&savedNetwork.crosswalks.length===2,"Link removal changed crossings");
    for(const [id,edge] of [["crossing_0","2"],["crossing_1","4"]]){document.querySelector(`[data-crosswalk-id="${id}"][data-crosswalk-edge="${edge}"]`)!.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",bubbles:true}));await pause();}
    save.click();await waitFor(()=>savedCount===4&&save.disabled&&document.querySelectorAll(".crossing-network-link-row").length===1,"Recreation after removal failed");
  }
  if(page==="review"){
    await waitFor(()=>document.querySelectorAll(".manual-label-box").length===1,"Initial capture labels missing");
    [...document.querySelectorAll<HTMLButtonElement>(".capture-browser-item")].find(b=>b.textContent?.includes("cap_b"))!.click();
    await waitFor(()=>document.body.textContent?.includes("Fixture labels unavailable"),"Capture failure missing");
    check(!findButton("Save review")&&!document.querySelector(".label-canvas"),"Previous labels editable after capture switch failure");
    check(captureBImageRequests===0,"Image requested before matching labels");
    const retry=async()=>{await waitFor(()=>Boolean(findButton("Refresh list")&&!findButton("Refresh list")!.disabled),"Refresh disabled");findButton("Refresh list")!.click();};
    labelFailure=false;await retry();
    await waitFor(()=>document.body.textContent?.includes("Captured image unavailable."),"Missing image failure state");
    check(findButton("Save review")?.disabled&&!document.querySelector(".label-canvas"),"Unreadable capture can be marked negative");
    imageFailure=false;imageVariant="wrong-size";await retry();
    await waitFor(()=>document.body.textContent?.includes("Captured image dimensions differ from labels."),"Wrong-size image was not rejected");
    check(findButton("Save review")?.disabled&&!document.querySelector(".label-canvas"),"Wrong-size image enabled save");
    imageVariant="invalid";await retry();
    await waitFor(()=>document.body.textContent?.includes("Captured image could not be decoded."),"Invalid PNG was not rejected");
    check(findButton("Save review")?.disabled&&!document.querySelector(".label-canvas"),"Invalid PNG enabled save");
    imageVariant="valid";await retry();
    try { await waitFor(()=>Boolean(findButton("Save review")&&!findButton("Save review")!.disabled),"Image and label retry failed"); }
    catch (reason) { throw Error(String(reason)+"; image requests="+captureBImageRequests+"; "+document.querySelector(".label-empty-state")?.textContent); }
    check(captureBImageRequests===4,"Refresh issued duplicate or missing image requests");
    check(document.querySelectorAll(".manual-label-box").length===0,"Old labels survived retry");
    findButton("Save review")!.click();
    await waitFor(()=>labelSaves===1&&document.body.textContent?.includes("reviewed negative example"),"Negative review save failed");
    await waitFor(()=>document.querySelector(".capture-browser-item.active")?.textContent?.includes("0 boxes · reviewed"),"Saved review list inconsistent");
  }
  if(page==="models"){check(document.body.textContent?.includes("fixture_model"),"Fixture model missing");const search=document.querySelector<HTMLInputElement>("input[type=search]")!;const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value")!.set!;setter.call(search,"not_present");search.dispatchEvent(new Event("input",{bubbles:true}));await pause();check(document.body.textContent?.includes("No matching models."),"Model filtering");setter.call(search,"");search.dispatchEvent(new Event("input",{bubbles:true}));await pause();check(document.body.textContent?.includes("fixture_model"),"Filter restoration");const load=[...document.querySelectorAll("button")].find(b=>b.textContent==="Load model")!;load.click();for(let i=0;i<20&&!load.disabled;i++)await pause();await pause();check(activeModel&&document.querySelector(".model-list-grid")?.textContent?.includes("active"),"Model activation");modelFailure=true;const refresh=[...document.querySelectorAll("button")].find(b=>b.textContent==="Refresh")!;refresh.click();for(let i=0;i<20&&!document.body.textContent?.includes("Model registry unavailable or loading.");i++)await pause();check(document.body.textContent?.includes("Model registry unavailable or loading.")&&!document.body.textContent?.includes("No trained models were found"),"Registry error rendered as empty");modelFailure=false;[...document.querySelectorAll("button")].find(b=>b.textContent==="Refresh")?.click();for(let i=0;i<20&&!document.querySelector(".model-list-grid")?.textContent?.includes("fixture_model");i++)await pause();check(document.querySelector(".model-list-grid")?.textContent?.includes("fixture_model"),"Model recovery");}
  result.textContent="MESH_WORKSPACE_PASS · synthetic API fixture";
}
void main().catch(error=>{result.textContent="MESH_WORKSPACE_FAIL: "+String(error);});
