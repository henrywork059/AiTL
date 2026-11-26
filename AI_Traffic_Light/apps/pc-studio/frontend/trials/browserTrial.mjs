import {spawn,spawnSync} from 'node:child_process';
import {existsSync,readFileSync} from 'node:fs';
import {resolve} from 'node:path';
const edge=resolve(process.env['ProgramFiles(x86)']||'C:/Program Files (x86)','Microsoft/Edge/Application/msedge.exe');
if(!existsSync(edge))throw new Error('Edge unavailable');
const server=spawn(process.execPath,['node_modules/vite/bin/vite.js','preview','--config','trials/vite.config.ts','--host','127.0.0.1','--port','4179','--strictPort'],{stdio:'inherit'});
const url='http://127.0.0.1:4179/renderer.html';
try {
  let ready=false;
  for(let i=0;i<100;i++){try{if((await fetch(url)).ok){ready=true;break;}}catch{} await new Promise(r=>setTimeout(r,200));}
  if(!ready)throw new Error('Trial server unavailable');
  const args=['--headless=new','--disable-background-networking','--no-first-run','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--window-size=1000,650','--virtual-time-budget=25000'];
  const profile=resolve(process.env.RUNNER_TEMP||'.','mesh-edge-dom');
  if(!process.argv.includes('--native-only')){
  const dom=spawnSync(edge,[...args,'--user-data-dir='+profile,'--dump-dom',url],{encoding:'utf8',timeout:45000,windowsHide:true});
  if(dom.status!==0||!dom.stdout.includes('<div id="result">MESH_RENDERER_PASS</div>'))throw new Error('Browser trial failed: '+dom.stdout.slice(-1500)+' '+dom.stderr.slice(-1000));
  const png=resolve(process.env.RUNNER_TEMP||'.','mesh-renderer.png');
  const shot=spawnSync(edge,[...args,'--user-data-dir='+profile+'-shot','--screenshot='+png,url],{encoding:'utf8',timeout:45000,windowsHide:true});
  if(shot.status!==0||!existsSync(png)||readFileSync(png).length<1000)throw new Error('Screenshot missing');
  console.log('[PASS] actual headless WebGL draw, top view, context loss callback, repeated disposal and screenshot');
  const integration=spawnSync(edge,[...args,'--user-data-dir='+profile+'-integration','--dump-dom','http://127.0.0.1:4179/integration.html'],{encoding:'utf8',timeout:45000,windowsHide:true});
  if(integration.status!==0||!integration.stdout.includes('<div id="result">MESH_INTEGRATION_PASS</div>'))throw new Error('Production integration trial failed: '+integration.stdout.slice(-2000)+' '+integration.stderr.slice(-1500));
  console.log('[PASS] production React renderer opt-in, source change, top view, editor/overlay fallback, loss/retry, rollback and cleanup');
  console.log('[PASS] native SVG identity, older tick/generation rejection, four transforms, volumetric WebGL fallback, standalone mocked command lifecycle and polling retirement');
  }
  const actual=process.argv.includes('--native-only');
  const nativeUrl='http://127.0.0.1:4179/native.html'+(actual?'?actual=1':'');
  const nativeDom=spawnSync(edge,[...args,'--user-data-dir='+profile+'-native','--dump-dom',nativeUrl],{encoding:'utf8',timeout:45000,windowsHide:true});
  if(nativeDom.status!==0||!nativeDom.stdout.includes('<div id="result">MESH_NATIVE_RENDERER_PASS</div>')||
      (actual&&!nativeDom.stdout.includes('Executed SUMO capture')))throw Error('Native renderer trial failed: '+nativeDom.stdout.slice(-1500)+' '+nativeDom.stderr.slice(-1000));
  const nativePng=resolve(process.env.RUNNER_TEMP||'.',actual?'mesh-native-actual.png':'mesh-native-fixture.png');
  const nativeShot=spawnSync(edge,[...args,'--user-data-dir='+profile+'-native-shot','--screenshot='+nativePng,nativeUrl],{encoding:'utf8',timeout:45000,windowsHide:true});
  if(nativeShot.status!==0||!existsSync(nativePng)||readFileSync(nativePng).length<1000)throw Error('Native screenshot missing');
  const detailPng=resolve(process.env.RUNNER_TEMP||'.',actual?'mesh-native-actual-detail.png':'mesh-native-fixture-detail.png');
  const detailShot=spawnSync(edge,[...args,'--user-data-dir='+profile+'-native-detail','--screenshot='+detailPng,nativeUrl+(actual?'&':'?')+'detail=1'],{encoding:'utf8',timeout:45000,windowsHide:true});
  if(detailShot.status!==0||!existsSync(detailPng)||readFileSync(detailPng).length<1000)throw Error('Native detail screenshot missing');
  console.log('[PASS] native WebGL screenshot from '+(actual?'actual SUMO capture':'illustrative scene fixture'));
} finally {server.kill();}
