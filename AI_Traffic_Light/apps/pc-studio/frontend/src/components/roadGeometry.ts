/** Canonical legacy synthetic camera geometry, in reference pixels (not metres). */
export const ROAD = Object.freeze({ width: 1280, height: 720, top: 179, bottom: 625, crossingLeft: 520, crossingRight: 760, stopEast: 495, stopWest: 785 });
export type Surface = Readonly<{ kind: string; x: number; y: number; width: number; height: number; elevation: number; color: number }>;
export function roadSurfaces(): Surface[] {
  const r = ROAD;
  const result: Surface[] = [];
  const add = (kind: string, x: number, y: number, width: number, height: number, elevation: number, color: number) => {
    result.push({ kind, x, y, width, height, elevation, color });
  };
  add('road', 0, r.top, r.width, r.bottom-r.top, 0, 0x393f46);
  add('pavement', 0, 0, r.width, r.top, 6, 0x9a9e99);
  add('pavement', 0, r.bottom, r.width, r.height-r.bottom, 6, 0x9a9e99);
  for (const y of [r.top, r.bottom]) add('kerb', 0, y-2, r.width, 4, 7, 0xc2c6be);
  for (const y of [310, 500]) for (let x=0; x<r.width; x+=86) {
    const end=Math.min(x+50,r.width);
    if (x<r.crossingLeft) add('lane',x,y-2,Math.min(end,r.crossingLeft)-x,4,1,0xe0b06b);
    if (end>r.crossingRight) add('lane',Math.max(x,r.crossingRight),y-2,end-Math.max(x,r.crossingRight),4,1,0xe0b06b);
  }
  add('crossing',r.crossingLeft,r.top,r.crossingRight-r.crossingLeft,r.bottom-r.top,1,0x43494f);
  for(let y=205;y<610;y+=46) add('stripe',r.crossingLeft+18,y,r.crossingRight-r.crossingLeft-36,22,2,0xe6e8e1);
  for(const x of [r.stopEast,r.stopWest]) add('stop',x-3,r.top,6,r.bottom-r.top,2,0xf0f0eb);
  return result;
}
export function worldPoint(x:number,y:number,sourceId:string) {
  const flipX=sourceId==='simulation_camera_c'||sourceId==='simulation_camera_d';
  const flipY=sourceId==='simulation_camera_b'||sourceId==='simulation_camera_d';
  return { x:(flipX?ROAD.width-x:x)-ROAD.width/2, z:(flipY?ROAD.height-y:y)-ROAD.height/2 };
}
export function cameraPose(orbit:number,pitch:number,zoom:number) {
  const safe=(v:number,fallback:number)=>Number.isFinite(v)?v:fallback;
  const az=safe(orbit,0)*Math.PI/180;
  const tilt=Math.max(0,Math.min(75,safe(pitch,48)))*Math.PI/180;
  const d=1500/Math.max(.5,Math.min(1.35,safe(zoom,.85)));
  return {x:d*Math.sin(tilt)*Math.sin(az),y:d*Math.cos(tilt),z:d*Math.sin(tilt)*Math.cos(az),upX:-Math.sin(az),upZ:-Math.cos(az)};
}
