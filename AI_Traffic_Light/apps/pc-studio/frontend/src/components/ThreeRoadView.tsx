import { useLayoutEffect, useRef } from "react";
import type { SimulationScene } from "../lib/remoteCameraApi";
import { RoadRenderer } from "./RoadRenderer";

type Props = {
  sourceId: string;
  snapshot: SimulationScene | null;
  orbit: number;
  pitch: number;
  zoom: number;
  onFailure: () => void;
};

/** Lifecycle adapter. The parent owns all data fetching and camera controls. */
export function ThreeRoadView({ sourceId, snapshot, orbit, pitch, zoom, onFailure }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const instance = useRef<RoadRenderer | null>(null);
  const pose = useRef({ orbit, pitch, zoom });
  const draw = useRef<(() => void) | null>(null);
  useLayoutEffect(() => {
    const element = host.current;
    if (!element) return;
    let renderer: RoadRenderer | null = null;
    let observer: ResizeObserver | null = null;
    let frame: number | null = null;
    let stopped = false;
    const stop = () => {stopped=true;if(frame!==null)cancelAnimationFrame(frame);frame=null;};
    try {
      renderer = new RoadRenderer(element, sourceId, onFailure);
      instance.current = renderer;
      const current = renderer;
      const render = (now=performance.now()) => {
        if (stopped || instance.current !== current || !element.clientWidth || !element.clientHeight) return;
        try {
          current.render(pose.current.orbit,pose.current.pitch,pose.current.zoom,now);
          if(current.isAnimating(now)&&frame===null)frame=requestAnimationFrame(t=>{frame=null;render(t);});
        } catch { stop();onFailure(); }
      };
      draw.current=()=>render();
      observer = new ResizeObserver(()=>render());
      observer.observe(element);
    } catch {
      stop();
      draw.current=null;
      observer?.disconnect();
      instance.current = null;
      renderer?.dispose();
      onFailure();
    }
    return () => {
      stop();
      draw.current=null;
      observer?.disconnect();
      instance.current = null;
      renderer?.dispose();
    };
  }, [sourceId, onFailure]);

  useLayoutEffect(() => {
    try { instance.current?.update(snapshot); }
    catch { onFailure(); }
  }, [sourceId, snapshot, onFailure]);

  useLayoutEffect(() => {
    pose.current = { orbit, pitch, zoom };
    draw.current?.();
  }, [sourceId, snapshot, orbit, pitch, zoom, onFailure]);

  return <div ref={host} className="sim3d-three-host" aria-hidden="true" style={{ position: "absolute", inset: 0 }} />;
}
