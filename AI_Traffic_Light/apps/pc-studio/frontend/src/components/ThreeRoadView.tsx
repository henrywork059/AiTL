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
  useLayoutEffect(() => {
    const element = host.current;
    if (!element) return;
    let renderer: RoadRenderer | null = null;
    let observer: ResizeObserver | null = null;
    try {
      renderer = new RoadRenderer(element, sourceId, onFailure);
      instance.current = renderer;
      const current = renderer;
      observer = new ResizeObserver(() => {
        if (instance.current !== current || element.clientWidth === 0 || element.clientHeight === 0) return;
        try { current.render(pose.current.orbit, pose.current.pitch, pose.current.zoom); }
        catch { onFailure(); }
      });
      observer.observe(element);
    } catch {
      observer?.disconnect();
      instance.current = null;
      renderer?.dispose();
      onFailure();
    }
    return () => {
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
    if (!host.current?.clientWidth || !host.current?.clientHeight) return;
    try { instance.current?.render(orbit, pitch, zoom); }
    catch { onFailure(); }
  }, [sourceId, snapshot, orbit, pitch, zoom, onFailure]);

  return <div ref={host} className="sim3d-three-host" aria-hidden="true" style={{ position: "absolute", inset: 0 }} />;
}
