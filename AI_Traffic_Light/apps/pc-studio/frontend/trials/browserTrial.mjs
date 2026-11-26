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
  const args=['--headless=new','--disable-background-networking','--no-first-run','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--window-size=1000,650','--virtual-time-budget=8000'];
  const profile=resolve(process.env.RUNNER_TEMP||'.','mesh-edge-dom');
  const dom=spawnSync(edge,[...args,'--user-data-dir='+profile,'--dump-dom',url],{encoding:'utf8',timeout:45000,windowsHide:true});
  if(dom.status!==0||!dom.stdout.includes('<div id="result">MESH_RENDERER_PASS</div>'))throw new Error('Browser trial failed: '+dom.stdout.slice(-1500)+' '+dom.stderr.slice(-1000));
  const png=resolve(process.env.RUNNER_TEMP||'.','mesh-renderer.png');
  const shot=spawnSync(edge,[...args,'--user-data-dir='+profile+'-shot','--screenshot='+png,url],{encoding:'utf8',timeout:45000,windowsHide:true});
  if(shot.status!==0||!existsSync(png)||readFileSync(png).length<1000)throw new Error('Screenshot missing');
  console.log('[PASS] actual headless WebGL draw, top view, context loss callback, repeated disposal and screenshot');
  const integration=spawnSync(edge,[...args,'--user-data-dir='+profile+'-integration','--dump-dom','http://127.0.0.1:4179/integration.html'],{encoding:'utf8',timeout:45000,windowsHide:true});
  if(integration.status!==0||!integration.stdout.includes('<div id="result">MESH_INTEGRATION_PASS</div>'))throw new Error('Production integration trial failed: '+integration.stdout.slice(-2000)+' '+integration.stderr.slice(-1500));
  console.log('[PASS] production React renderer opt-in, source change, top view, editor/overlay fallback, loss/retry, rollback and cleanup');
} finally {server.kill();}
