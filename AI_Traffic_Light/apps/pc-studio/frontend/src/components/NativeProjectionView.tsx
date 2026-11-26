import {useCallback,useEffect,useRef,useState} from "react";
import {fetchNativeProjection,fetchNativeEvaluation,nativeEvaluationCommand,nativeEvaluationCaptureUrl,nativeEvaluationFrameUrl,nativeEvaluationExportUrl,runNativeComparison,type NativeProjectionScene,type NativeProjectionResponse,type NativeEvaluationState} from "../lib/remoteCameraApi";
import {useSerialPolling} from "../lib/useSerialPolling";
import {NativeRoad3D} from "./NativeRoad3D";
import {NativeRegionDraft} from "./NativeRegionDraft";

const SOURCE_TRANSFORM:Record<string,string>={
  simulation_camera:"",
  simulation_camera_b:"translate(0 719) scale(1 -1)",
  simulation_camera_c:"translate(1279 0) scale(-1 1)",
  simulation_camera_d:"translate(1279 719) scale(-1 -1)",
};
function validScene(s:NativeProjectionScene){
  return s.schema_version===1&&s.width===1280&&s.height===720&&Number.isSafeInteger(s.tick)&&s.tick>=0&&
    Number.isFinite(s.time_s)&&s.time_s>=0&&Array.isArray(s.lanes)&&s.lanes.length<=2000&&
    Array.isArray(s.agents)&&s.agents.length<=2000&&new Set(s.agents.map(a=>a.id)).size===s.agents.length&&
    s.agents.every(a=>typeof a.id==="string"&&["vehicle","pedestrian"].includes(a.kind)&&[a.x,a.y,a.speed_m_s].every(Number.isFinite)&&a.x>=0&&a.x<1280&&a.y>=0&&a.y<720&&a.speed_m_s>=0)&&
    s.lanes.every(l=>["road","walk","crossing"].includes(l.kind)&&Number.isFinite(l.width_px)&&l.width_px>0&&Array.isArray(l.points)&&l.points.length>=2&&l.points.length<=1000&&l.points.every(p=>Array.isArray(p)&&p.length===2&&p.every(Number.isFinite)))&&
    (s.pixels_per_m===undefined||Number.isFinite(s.pixels_per_m)&&s.pixels_per_m>0&&s.pixels_per_m<100);
}

function NativeContent({sourceId,standalone,profile}:{sourceId:string;standalone:boolean;profile?:string}){
  const [scene,setScene]=useState<NativeProjectionScene|null>(null);
  const [state,setState]=useState<NativeEvaluationState|null>(null);
  const [status,setStatus]=useState("Loading native preview");
  const [three,setThree]=useState(false);
  const [image,setImage]=useState(false);
  const [playing,setPlaying]=useState(false);
  const play=useRef<{epoch:string;generation:number}|null>(null);
  const [comparisonUrl,setComparisonUrl]=useState<string|null>(null);
  useEffect(()=>()=>{if(comparisonUrl)URL.revokeObjectURL(comparisonUrl);},[comparisonUrl]);
  const stopPlayback=()=>{play.current=null;setPlaying(false);};
  const [top,setTop]=useState(false);
  const [detail,setDetail]=useState(false);
  const [region,setRegion]=useState(false);
  const [seed,setSeed]=useState(42);
  const [duration,setDuration]=useState(500);
  const validSeed=Number.isInteger(seed)&&seed>=0&&seed<=2147483647;
  const [failed,setFailed]=useState(false);
  const [pending,setPending]=useState(false);
  const [density,setDensity]=useState("normal");
  const [geometry,setGeometry]=useState("standard");
  const [mode,setMode]=useState("fixed");
  const latest=useRef({epoch:"",generation:-1,tick:-1});
  const active=useRef<AbortController|null>(null);
  useEffect(()=>()=>{play.current=null;active.current?.abort();},[]);
  const onFailure=useCallback(()=>{setThree(false);setFailed(true);},[]);
  const accept=(response:NativeProjectionResponse)=>{
    if(response.provenance!=="synthetic_sumo_projection"){stopPlayback();setRegion(false);setScene(null);setState(null);setStatus("Invalid native provenance");return;}
    const evaluation=standalone?response as NativeEvaluationState:null;
    const epoch=evaluation?.epoch??"shadow";
    if(epoch!==latest.current.epoch)latest.current={epoch,generation:-1,tick:-1};
    const generation=response.generation;
    if(generation!==undefined&&generation<latest.current.generation)return;
    if(generation!==undefined&&generation>latest.current.generation)latest.current={epoch,generation,tick:-1};
    if(response.status!=="running"||!response.snapshot){
      stopPlayback();setRegion(false);setScene(null);setStatus(response.status==="disabled"?"Native preview disabled on server":"Native preview: "+response.status);
      if(evaluation)setState(evaluation);
      return;
    }
    const next=response.snapshot;
    if(next.provenance!==response.provenance||next.generation!==generation||!Number.isSafeInteger(generation)||!validScene(next)){
      stopPlayback();setRegion(false);setScene(null);setState(null);setStatus("Invalid native scene");return;
    }
    if(next.tick<latest.current.tick)return;
    latest.current={epoch,generation:next.generation,tick:next.tick};
    setScene(next);if(evaluation)setState(evaluation);
    setStatus(standalone?"Native-only evaluation":"Native simulation · read-only");
  };
  const polling=useSerialPolling(async({signal,isCurrent})=>{
    if(active.current)return;
    const intent=play.current;
    const response=standalone?await fetchNativeEvaluation(signal):await fetchNativeProjection(signal);
    if(!isCurrent()||active.current)return;
    if(standalone&&intent&&play.current===intent){
      const current=response as NativeEvaluationState;
      const snap=current.snapshot;
      if(current.epoch!==intent.epoch||current.generation!==intent.generation||current.status!=="running"||
         !snap||snap.paused||snap.tick>=current.max_ticks||!validScene(snap)||snap.provenance!==current.provenance||snap.generation!==current.generation){
        stopPlayback();accept(current);return;
      }
      // The server performs one protected 0.2 s step; never catch up by
      // skipping samples. No automatic resume after reset/connection loss.
      const next=await nativeEvaluationCommand("step",{epoch:intent.epoch,generation:intent.generation,tick:snap.tick,steps:1},signal);
      if(isCurrent()&&!active.current)accept(next);
      return;
    }
    accept(response);
  },playing?200:500,{restartKey:sourceId,onError:()=>{if(!active.current){stopPlayback();setRegion(false);setScene(null);setState(null);setStatus("Native preview unavailable");}}});
  const command=async(action:"start"|"step"|"pause"|"stop",extra:Record<string,unknown>={})=>{
    if(!state||active.current)return;
    stopPlayback();setRegion(false);
    const controller=new AbortController();active.current=controller;setPending(true);
    try{
      await polling.waitForIdle();
      if(controller.signal.aborted)return;
      const response=await nativeEvaluationCommand(action,{epoch:state.epoch,generation:state.generation,...extra},controller.signal);
      if(!controller.signal.aborted)accept(response);
    }catch{if(!controller.signal.aborted)setStatus("Native evaluation command rejected; refreshing");}
    finally{active.current=null;if(!controller.signal.aborted){setPending(false);void polling.runNow();}}
  };
  const compare=async()=>{
    if(!state||scene||active.current)return;
    const controller=new AbortController();active.current=controller;setPending(true);setComparisonUrl(null);
    try{
      await polling.waitForIdle();if(controller.signal.aborted)return;
      const blob=await runNativeComparison(state,density,controller.signal,seed,duration,profile,geometry);
      if(!controller.signal.aborted)setComparisonUrl(URL.createObjectURL(blob));
    }catch{if(!controller.signal.aborted)setStatus("Native comparison failed");}
    finally{active.current=null;if(!controller.signal.aborted)setPending(false);}
  };
  return <div className="native-projection-view" data-native-status={scene?"running":"unavailable"}>
    {scene&&image&&standalone&&state?<img key={`${state.epoch}:${state.generation}:${scene.tick}:${sourceId}`} src={nativeEvaluationFrameUrl(state,sourceId)} alt="Exact synthetic native PNG; original editor coordinates are separate" style={{position:"absolute",inset:0,width:"100%",height:"100%",objectFit:"contain"}}/>:
      scene&&three?<NativeRoad3D key={latest.current.epoch+scene.generation} sourceId={sourceId} scene={scene} top={top} detail={detail} onFailure={onFailure}/>:
      scene&&<svg viewBox="0 0 1280 720" role="img" aria-label="Synthetic native SUMO road and agents"
        data-native-generation={scene.generation} data-native-tick={scene.tick}>
        <rect width="1280" height="720" fill="#1d2125"/>
        <g transform={SOURCE_TRANSFORM[sourceId]??""} key={scene.generation}>
          {(["road","walk","crossing"] as const).flatMap(kind=>scene.lanes.filter(l=>l.kind===kind).map(lane=>
            <polyline key={lane.id} data-native-lane={lane.id} points={lane.points.map(p=>p.join(",")).join(" ")} fill="none"
              stroke={kind==="road"?"#56504b":kind==="walk"?"#8e8982":"#e1e1e1"} strokeWidth={lane.width_px} strokeLinejoin="round" strokeLinecap="round"/>))}
          {scene.agents.map(agent=><circle key={agent.id} data-native-agent={agent.id} cx={agent.x} cy={agent.y}
            r={agent.kind==="vehicle"?4:3} fill={agent.kind==="vehicle"?"#41aaff":"#f5dc41"}/>)}
        </g>
      </svg>}
    {scene&&state&&region&&!three&&!image&&scene.coordinate_space==="native_projection_v1"&&scene.layout_id&&<NativeRegionDraft key={`${state.epoch}:${scene.generation}:${scene.layout_id}:${sourceId}`} sourceId={sourceId} state={state}/>}
    <div style={{position:"absolute",left:8,top:40,right:8,zIndex:5,display:"flex",flexWrap:"wrap",gap:4}}>
      {scene&&<><button type="button" onClick={()=>{setRegion(false);setImage(false);setThree(!three);setFailed(false);}}>{three?"Native 2D":failed?"Retry native 3D":"Native 3D"}</button>
        {three&&<><button type="button" onClick={()=>setTop(!top)}>{top?"Native perspective":"Native top"}</button><button type="button" onClick={()=>setDetail(!detail)}>{detail?"Native overview":"Native detail"}</button></>}
        {standalone&&<button type="button" onClick={()=>{setRegion(false);setThree(false);setImage(!image);}}>{image?"Native scene":"Native PNG"}</button>}</>}
      {standalone&&state&&state.status!=="disabled"&&<>
        <select aria-label="Native geometry" value={geometry} disabled={pending} onChange={e=>setGeometry(e.target.value)}><option value="standard">Standard junction</option><option value="compact">Compact junction</option><option value="elongated">Elongated junction</option></select>
        <select aria-label="Native density" value={density} disabled={pending} onChange={e=>setDensity(e.target.value)}><option>light</option><option>normal</option><option>busy</option></select>
        <select aria-label="Native policy" value={mode} disabled={pending} onChange={e=>setMode(e.target.value)}><option>fixed</option><option>adaptive</option></select>
        <label>Seed <input aria-label="Native seed" type="number" min={0} max={2147483647} value={seed} disabled={pending} onChange={e=>setSeed(Number(e.target.value))} style={{width:90}}/></label>
        <button type="button" disabled={pending||!validSeed} onClick={()=>void command("start",{density,mode,seed,geometry})}>{scene?"Reset native evaluation":"Start native evaluation"}</button>
        {!scene&&<><label>Duration <select value={duration} disabled={pending} onChange={e=>setDuration(Number(e.target.value))}>{[30,60,180,300,500].map(v=><option key={v} value={v}>{v}s</option>)}</select></label><button type="button" disabled={pending||!validSeed} onClick={()=>void compare()}>Compare fixed/adaptive</button>
          {comparisonUrl&&<a href={comparisonUrl} download="mesh-native-comparison.zip">Comparison ZIP</a>}</>}
        {scene&&<>
          <button type="button" disabled={pending||region||scene.paused||scene.tick>=state.max_ticks} onClick={()=>{
            if(play.current){stopPlayback();return;}
            play.current={epoch:state.epoch,generation:state.generation};setPlaying(true);
          }}>{playing?"Stop playback":"Play native"}</button>
          {scene.coordinate_space==="native_projection_v1"&&scene.layout_id&&<button type="button" disabled={pending||playing} onClick={()=>{stopPlayback();setThree(false);setImage(false);setRegion(!region);}}>{region?"Close draft":"Draft region"}</button>}
          <button type="button" disabled={pending||playing||region||scene.paused||scene.tick>=state.max_ticks} onClick={()=>void command("step",{tick:scene.tick,steps:Math.min(25,state.max_ticks-scene.tick)})}>Advance 5 s</button>
          <button type="button" disabled={pending} onClick={()=>void command("pause",{tick:scene.tick,paused:!scene.paused})}>{scene.paused?"Resume native":"Pause native"}</button>
          <button type="button" disabled={pending} onClick={()=>void command("stop")}>Stop native evaluation</button>
          {!pending&&!playing&&<><a href={nativeEvaluationCaptureUrl(state)} aria-label="Download native four-view capture">Capture ZIP</a>
            <a href={nativeEvaluationExportUrl(state)} target="_blank" rel="noreferrer">Export JSON</a></>}
        </>}
      </>}
    </div>
    <span role="status">{status}{scene?` · ${scene.time_s.toFixed(1)} s · ${scene.agents.length} agents${state?.geometry?` · ${state.geometry}`:""}${scene.paused?" · paused":""}`:""}{scene?.signal?` · Requested ${scene.signal.phase.replaceAll("_"," ")} · Applied ${scene.signal.applied_vehicle_go?"vehicle":scene.signal.applied_pedestrian_walk?"pedestrian":"no new entry"}`:""}{failed?" · WebGL unavailable, 2D fallback":""}{standalone&&scene?" · Separate native coordinate plane":""}</span>
  </div>;
}

/** Separate shadow and manually stepped native-only evaluation; neither is a saved camera. */
export function NativeProjectionView({sourceId,standaloneOnly=false,profile}:{sourceId:string;standaloneOnly?:boolean;profile?:string}){
  const [standalone,setStandalone]=useState(standaloneOnly);
  return <div style={{position:"absolute",inset:0}}>
    <NativeContent key={String(standalone)} sourceId={sourceId} standalone={standalone} profile={profile}/>
    {!standaloneOnly&&<button type="button" style={{position:"absolute",right:8,top:8,zIndex:6}} onClick={()=>setStandalone(!standalone)}>
      {standalone?"Shadow preview":"Standalone evaluation"}
    </button>}
  </div>;
}
