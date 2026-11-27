import {useLayoutEffect,useRef} from "react";
import type {NativeProjectionScene} from "../lib/remoteCameraApi";
import {NativeRoadRenderer} from "./NativeRoadRenderer";

export function NativeRoad3D({sourceId,scene,top,detail=false,onFailure}:{sourceId:string;scene:NativeProjectionScene;top:boolean;detail?:boolean;onFailure:()=>void}){
  const host=useRef<HTMLDivElement>(null);
  const renderer=useRef<NativeRoadRenderer|null>(null);
  const draw=useRef<(()=>void)|null>(null);
  const topRef=useRef(top);topRef.current=top;
  const detailRef=useRef(detail);detailRef.current=detail;
  useLayoutEffect(()=>{
    const element=host.current;if(!element)return;
    let instance:NativeRoadRenderer|null=null,observer:ResizeObserver|null=null,frame:number|null=null;
    let disposed=false;
    const stop=()=>{disposed=true;if(frame!==null)cancelAnimationFrame(frame);frame=null;};
    const render=(now=performance.now())=>{
      if(disposed||!instance)return;
      try{instance.render(topRef.current,now,detailRef.current);if(instance.isAnimating(now)&&frame===null)frame=requestAnimationFrame(t=>{frame=null;render(t);});}
      catch{stop();onFailure();}
    };
    try{instance=new NativeRoadRenderer(element,sourceId,onFailure);renderer.current=instance;draw.current=()=>render();observer=new ResizeObserver(()=>render());observer.observe(element);}
    catch{stop();onFailure();}
    return()=>{stop();observer?.disconnect();renderer.current=null;draw.current=null;instance?.dispose();};
  },[sourceId,onFailure]);
  useLayoutEffect(()=>{try{renderer.current?.update(scene);draw.current?.();}catch{onFailure();}},[scene,sourceId,top,detail,onFailure]);
  return <div ref={host} className="sim3d-three-host" style={{position:"absolute",inset:0}} aria-label="Native synthetic volumetric preview"/>;
}
