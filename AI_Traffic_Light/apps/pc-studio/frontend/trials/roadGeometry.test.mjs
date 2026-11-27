import assert from 'node:assert/strict';
import {ROAD,roadSurfaces,worldPoint,cameraPose} from '../src/components/roadGeometry.ts';
const s=roadSurfaces();
assert.equal(s.filter(x=>x.kind==='stripe').length,9);
assert.deepEqual(s.filter(x=>x.kind==='stop').map(x=>x.x+x.width/2),[495,785]);
assert.equal(s.filter(x=>x.kind==='pavement').length,2);
for(const v of s){assert(v.width>0&&v.height>0&&v.x>=0&&v.y>=0&&v.x+v.width<=ROAD.width&&v.y+v.height<=ROAD.height);if(v.kind==='lane')assert(v.x+v.width<=520||v.x>=760);}
assert.deepEqual(worldPoint(460,190,'simulation_camera'),{x:-180,z:-170});
assert.deepEqual(worldPoint(460,190,'simulation_camera_b'),{x:-180,z:170});
assert.deepEqual(worldPoint(460,190,'simulation_camera_c'),{x:180,z:-170});
assert.deepEqual(worldPoint(460,190,'simulation_camera_d'),{x:180,z:170});
assert.equal(cameraPose(0,0,1).y,1500);
assert(Object.values(cameraPose(NaN,Infinity,0)).every(Number.isFinite));
console.log('[PASS] road bounds, markings, four mirrored cameras and bounded camera pose');
