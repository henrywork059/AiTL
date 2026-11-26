import {useEffect,useRef,useState,type PointerEvent} from "react";
import {evaluateNativeRegion,type NativeEvaluationState,type NativeRegionResult} from "../lib/remoteCameraApi";

type Point=[number,number];
/** Draft-only native pixel geometry. Never writes the production zone registry. */
export function NativeRegionDraft({sourceId,state}:{sourceId:string;state:NativeEvaluationState}){
  const [points,setPoints]=useState<Point[]>([]);
  const [result,setResult]=useState<NativeRegionResult|null>(null);
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);
  const svg=useRef<SVGSVGElement>(null),drag=useRef<number|null>(null),request=useRef<AbortController|null>(null);
  useEffect(()=>()=>request.current?.abort(),[]);
  useEffect(()=>{request.current?.abort();request.current=null;setBusy(false);setResult(null);setError("");},[state.snapshot?.tick]);
  const coordinate=(event:PointerEvent<SVGSVGElement>):Point|null=>{
    const matrix=svg.current?.getScreenCTM();if(!matrix)return null;
    const p=new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix.inverse());
    if(!Number.isFinite(p.x)||!Number.isFinite(p.y))return null;
    return [Math.round(Math.max(0,Math.min(1279,p.x))*100)/100,Math.round(Math.max(0,Math.min(719,p.y))*100)/100];
  };
  const changed=(next:Point[])=>{request.current?.abort();request.current=null;setBusy(false);setPoints(next);setResult(null);setError("");};
  const evaluate=async()=>{
    if(points.length!==4||busy||!state.snapshot)return;
    const controller=new AbortController();request.current=controller;setBusy(true);setError("");
    try{
      const value=await evaluateNativeRegion(state,sourceId,points,controller.signal);
      if(!controller.signal.aborted&&value.tick===state.snapshot.tick&&value.generation===state.generation&&value.epoch===state.epoch&&value.layout_id===state.snapshot.layout_id&&value.persisted===false&&value.source_id===sourceId)setResult(value);
    }catch(e){if(!controller.signal.aborted)setError(e instanceof Error?e.message:"Region evaluation failed");}
    finally{if(!controller.signal.aborted){setBusy(false);request.current=null;}}
  };
  return <>
    <svg ref={svg} viewBox="0 0 1280 720" aria-label="Native draft region editor" data-native-region-editor="true"
      style={{position:"absolute",inset:0,width:"100%",height:"100%",zIndex:3,touchAction:"none",cursor:"crosshair"}}
      onPointerDown={event=>{const p=coordinate(event);if(!p)return;
        const index=points.findIndex(([x,y])=>Math.hypot(x-p[0],y-p[1])<18);
        if(index>=0){drag.current=index;event.currentTarget.setPointerCapture(event.pointerId);}
        else if(points.length<4)changed([...points,p]);
      }}
      onPointerMove={event=>{if(drag.current===null)return;const p=coordinate(event);if(p){const i=drag.current;changed(points.map((v,j)=>i===j?p:v));}}}
      onPointerUp={()=>{drag.current=null;}} onPointerCancel={()=>{drag.current=null;}} onLostPointerCapture={()=>{drag.current=null;}}>
      {points.length>=2&&<polygon points={points.map(p=>p.join(",")).join(" ")} fill="rgba(87,255,237,.12)" stroke="#57ffed" strokeWidth="3" strokeDasharray="8 4"/>}
      {points.map(([x,y],i)=><circle key={i} cx={x} cy={y} r="10" fill="#f0ece2" stroke="#57ffed" strokeWidth="3"/>)}
    </svg>
    <div style={{position:"absolute",bottom:36,left:8,zIndex:5,background:"rgba(28,29,32,.9)",padding:8,borderRadius:4,display:"flex",gap:6,alignItems:"center",flexWrap:"wrap"}}>
      <span>{points.length}/4 vertices · native draft only</span>
      <button type="button" onClick={()=>changed([])}>Clear draft</button>
      <button type="button" disabled={points.length!==4||busy} onClick={()=>void evaluate()}>Evaluate draft</button>
      {result&&<span role="status">Vehicles {result.counts.vehicle} · Pedestrians {result.counts.pedestrian} · tick {result.tick}</span>}
      {error&&<span role="alert">{error}</span>}
    </div>
  </>;
}
