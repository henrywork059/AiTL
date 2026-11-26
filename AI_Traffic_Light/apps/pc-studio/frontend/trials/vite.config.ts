import {defineConfig} from 'vite';
import {resolve} from 'node:path';
export default defineConfig({root:resolve(process.cwd(),'trials'),build:{outDir:resolve(process.cwd(),'renderer-trial-dist'),emptyOutDir:true,rollupOptions:{input:resolve(process.cwd(),'trials/renderer.html')}}});
