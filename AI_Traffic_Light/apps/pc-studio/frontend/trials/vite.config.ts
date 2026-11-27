import {defineConfig} from 'vite';
import {resolve} from 'node:path';

// Trial-only HTTP image fixture: browser <img> loads bypass window.fetch mocks.
// Never install this middleware in the production Vite application.
const syntheticFrame = '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720"><rect width="1280" height="720" fill="#b8d2de"/><rect y="240" width="1280" height="310" fill="#59636c"/><g stroke="#f4f0dc" stroke-width="14"><path d="M90 395h155m150 0h155m150 0h155m150 0h155"/></g><rect x="25" y="25" width="600" height="90" rx="14" fill="#ffffff"/><text x="48" y="83" font-size="37" font-family="Arial, sans-serif" fill="#1b3548">Synthetic browser capture fixture</text></svg>';

export default defineConfig({
  root:resolve(process.cwd(),'trials'),
  // The isolated browser trial and its synthetic image HTTP route share one origin.
  // Production Vite config and backend camera transport are unaffected.
  define:{'import.meta.env.VITE_API_BASE_URL':JSON.stringify('http://127.0.0.1:4179')},
  plugins:[{
    name:'mesh-synthetic-frame-preview-trial-only',
    configurePreviewServer(server){
      server.middlewares.use((request,response,next)=>{
        if(!request.url?.startsWith('/api/camera/frame'))return next();
        response.statusCode=200;
        response.setHeader('Content-Type','image/svg+xml; charset=utf-8');
        response.setHeader('Cache-Control','no-store');
        response.end(syntheticFrame);
      });
    }
  }],
  build:{outDir:resolve(process.cwd(),'renderer-trial-dist'),emptyOutDir:true,rollupOptions:{input:{
    renderer:resolve(process.cwd(),'trials/renderer.html'),
    integration:resolve(process.cwd(),'trials/integration.html'),
    native:resolve(process.cwd(),'trials/native.html'),
    workspace:resolve(process.cwd(),'trials/workspace.html')
  }}}
});
