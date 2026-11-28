import {useEffect,useState} from "react";
import type {CameraStatus, CaptureRecord} from "../src/types";
import {SimulationLabPage} from "../src/pages/SimulationLabPage";
import type {SimulationExperiment, ExperimentModeResult} from "../src/types/experiments";
import {createRoot} from "react-dom/client";
import {flushSync} from "react-dom";
import {AppShell} from "../src/layout/AppShell";
import {DashboardPage} from "../src/pages/DashboardPage";
import {CameraSettingsPage} from "../src/pages/CameraSourcesPage";
import {DEFAULT_REMOTE_CAMERA_SETTINGS} from "../src/lib/remoteCameraApi";
import {CameraDiagnosticsPage} from "../src/pages/CameraDiagnosticsPage";
import {CrosswalkNetworkPanel} from "../src/components/CrosswalkNetworkPanel";
import {DatasetReviewPage} from "../src/pages/DatasetReviewPage";
import {DatasetCapturePage} from "../src/pages/DatasetCapturePage";
import {TrainExportPage} from "../src/pages/TrainExportPage";
import {CrosswalksPage} from "../src/pages/CrosswalksPage";
import {JunctionNetworkPage} from "../src/pages/JunctionNetworkPage";
import {fallbackJunctionNode} from "../src/lib/junctionNetworkView";
import type {JunctionNetworkConfig,JunctionNetworkOverview,JunctionCameraView} from "../src/types/junctionNetwork";
import {ModelRegistryPage} from "../src/pages/ModelRegistryPage";
import {fetchCrosswalks} from "../src/lib/crosswalksApi";
import {fallbackRuntimeSettings} from "../src/api";
import type {AppPageId} from "../src/types/app";
import type {CrosswalkConfig} from "../src/types/crosswalks";
import "../src/styles.css";

const page=new URLSearchParams(location.search).get("page")??"dashboard";
const routes:Record<string,AppPageId>={dashboard:"dashboard",cameras:"camera_settings",diagnostics:"camera_diagnostics",network:"junction_network",junctions:"junction_network",crosswalks:"crosswalks",models:"model_registry",review:"dataset_review",capture:"dataset_capture",training:"train_export",experiments:"simulation_lab"};
const fixture:CrosswalkConfig={schema_version:1,crosswalks:["North crossing","South crossing"].map((label,i)=>({id:"crossing_"+i,label,location:"Synthetic fixture",camera_side_a_id:i===0?"fixture_a":null,camera_side_b_id:null,regions:[]}))};
const model={model_id:"fixture_model",model_path:"outputs/training/fixture_model/weights/best.pt",modified_at_ms:0,size_bytes:1048576,is_active:false,is_default:true,is_latest:true};
const classes=[{id:0,name:"vehicle"}];
const captureList=["cap_a","cap_b"].map(id=>({capture_id:id,session_id:id,quality_tag:"good",origin:"synthetic",width:1280,height:720,labeled:false,label_count:0}));
const labelDocs=Object.fromEntries(captureList.map(c=>[c.capture_id,{capture_id:c.capture_id,session_id:c.session_id,image_path:"fixture",width:c.width,height:c.height,reviewed:false,updated_at_ms:null,labels:c.capture_id==="cap_a"?[{class_id:0,class_name:"vehicle",box_xyxy:[10,10,20,20]}]:[]} ]));
let labelFailure=true, imageFailure=true, labelSaves=0, imageVariant:"valid"|"wrong-size"|"invalid"="valid";
let captureBImageRequests=0, datasetBuilt=false, datasetStale=false, datasetBuilds=0, captureDeletes=0;
let capturePostCount=0, captureSavedCount=0, receiverSource="camera_b", trainingStatusFailure=false, trainingStartCount=0, trainingPollCount=0;
let trainerState="idle";
let captureStatusFailure=false, datasetOnlyFailure=false;
let savedCapture:CaptureRecord|null=null;
if(page==="training"){datasetBuilt=true;datasetStale=true;captureList.forEach(c=>{c.labeled=true;c.label_count=1;});}
const datasetStatus=()=>{const reviewed=captureList.filter(c=>c.labeled);return {ready:datasetBuilt&&!datasetStale,stale:datasetStale,eligible_frame_count:reviewed.length,labeled_frame_count:reviewed.length,label_box_count:reviewed.reduce((sum,c)=>sum+c.label_count,0),train_count:datasetBuilt?1:0,val_count:datasetBuilt?1:0,message:"Synthetic fixture",classes};};
// Encode once synchronously: canvas.toBlob callbacks can be delayed by headless virtual time.
const fixtureImage=(width=1280,height=720)=>{const canvas=document.createElement("canvas");canvas.width=width;canvas.height=height;const ctx=canvas.getContext("2d")!;ctx.fillStyle="#dae4e8";ctx.fillRect(0,0,width,height);ctx.fillStyle="#59636c";ctx.fillRect(0,250,width,220);ctx.fillStyle="#ffffff";ctx.font="32px sans-serif";ctx.fillText("Synthetic empty road fixture",40,100);const bytes=Uint8Array.from(atob(canvas.toDataURL("image/png").split(",")[1]),char=>char.charCodeAt(0));return new Blob([bytes],{type:"image/png"});};
const validFixtureImage=fixtureImage(), wrongSizeFixtureImage=fixtureImage(640,360), invalidFixtureImage=new Blob(["not an image"],{type:"image/png"});
let activeModel=false, modelFailure=false, failModelRefreshAfterLoad=false, savedNetwork=fixture;
let savedCount=0, readCount=0, selectedCamera="camera_a", failProbe=true, failRegionSave=false, failCameraStatus=false;
const profiles=["camera_a","camera_b"].map((source_id,i)=>({source_id,host:"192.168.1."+(80+i),kind:"esp32",selected:i===0,connected:false,streaming:false,device_reachable:false,target_fps:15,settings:DEFAULT_REMOTE_CAMERA_SETTINGS,last_error:null as string|null,stream_connected:false,measured_fps:0,paused_for_simulation:false}));
if(page==="crosswalks")Object.assign(profiles[0],{connected:true,streaming:true,device_reachable:true,stream_connected:true});
let junctionFailure=false, junctionSaves=0;
let junctionConfig:JunctionNetworkConfig={schema_version:1,active_intersection_id:"j_a",intersections:["a","b"].map((id,i)=>({id:"j_"+id,label:"Junction "+id.toUpperCase(),enabled:true,source_ids:["camera_"+id],primary_source_id:"camera_"+id,zone_ids:[],crosswalk_edges:{north:null,east:null,south:null,west:null},signal_profile:"Normal",position:{x:30+40*i,y:45}})),links:[]};
const junctionCameras:JunctionCameraView[]=profiles.map(p=>({source_id:p.source_id,kind:"esp32_cam",saved:true,host:p.host,selected:p.selected,connected:true,device_reachable:true,streaming:true,stream_connected:true,measured_fps:12,last_success_at_ms:Date.now(),last_error:null,state:"streaming"}));
const junctionOverview=():JunctionNetworkOverview=>{const nodes=junctionConfig.intersections.map(c=>{const node=fallbackJunctionNode(c,junctionConfig.active_intersection_id);if(c.id==="j_a"){node.live={...node.live,available:true,pipeline_source_active:true,source_id:"camera_a",source_mapping_matched:true,observation_provenance:"ai_detection",phase:"vehicle_green",vehicle:{total:9,waiting:4,load:"moderate"},pedestrian:{total:2,waiting:2,crossing:0,load:"light"}};}return node;});return {schema_version:1,generated_at_ms:Date.now(),network:junctionConfig,available_cameras:junctionCameras,active_source_id:"camera_a",current_frame_source_id:"camera_a",observation_intersection_id:"j_a",observation_provenance:"ai_detection",source_mapping_matched:true,simulation_enabled:false,junctions:nodes,links:[],warnings:[],summary:{junction_count:2,enabled_junction_count:2,link_count:0,saved_esp_camera_count:2,assigned_esp_camera_count:2,reachable_esp_camera_count:2,streaming_esp_camera_count:2,warning_junction_count:0,event_count:0,heavy_vehicle_junction_count:0,heavy_pedestrian_junction_count:0},multi_camera_assignment:true,simultaneous_multi_junction_inference:false,prototype_only:true,scope_note:"Synthetic fixture; no physical authority."};};
if(page==="junctions")savedNetwork={...fixture,crosswalks:fixture.crosswalks.map((c,i)=>({...c,camera_side_a_id:i===0?"camera_a":null}))};
const remoteState=()=>({cameras:profiles.map(p=>({...p,selected:p.source_id===selectedCamera})),active_source_id:selectedCamera,camera_count:2,max_saved_cameras:12,source_id:selectedCamera,host:profiles.find(p=>p.source_id===selectedCamera)?.host});
const waitMetrics={count:1,average_seconds:4,median_seconds:4,p95_seconds:4,max_seconds:4,total_seconds:4};
const queueMetrics={sample_count:1,average:1,p95:1,max:1,queue_seconds:1,occupied_seconds:1,occupied_share_percent:100};
function experimentMode(mode:"fixed"|"adaptive"):ExperimentModeResult{return {mode,metrics:{
  waiting:{vehicle:waitMetrics,pedestrian:waitMetrics},
  queues:{vehicle:queueMetrics,pedestrian:queueMetrics,simultaneous_queue_seconds:1,simultaneous_queue_share_percent:100},
  throughput:{vehicle_passages:2,pedestrian_crossings:1,vehicle_per_minute:2,pedestrian_per_minute:1,combined_services:3,combined_services_per_minute:3,vehicle_passages_per_green_minute:2},
  signal:{phase_time_seconds:{vehicle_green:60},phase_share_percent:{vehicle_green:100},phase_transitions:0,cycles_completed:0,clearance_time_seconds:0,clearance_share_percent:0,rule_application_count:0,rule_applications:{},extension_seconds:0,reduction_seconds:0},
  diagnostics:{protected_overlap_seconds:0,protected_overlap_detected:false,note:"Synthetic fixture"}},
  final_signal:null,timeline:[]};}
function experimentFixture(id:string,seed:number):SimulationExperiment{return {run_id:id,created_at_ms:123456,label:id,scenario:{density:"normal",duration_seconds:60,seed,sample_interval_seconds:1,profile:"fixture",comparison:["fixed","adaptive"]},
  fixed:experimentMode("fixed"),adaptive:experimentMode("adaptive"),
  comparison:Object.fromEntries(["vehicle_wait_average","pedestrian_wait_average","vehicle_throughput","pedestrian_throughput","combined_throughput","simultaneous_queue_time"].map(key=>[key,{fixed:4,adaptive:4,difference:0,percent_change:0,adaptive_direction:"same",lower_is_better:true}])),
  prototype_only:true,scope_note:"Synthetic browser fixture, not measured results"};}
let demoRequests=0, demoFailure=true;
let storedExperiments=[experimentFixture("run_a",11),experimentFixture("run_b",22)];
let experimentDetailFailure=true,experimentProfileFailure=false,experimentListFailure=false,experimentDeletes=0,experimentCreates=0;
const fixtureError=(message:string)=>new Response(JSON.stringify({ok:false,error:{code:"FIXTURE",message}}),{status:503,headers:{"Content-Type":"application/json"}});
window.fetch=async (input,init)=>{
  const path=new URL(typeof input==="string"?input:input instanceof URL?input.href:input.url,location.href).pathname;
  let data:unknown;
  if(path==="/api/camera/remote/status"){if(failCameraStatus)return fixtureError("Fixture camera status unavailable");data=page==="cameras"||page==="crosswalks"?remoteState(): {cameras:[],active_source_id:null};}
  else if(path==="/api/camera/remote/select"){selectedCamera=JSON.parse(String(init?.body)).source_id;check(profiles.some(p=>p.source_id===selectedCamera),"Wrong camera identity");data=remoteState();}
  else if(path==="/api/camera/remote/cameras"){const body=JSON.parse(String(init?.body));check(body.source_id===selectedCamera&&body.host===profiles.find(p=>p.source_id===selectedCamera)?.host,"Camera profile mismatch");data=remoteState();}
  else if(path==="/api/camera/remote/connect"){const body=JSON.parse(String(init?.body));check(body.source_id===selectedCamera,"Wrong connection target");const p=profiles.find(p=>p.source_id===selectedCamera)!;if(failProbe){p.last_error="Fixture ESP unreachable";return fixtureError(p.last_error);}p.last_error=null;p.connected=true;p.device_reachable=true;data=remoteState();}
  else if(path==="/api/camera/remote/start"||path==="/api/camera/remote/stop"){const p=profiles.find(p=>p.source_id===selectedCamera)!;check(p.connected,"Stream requested without connection");p.streaming=path.endsWith("/start");p.stream_connected=p.streaming;data=remoteState();}
  else if(path==="/api/camera/frame")return new Response(validFixtureImage,{headers:{"Content-Type":"image/png"}});
  else if(path==="/api/camera/status")data={mode:"receiver",simulation_enabled:false,simulation_paused:false,frame_available:false,stale:true,streaming:profiles.find(p=>p.source_id===selectedCamera)?.streaming??false,active_source_id:selectedCamera,resolution:null,age_ms:null,frame_url:null};
  else if(path==="/api/dataset/status"){if(captureStatusFailure)return fixtureError("Dataset storage status unavailable");data={active_dataset_id:"captures",session_count:captureSavedCount>0?1:0,frame_count:captureSavedCount,metadata_count:captureSavedCount,capture_enabled:true,status:"ready",dataset_path:"datasets/captures",last_capture:savedCapture};}
  else if(path==="/api/dataset/captures"&&init?.method==="POST"){capturePostCount++;const body=JSON.parse(String(init.body));check(body.expected_source_id==="camera_a"&&body.expected_origin==="upload"&&body.session_id==="default","Capture identity preflight missing");if(body.expected_source_id!==receiverSource)return fixtureError("Camera source changed before capture");captureSavedCount++;savedCapture={capture_id:"saved_capture_1",session_id:"default",source_id:receiverSource,origin:"upload",image_path:"captures/default/saved_capture_1.png",metadata_path:"captures/default/saved_capture_1.json",content_type:"image/png",width:1280,height:720,source_frame_number:7,source_received_at_ms:123456,captured_at_ms:123457,size_bytes:500,quality_tag:"unreviewed",note:""};data=savedCapture;captureStatusFailure=true;}
  else if(path==="/api/dataset/captures/saved_capture_1"&&init?.method==="DELETE"){check(savedCapture!==null,"Wrong capture deletion target");savedCapture=null;captureSavedCount=0;captureStatusFailure=true;data={capture_id:"saved_capture_1",session_id:"default",deleted:true,cleanup_pending:false,deleted_paths:[],training_dataset:datasetStatus()};}
  else if(path==="/api/dataset/captures")data={captures:captureList,total:captureList.length,classes};
  else if(path.startsWith("/api/dataset/captures/")&&path.endsWith("/image")){const id=path.split("/")[4];if(id==="cap_b"){captureBImageRequests++;if(imageFailure)return fixtureError("Fixture image unavailable");}const blob=id!=="cap_b"||imageVariant==="valid"?validFixtureImage:imageVariant==="wrong-size"?wrongSizeFixtureImage:invalidFixtureImage;return new Response(blob,{headers:{"Content-Type":"image/png"}});}
  else if(path==="/api/dataset/training-dataset/status"){if(trainingStatusFailure||datasetOnlyFailure)return fixtureError("Managed dataset status unavailable");data=datasetStatus();}
  else if(path==="/api/settings/runtime")data=fallbackRuntimeSettings;
  else if(path==="/api/traffic/signal-rules"&&page==="experiments"){if(experimentProfileFailure)return fixtureError("Signal profile unavailable");data={profiles:{fixture:{}},active_profile:"fixture"};}
  else if(path==="/api/traffic/fake-junction-demo"&&page==="experiments"){
    const body=JSON.parse(String(init?.body));demoRequests++;
    if(demoFailure)return fixtureError("Synthetic demonstration unavailable");
    check(body.scenario==="missing_ack"&&body.authorized===true,"Fake demo request lost authorization or scenario");
    const off={connected:false,armed:false,active:false,reason:"disconnected",physical_output_allowed:false};
    const checks=Object.fromEntries(["authorization_matches","activation_matches_scenario","denied_never_active","acknowledgments_match","expected_stop","final_disconnected","physical_and_audio_unavailable"].map(key=>[key,true]));
    data={schema_version:1,scenario:body.scenario,authorization_requested:body.authorized,provenance:"illustrative/synthetic",time_basis:"virtual_ms",lease_ms:1000,prototype_only:true,physical_output_allowed:false,audio_playback:false,
      trace:[{time_ms:0,event:"fault_stop",lighting:off,speaker:off,ack:null},{time_ms:0,event:"final_disconnected",lighting:off,speaker:off,ack:null}],checks};
  }
  else if(path==="/api/traffic/experiments"&&init?.method==="POST"&&page==="experiments"){
    const body=JSON.parse(String(init.body));check(body.profile==="fixture","Wrong experiment profile");experimentCreates++;
    const created=experimentFixture("run_c",body.seed);storedExperiments=[created,...storedExperiments];experimentListFailure=true;data=created;
  }
  else if(path==="/api/traffic/experiments"&&page==="experiments"){
    if(experimentListFailure)return fixtureError("Stored experiment list unavailable");
    data={experiments:storedExperiments.map(run=>({run_id:run.run_id,created_at_ms:run.created_at_ms,label:run.label,scenario:run.scenario,headline:run.comparison})),total:storedExperiments.length,storage_path:"fixture",prototype_only:true};
  }
  else if(path.startsWith("/api/traffic/experiments/")&&page==="experiments"){
    const id=decodeURIComponent(path.split("/").pop()!);
    if(init?.method==="DELETE"){check(id==="run_c"&&storedExperiments.some(run=>run.run_id===id),"Wrong stored experiment deletion");experimentDeletes++;storedExperiments=storedExperiments.filter(run=>run.run_id!==id);data={deleted:true,run_id:id};}
    else {if(id==="run_b"){await new Promise(resolve=>setTimeout(resolve,350));if(experimentDetailFailure)return fixtureError("Stored experiment unavailable");}const found=storedExperiments.find(run=>run.run_id===id);if(!found)return fixtureError("Unknown experiment");data=found;}
  }
  else if(path==="/api/training/status"){trainingPollCount++;if(trainingStatusFailure)return fixtureError("Training status unavailable");data={training_available:true,status:trainerState,progress:trainerState==="running"?2:0,completed_epochs:0,active_run_id:trainerState==="running"?"fixture_run":null,dataset_integrity_sha256:trainerState==="running"?"a".repeat(64):null,message:"Synthetic training fixture",config:null,output_path:null,best_model_path:null,error:null,history:[],early_stopping:null};}
  else if(path==="/api/training/start"){const body=JSON.parse(String(init?.body));check(body.dataset_yaml==="yolo/data.yaml"&&datasetStatus().ready&&!datasetStatus().stale,"Training started with stale managed dataset");trainingStartCount++;trainerState="running";data={training_available:true,status:"running",progress:0,completed_epochs:0,active_run_id:"fixture_run",dataset_integrity_sha256:"a".repeat(64),message:"Synthetic run initiated",config:body,output_path:null,best_model_path:null,error:null,history:[],early_stopping:null};}
  else if(path==="/api/dataset/training-dataset"&&init?.method==="POST"){check(JSON.parse(String(init.body)).validation_fraction===0.2&&datasetStatus().eligible_frame_count>=2,"Invalid dataset build");datasetBuilds++;datasetBuilt=true;datasetStale=false;data=datasetStatus();}
  else if(path.startsWith("/api/dataset/captures/")&&init?.method==="DELETE"){const id=path.split("/")[4];check(id==="cap_b"&&captureList.some(c=>c.capture_id===id),"Wrong delete capture");captureList.splice(captureList.findIndex(c=>c.capture_id===id),1);delete labelDocs[id];captureDeletes++;datasetStale=datasetBuilt;data={capture_id:id,session_id:id,deleted:true,cleanup_pending:false,deleted_paths:[],training_dataset:datasetStatus()};}
  else if(path.startsWith("/api/dataset/captures/")&&path.endsWith("/labels")){const id=path.split("/")[4];if(init?.method==="PUT"){check(id===(labelSaves===0?"cap_b":"cap_a"),"Wrong capture label save");const body=JSON.parse(String(init.body));check(Array.isArray(body.labels),"Invalid labels");if(id==="cap_b")check(body.labels.length===0,"Old capture labels leaked");else{check(body.labels.length===2,"New annotation not saved");const box=body.labels[1].box_xyxy;check([160,200,400,360].every((value,i)=>Math.abs(box[i]-value)<3),"Annotation coordinates mismatch: "+box);}labelSaves++;if(datasetBuilt)datasetStale=true;labelDocs[id]={...labelDocs[id],reviewed:true,labels:body.labels};const cap=captureList.find(x=>x.capture_id===id)!;cap.labeled=true;cap.label_count=body.labels.length;}else if(id==="cap_b"&&labelFailure){await new Promise(r=>setTimeout(r,150));return fixtureError("Fixture labels unavailable");}data=labelDocs[id];}
  else if(path==="/api/models"){if(modelFailure)return new Response(JSON.stringify({ok:false,error:{code:"FIXTURE",message:"Model registry unavailable"}}),{status:503,headers:{"Content-Type":"application/json"}});data={total:1,models:[{...model,is_active:activeModel}],default_model_id:model.model_id,active_model_id:activeModel?model.model_id:null};}
  else if(path==="/api/inference/load"){check(JSON.parse(String(init?.body)).model_id===model.model_id,"Wrong load model");activeModel=true;if(failModelRefreshAfterLoad)modelFailure=true;data={model_loaded:true,backend_available:true,active_model_id:model.model_id};}
  else if(path==="/api/crosswalks"){if(init?.method==="PUT"){const next=JSON.parse(String(init.body)).config;if(page==="crosswalks"&&next.crosswalks[0]?.regions.length){await new Promise(r=>setTimeout(r,350));if(failRegionSave)return fixtureError("Fixture region save rejected");}savedNetwork=next;savedCount++;}else{readCount++;}data=savedNetwork;}
  else if(path==="/api/inference/status")data={model_loaded:activeModel,backend_available:true,active_model_id:activeModel?model.model_id:null};
  else if(path==="/api/traffic/network/overview"){if(junctionFailure)return fixtureError("Fixture junction observation unavailable");data=junctionOverview();}
  else if(path==="/api/traffic/network"&&init?.method==="PUT"){const next:JunctionNetworkConfig=JSON.parse(String(init.body)).config;check(next.intersections[0].source_ids.join(",")==="camera_a,camera_b"&&next.intersections[1].source_ids.length===0&&next.intersections[1].primary_source_id===null,"Camera ownership transfer invalid");junctionConfig=next;junctionSaves++;data=junctionConfig;}
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
const waitFor=async (predicate:()=>unknown,reason:string)=>{for(let i=0;i<(["review","crosswalks","junctions","capture","training","cameras","experiments"].includes(page)?120:30);i++){if(predicate())return;await pause();}throw Error(reason+(page==="review"?"; image requests="+captureBImageRequests+"; state="+document.querySelector(".label-empty-state")?.textContent:""));};
const findButton=(label:string)=>[...document.querySelectorAll("button")].find(b=>b.textContent===label);
let dragSerial=0;
async function dragImagePoint(selector:string,start:[number,number],end:[number,number],done:()=>unknown){const svg=document.querySelector<SVGSVGElement>(selector)!;svg.scrollIntoView({block:"center"});await pause();const matrix=svg.getScreenCTM()!;const toScreen=(point:[number,number])=>{const p=new DOMPoint(...point).matrixTransform(matrix);return [p.x,p.y];};const id=++dragSerial;result.dataset.drag=JSON.stringify({id,from:toScreen(start),to:toScreen(end),target:selector===".crosswalk-region-overlay"?".crosswalk-region-vertex":".label-canvas",svgSelector:selector,logicalFrom:start,logicalTo:end});await waitFor(()=>result.dataset.dragDone===String(id)&&done(),"Real pointer drag not committed: "+selector+"; released="+result.dataset.dragDone+"; vertices="+[...svg.querySelectorAll("circle")].map(c=>c.getAttribute("cx")+","+c.getAttribute("cy")).join(";"));delete result.dataset.drag;}
const vertexNear=(x:number,y:number)=>{const c=document.querySelector(".crosswalk-region-vertex");return Boolean(c&&Math.abs(Number(c.getAttribute("cx"))-x)<=1&&Math.abs(Number(c.getAttribute("cy"))-y)<=1);};
function CaptureFixture(){const [status,setStatus]=useState<CameraStatus>({mode:"receiver",simulation_enabled:false,simulation_paused:false,simulation_density:"normal",frame_available:true,streaming:true,active_source_id:"camera_a",resolution:{width:1280,height:720},content_type:"image/png",received_at_ms:123456,age_ms:50,frame_number:7,size_bytes:500,origin:"upload",stale:false,frame_url:null,upload_endpoint:""});useEffect(()=>{const image=document.querySelector<HTMLImageElement>(".camera-preview-panel img");if(image)image.src=location.origin+"/api/camera/frame";},[status.stale]);return <><button id="fixture-source-stale" type="button" onClick={()=>setStatus(current=>({...current,stale:!current.stale}))}>Toggle fixture stale</button><DatasetCapturePage cameraStatus={status}/></>;}
function CrosswalkFixture(){const [status,setStatus]=useState<CameraStatus>({mode:"receiver",simulation_enabled:false,simulation_paused:false,simulation_density:"normal",frame_available:false,streaming:true,active_source_id:"camera_a",resolution:null,content_type:null,received_at_ms:null,age_ms:null,frame_number:0,size_bytes:0,origin:null,stale:false,frame_url:null,upload_endpoint:""});return <CrosswalksPage cameraStatus={status} showSimulationTools={false} changingMode={false} onSimulationChange={async()=>{}} onCameraStatusChange={setStatus}/>;}
async function main(){
  const content=page==="cameras"?<CameraFixture/>:page==="diagnostics"?<CameraDiagnosticsPage/>:page==="network"?<NetworkFixture/>:page==="junctions"?<JunctionNetworkPage cameraStatus={null} showSimulationTools={false} changingMode={false} onSimulationChange={async()=>{}}/>:page==="crosswalks"?<CrosswalkFixture/>:page==="review"?<DatasetReviewPage/>:page==="capture"?<CaptureFixture/>:page==="training"?<TrainExportPage/>:page==="experiments"?<SimulationLabPage/>:page==="models"?<ModelRegistryPage runtimeSettings={fallbackRuntimeSettings} onSettingsChange={()=>{}}/>:<DashboardPage health={null} smokeStatus={null} cameraStatus={null} apiState={apiState} onRefresh={()=>{}} refreshing={false} onNavigate={id=>{selected=id;}}/>;
  flushSync(()=>root.render(<AppShell activePage={routes[page]} apiState={apiState} cameraStatus={null} onPageChange={id=>{selected=id;}} showSimulationTools={page==="experiments"} onSimulationToolsToggle={()=>{}}>{content}</AppShell>));
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
    check(document.querySelector(".camera-status-entry.is-selected")?.textContent?.includes("Streaming"),"Fixture streaming status missing");
    failCameraStatus=true;
    await waitFor(()=>document.querySelector(".camera-status-strip")?.textContent?.includes("status unavailable"),"Failed camera poll not shown");
    check(document.querySelectorAll(".camera-status-entry").length===2&&!document.querySelector(".camera-status-entry.is-selected")&&[...document.querySelectorAll(".camera-status-entry .status-pill")].every(el=>el.textContent==="Unavailable"),"Cached profiles or stale status after failed poll");
    check(findButton("Stop Stream")?.disabled&&!document.querySelector("img.camera-frame"),"Unverified selected command or frame remained available");
    failCameraStatus=false;
    await waitFor(()=>document.querySelector(".camera-status-entry.is-selected")?.textContent?.includes("camera_b")&&!findButton("Stop Stream")?.disabled,"Camera poll recovery did not restore active state");
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
  if(page==="junctions"){
    await waitFor(()=>document.querySelector<HTMLDetailsElement>(".junction-advanced-config"),"Junction config not loaded");document.querySelector<HTMLDetailsElement>(".junction-advanced-config")!.open=true;
    await waitFor(()=>document.querySelector(".junction-live-grid")?.textContent?.includes("9 total")&&document.querySelectorAll(".junction-camera-row input").length===2,"Live fixture observation missing");
    const other=()=>document.querySelectorAll<HTMLInputElement>(".junction-camera-row input")[1];window.confirm=()=>false;other().click();await pause();check(!other().checked,"Cancelled camera transfer changed draft");
    window.confirm=()=>true;other().click();await waitFor(()=>other().checked&&findButton("Save junction configuration")&&!findButton("Save junction configuration")!.disabled,"Camera transfer draft missing");
    junctionFailure=true;await waitFor(()=>document.body.textContent?.includes("Live junction status unavailable")&&!document.querySelector(".junction-live-grid"),"Old observation remained current after poll failure");
    check(other().checked&&!findButton("Save junction configuration")!.disabled&&document.querySelector(".junction-camera-fps")?.textContent==="Unavailable","Failed poll erased draft or retained live camera status");
    check(document.body.textContent?.includes("Not currently observed"),"Crosswalk retained failed observation");
    junctionFailure=false;await waitFor(()=>document.querySelector(".junction-live-grid")?.textContent?.includes("9 total"),"Junction observation did not recover");
    check(other().checked,"Recovered poll erased draft");findButton("Save junction configuration")!.click();await waitFor(()=>junctionSaves===1&&findButton("Save junction configuration")?.disabled,"Junction assignment save failed");
    junctionFailure=true;await waitFor(()=>document.body.textContent?.includes("Live junction status unavailable")&&!document.querySelector(".junction-live-grid"),"Post-save stale observation remained");
    check(junctionConfig.intersections[0].source_ids.length===2&&junctionConfig.intersections[1].primary_source_id===null,"Saved source ownership lost");
  }
  if(page==="crosswalks"){
    await waitFor(()=>document.querySelectorAll(".crosswalk-camera-select select").length===2&&document.querySelector(".crosswalk-camera-select select option[value=camera_a]"),"Saved camera choices unavailable");
    const choose=(index:number,value:string)=>{const select=document.querySelectorAll<HTMLSelectElement>(".crosswalk-camera-select select")[index];select.value=value;select.dispatchEvent(new Event("change",{bubbles:true}));};
    choose(0,"camera_a");await pause();choose(1,"camera_b");await pause();findButton("Save changes")!.click();
    await waitFor(()=>savedCount===1&&findButton("Save changes")?.disabled,"Camera assignment save failed");
    check(savedNetwork.crosswalks[0].camera_side_a_id==="camera_a"&&savedNetwork.crosswalks[0].camera_side_b_id==="camera_b","Wrong side assignment");
    findButton("Reload saved")!.click();await waitFor(()=>document.body.textContent?.includes("Saved crosswalks reloaded."),"Camera assignment reload failed");
    check([...document.querySelectorAll<HTMLSelectElement>(".crosswalk-camera-select select")].map(s=>s.value).join(",")==="camera_a,camera_b","Camera side assignments lost");
    findButton("Edit regions (0)")!.click();await waitFor(()=>document.querySelector(".crosswalk-region-overlay"),"Region editor missing");
    check(document.body.textContent?.includes("Preview unavailable")&&!document.querySelector("img.crosswalk-region-camera"),"No verified frame shown as live");
    findButton("Add region")!.click();await waitFor(()=>document.querySelectorAll(".crosswalk-region-vertex").length===4,"New region missing");
    await dragImagePoint(".crosswalk-region-overlay",[390,220],[320,180],()=>vertexNear(320,180));
    findButton("Side B")!.click();await waitFor(()=>vertexNear(390,220),"Side A geometry leaked into Side B");
    await waitFor(()=>{
      const svg=document.querySelector<SVGSVGElement>(".crosswalk-region-overlay");
      const circle=[...document.querySelectorAll<SVGCircleElement>(".crosswalk-region-vertex")].find(el=>Number(el.getAttribute("cx"))===390&&Number(el.getAttribute("cy"))===220);
      const matrix=svg?.getScreenCTM();
      if(!circle||!matrix)return false;
      const expected=new DOMPoint(390,220).matrixTransform(matrix);
      const rect=circle.getBoundingClientRect();
      return Math.abs(rect.x+rect.width/2-expected.x)<3&&Math.abs(rect.y+rect.height/2-expected.y)<3;
    },"Side B vertex DOM attributes changed without repainting pointer hit geometry");
    await dragImagePoint(".crosswalk-region-overlay",[390,220],[450,180],()=>vertexNear(450,180));
    failRegionSave=true;findButton("Save regions")!.click();await waitFor(()=>findButton("Saving…")&&findButton("Add region")?.disabled&&findButton("Back to crosswalks")?.disabled,"Region edits not locked during save");
    await waitFor(()=>document.body.textContent?.includes("Fixture region save rejected"),"Editor save error not visible");
    check(savedNetwork.crosswalks[0].regions.length===0&&vertexNear(450,180),"Failed save lost draft or changed saved data");
    failRegionSave=false;findButton("Save regions")!.click();await waitFor(()=>savedCount===2&&findButton("Save regions")?.disabled,"Region save retry failed");
    const saved=savedNetwork.crosswalks[0].regions[0];check(saved.vertices_by_side?.a&&saved.vertices_by_side?.b&&[320,180].every((value,i)=>Math.abs(saved.vertices_by_side!.a![0][i]-value)<=1)&&[450,180].every((value,i)=>Math.abs(saved.vertices_by_side!.b![0][i]-value)<=1),"Independent side geometry not persisted");
    findButton("Back to crosswalks")!.click();await waitFor(()=>findButton("Reload saved")&&!findButton("Reload saved")!.disabled,"Crosswalk page did not return");findButton("Reload saved")!.click();await waitFor(()=>document.body.textContent?.includes("Saved crosswalks reloaded.")&&findButton("Edit regions (1)"),"Region reload failed");
    findButton("Edit regions (1)")!.click();await waitFor(()=>vertexNear(320,180),"Side A reload failed");
    findButton("Side B")!.click();await waitFor(()=>vertexNear(450,180),"Side B reload failed");
  }
  if(page==="review"){
    const activeCapture=()=>document.querySelector(".capture-browser-item.active strong")?.textContent;
    const clickReady=async(label:string,ready:()=>unknown=()=>true)=>waitFor(()=>{const button=findButton(label);if(!button||button.disabled||!ready())return false;button.click();return true;},"Button not ready: "+label);
    const clickCapture=async(id:string)=>waitFor(()=>{const button=[...document.querySelectorAll<HTMLButtonElement>(".capture-browser-item")].find(b=>b.querySelector("strong")?.textContent===id);if(!button||button.disabled)return false;button.click();return true;},"Capture not selectable: "+id);
    const imageFor=(id:string,count:number)=>activeCapture()===id&&Boolean(document.querySelector(".label-canvas"))&&document.querySelectorAll(".manual-label-box:not(.draft)").length===count;
    await waitFor(()=>imageFor("cap_a",1),"Initial capture labels missing");
    await clickCapture("cap_b");
    await waitFor(()=>document.body.textContent?.includes("Fixture labels unavailable"),"Capture failure missing");
    check(!findButton("Save review")&&!document.querySelector(".label-canvas"),"Previous labels editable after capture switch failure");
    check(captureBImageRequests===0,"Image requested before matching labels");
    const retry=()=>clickReady("Refresh list",()=>activeCapture()==="cap_b");
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
    await clickReady("Save review",()=>imageFor("cap_b",0));
    await waitFor(()=>labelSaves===1&&document.body.textContent?.includes("reviewed negative example"),"Negative review save failed");
    await waitFor(()=>document.querySelector(".capture-browser-item.active")?.textContent?.includes("0 boxes · reviewed")&&document.querySelector(".managed-dataset-metrics strong")?.textContent==="1","Saved review list or summary inconsistent");
    await clickCapture("cap_a");await waitFor(()=>imageFor("cap_a",1)&&findButton("Save review")&&!findButton("Save review")!.disabled,"Positive review unavailable");
    await dragImagePoint(".label-canvas",[160,200],[400,360],()=>document.querySelectorAll(".manual-label-box:not(.draft)").length===2);
    check(findButton("Refresh list")?.disabled&&findButton("Build managed dataset")?.disabled,"Unsaved annotations did not block refresh/build");
    await clickReady("Save review",()=>imageFor("cap_a",2));await waitFor(()=>labelSaves===2&&document.querySelector(".capture-browser-item.active")?.textContent?.includes("2 boxes · reviewed")&&document.querySelector(".managed-dataset-metrics strong")?.textContent==="2","Positive review save/summary failed");
    await clickReady("Build managed dataset",()=>activeCapture()==="cap_a");
    await waitFor(()=>datasetBuilds===1&&document.body.textContent?.includes("Managed dataset ready: 1 train / 1 validation frames."),"Managed export build failed");
    await clickCapture("cap_b");
    // Await the new decoded image and matching identity, not the still-mounted previous toolbar.
    window.confirm=()=>false;await clickReady("Delete capture",()=>imageFor("cap_b",0));await pause();check(captureDeletes===0&&captureList.length===2,"Cancelled deletion changed data");
    window.confirm=()=>true;await clickReady("Delete capture",()=>imageFor("cap_b",0));await waitFor(()=>captureDeletes===1&&document.querySelectorAll(".capture-browser-item").length===1&&document.body.textContent?.includes("rebuild required"),"Delete did not invalidate managed dataset");
    await waitFor(()=>imageFor("cap_a",2)&&findButton("Save review")&&!findButton("Save review")!.disabled,"Remaining positive capture did not reload");
    check(findButton("Build managed dataset")?.disabled&&captureList[0].capture_id==="cap_a"&&labelDocs.cap_a.labels.length===2,"Deletion corrupted remaining capture or rebuild gate");
  }

  if(page==="capture"){
    await waitFor(()=>findButton("Capture frame")&&!findButton("Capture frame")!.disabled,"Available selected frame did not unlock capture");
    await waitFor(()=>{const image=document.querySelector<HTMLImageElement>(".camera-preview-panel img");return image?.complete&&image.naturalWidth===1280;},"Synthetic HTTP capture preview was not decoded");
    document.querySelector<HTMLButtonElement>("#fixture-source-stale")!.click();
    await waitFor(()=>findButton("Capture frame")?.disabled,"Stale frame did not prevent capture");
    check(capturePostCount===0,"Stale frame was captured");
    document.querySelector<HTMLButtonElement>("#fixture-source-stale")!.click();
    await waitFor(()=>findButton("Capture frame")&&!findButton("Capture frame")!.disabled,"Fresh frame did not recover");
    findButton("Capture frame")!.click();
    await waitFor(()=>capturePostCount===1&&document.body.textContent?.includes("Camera source changed before capture"),"Cross-source capture was not rejected");
    check(captureSavedCount===0,"Cross-source capture wrote a frame");
    receiverSource="camera_a";
    await waitFor(()=>!findButton("Capture frame")!.disabled,"Capture recovery unavailable");
    findButton("Capture frame")!.click();
    await waitFor(()=>capturePostCount===2&&captureSavedCount===1&&document.body.textContent?.includes("Captured captures/default/saved_capture_1.png")&&document.body.textContent?.includes("Dataset storage status unavailable"),"Capture acknowledgement was lost on refresh failure");
    check(!findButton("Delete last capture"),"Unverified capture status allowed deletion");
    captureStatusFailure=false;
    await waitFor(()=>findButton("Delete last capture")&&!findButton("Delete last capture")!.disabled,"Capture storage did not recover");
    window.confirm=()=>true;
    findButton("Delete last capture")!.click();
    await waitFor(()=>captureSavedCount===0&&document.body.textContent?.includes("Deleted saved_capture_1.")&&document.body.textContent?.includes("Dataset storage status unavailable"),"Confirmed deletion was lost on refresh failure");
    check(!findButton("Delete last capture"),"Deleted capture stayed actionable");
    captureStatusFailure=false;
    await waitFor(()=>findButton("Capture frame")&&!findButton("Capture frame")!.disabled,"Capture status did not recover after deletion");
  }
  if(page==="training"){
    await waitFor(()=>trainingPollCount>0&&findButton("Start training")?.disabled&&document.body.textContent?.includes("rebuild required"),"Stale dataset did not block training");
    check(trainingStartCount===0,"Stale training started");
    datasetStale=false;
    await waitFor(()=>findButton("Start training")&&!findButton("Start training")!.disabled,"Ready dataset did not unblock training");
    trainingStatusFailure=true;
    await waitFor(()=>findButton("Start training")?.disabled&&document.body.textContent?.includes("Training status unavailable"),"Failed training poll retained ready permission");
    check(trainingStartCount===0,"Unavailable status allowed training");
    trainingStatusFailure=false;
    await waitFor(()=>findButton("Start training")&&!findButton("Start training")!.disabled,"Training polling did not recover");
    findButton("Start training")!.click();
    await waitFor(()=>trainingStartCount===1&&document.body.textContent?.includes("Training in progress"),"Training fresh readiness preflight or launch failed");
    check(document.body.textContent?.includes("fixture_run"),"Training run identity not displayed");
    check(document.body.textContent?.includes("aaaaaaaaaaaa")&&document.body.textContent?.includes("Verified dataset"),"Training dataset digest not displayed");
    datasetOnlyFailure=true;
    await waitFor(()=>document.body.textContent?.includes("Managed dataset status unavailable"),"Dataset-only failure not displayed");
    check(document.body.textContent?.includes("fixture_run")&&findButton("Training in progress...")?.disabled,"Dataset-only failure withdrew verified running trainer");
    datasetOnlyFailure=false;
    await waitFor(()=>!document.body.textContent?.includes("Managed dataset status unavailable"),"Dataset status recovery failed");
  }
  if(page==="experiments"){
    const select=()=>document.querySelector<HTMLSelectElement>(".experiment-saved-row select")!;
    const enabled=(label:string)=>Boolean(findButton(label)&&!findButton(label)!.disabled);
    await waitFor(()=>enabled("Export samples CSV")&&select().value==="run_a","Initial stored experiment not verified");
    select().value="run_b";select().dispatchEvent(new Event("change",{bubbles:true}));
    await waitFor(()=>select().value==="run_b"&&findButton("Export samples CSV")?.disabled&&findButton("Export evidence ZIP")?.disabled&&findButton("Delete run")?.disabled,"Stale result remained actionable during selection");
    await waitFor(()=>document.body.textContent?.includes("Stored experiment unavailable")&&enabled("Refresh stored runs"),"Selection failure not displayed");
    check(findButton("Export samples CSV")?.disabled&&findButton("Delete run")?.disabled,"Failed selection restored stale actions");
    experimentDetailFailure=false;experimentProfileFailure=true;findButton("Refresh stored runs")!.click();
    await waitFor(()=>enabled("Export samples CSV")&&select().value==="run_b"&&document.body.textContent?.includes("Signal profile unavailable"),"Stored result recovery blocked by missing profile");
    check(findButton("Run comparison")?.disabled,"Unverified profile allowed a new comparison");
    experimentProfileFailure=false;findButton("Refresh stored runs")!.click();
    await waitFor(()=>enabled("Run comparison"),"Profile recovery unavailable");
    const seedInput=document.querySelector<HTMLInputElement>('input[aria-label="Experiment seed"]')!;
    const seedSetter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value")!.set!;
    seedSetter.call(seedInput,"");seedInput.dispatchEvent(new Event("input",{bubbles:true}));
    await waitFor(()=>findButton("Run comparison")?.disabled,"Blank experiment seed allowed comparison");
    seedSetter.call(seedInput,"25025");seedInput.dispatchEvent(new Event("input",{bubbles:true}));
    await waitFor(()=>enabled("Run comparison"),"Valid seed did not recover");
    findButton("Run comparison")!.click();
    await waitFor(()=>experimentCreates===1&&select().value==="run_c"&&enabled("Export samples CSV")&&document.body.textContent?.includes("Experiment saved; the stored-run list could not be refreshed."),"Acknowledged experiment creation lost after list failure");
    window.confirm=()=>true;findButton("Delete run")!.click();
    await waitFor(()=>experimentDeletes===1&&select().value===""&&document.body.textContent?.includes("Experiment deleted; the stored-run list could not be refreshed."),"Acknowledged experiment deletion lost");
    check(findButton("Delete run")?.disabled&&findButton("Export samples CSV")?.disabled&&findButton("Export evidence ZIP")?.disabled,"Deleted experiment remained actionable");
    experimentListFailure=false;findButton("Refresh stored runs")!.click();
    await waitFor(()=>enabled("Export samples CSV")&&select().value==="run_a","Stored experiment list recovery failed");
    findButton("Simulated demonstration")!.click();
    await waitFor(()=>enabled("Run synthetic demo"),"Demo workspace missing");
    findButton("Run synthetic demo")!.click();
    await waitFor(()=>demoRequests===1&&document.body.textContent?.includes("Synthetic demonstration unavailable"),"Demo failure not surfaced");
    check(!document.querySelector('a[download^="mesh-fake-demo"]'),"Failed demo exposed export");
    const demoSelect=document.querySelector<HTMLSelectElement>('select[aria-label="Demo scenario"]')!;
    demoSelect.value="missing_ack";demoSelect.dispatchEvent(new Event("change",{bubbles:true}));
    document.querySelector<HTMLInputElement>('input[aria-label="Authorize fake leases"]')!.click();
    await pause();
    demoFailure=false;findButton("Run synthetic demo")!.click();
    await waitFor(()=>demoRequests===2&&document.body.textContent?.includes("7/7 synthetic checks passed")&&document.body.textContent?.includes("fault stop"),"Demo result missing");
    const link=document.querySelector<HTMLAnchorElement>('a[download="mesh-fake-demo-missing_ack.json"]');
    check(link?.href.startsWith("blob:"),"Demo JSON export missing");
    check(!document.querySelector<HTMLInputElement>('input[aria-label="Authorize fake leases"]')!.checked,"Fake authorization was retained after the request");
    findButton("Back to legacy experiments")!.click();
    await waitFor(()=>enabled("Export samples CSV")&&select().value==="run_a","Demo changed stored experiment state");
  }
  if(page==="models"){check(document.body.textContent?.includes("fixture_model"),"Fixture model missing");const search=document.querySelector<HTMLInputElement>("input[type=search]")!;const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value")!.set!;setter.call(search,"not_present");search.dispatchEvent(new Event("input",{bubbles:true}));await pause();check(document.body.textContent?.includes("No matching models."),"Model filtering");setter.call(search,"");search.dispatchEvent(new Event("input",{bubbles:true}));await pause();check(document.body.textContent?.includes("fixture_model"),"Filter restoration");const load=[...document.querySelectorAll("button")].find(b=>b.textContent==="Load model")!;failModelRefreshAfterLoad=true;load.click();await waitFor(()=>activeModel&&document.body.textContent?.includes("Loaded model fixture_model.")&&document.body.textContent?.includes("Model registry unavailable or loading."),"Model activation acknowledgment lost during registry failure");check(document.querySelector(".inference-status-list")?.textContent?.includes("fixture_model"),"Independent active inference status withdrawn");modelFailure=true;await waitFor(()=>findButton("Refresh")&&!findButton("Refresh")!.disabled,"Model activation refresh did not finish");findButton("Refresh")!.click();await waitFor(()=>findButton("Refresh")&&!findButton("Refresh")!.disabled&&document.body.textContent?.includes("Model registry unavailable"),"Failed registry refresh did not finish");check(document.body.textContent?.includes("Model registry unavailable or loading.")&&!document.body.textContent?.includes("No trained models were found"),"Registry error rendered as empty");modelFailure=false;findButton("Refresh")!.click();await waitFor(()=>findButton("Refresh")&&!findButton("Refresh")!.disabled&&document.querySelector(".model-list-grid")?.textContent?.includes("fixture_model")&&document.querySelector(".model-list-grid")?.textContent?.includes("active"),"Model recovery");}
  result.textContent="MESH_WORKSPACE_PASS · synthetic API fixture";
}
void main().catch(error=>{result.textContent="MESH_WORKSPACE_FAIL: "+String(error);});
