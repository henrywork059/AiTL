import {defineConfig} from 'vite';
import {resolve} from 'node:path';
export default defineConfig({root:resolve(process.cwd(),'trials'),build:{outDir:resolve(process.cwd(),'renderer-trial-dist'),emptyOutDir:true,rollupOptions:{input:{renderer:resolve(process.cwd(),'trials/renderer.html'),integration:resolve(process.cwd(),'trials/integration.html'),native:resolve(process.cwd(),'trials/native.html')}}}});
