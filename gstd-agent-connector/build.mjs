import {build} from 'esbuild';
import {readFile,readdir,writeFile,copyFile,mkdir} from 'node:fs/promises';
import {join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=dirname(fileURLToPath(import.meta.url));
await mkdir(join(root,'dist'),{recursive:true});
await build({entryPoints:[join(root,'server.mjs')],outfile:join(root,'dist/server.mjs'),bundle:true,platform:'node',format:'esm',target:'node18',legalComments:'linked',banner:{js:"import {createRequire as __gstdCreateRequire} from 'node:module'; const require=__gstdCreateRequire(import.meta.url);"}});
let notices='Third-party packages used by the bundled GSTD connector. Original rights apply.\n';
async function collect(folder){
 for(const entry of await readdir(folder,{withFileTypes:true})){
  if(!entry.isDirectory()||entry.name.startsWith('.'))continue;
  const path=join(folder,entry.name);
  if(entry.name.startsWith('@')){await collect(path);continue;}
  try{
   const info=JSON.parse(await readFile(join(path,'package.json'),'utf8'));
   notices+='\n===== '+info.name+' '+info.version+' ('+(typeof info.license==='string'?info.license:'see original package')+') =====\n';
   for(const name of await readdir(path))if(/^(license|licence|copying|notice)([.-]|$)/i.test(name)){
    try{const text=await readFile(join(path,name),'utf8');if(text.length<=262144)notices+='\n'+name+'\n'+text+'\n';}catch{}
   }
   try{await collect(join(path,'node_modules'));}catch{}
  }catch{}
 }
}
await collect(join(root,'node_modules'));
await writeFile(join(root,'dist/THIRD_PARTY_NOTICES.txt'),notices);
await copyFile(join(root,'../LICENSE'),join(root,'LICENSE'));
await copyFile(join(root,'../NOTICE'),join(root,'NOTICE'));
console.error('Built self-contained Node.js MCP runtime; no wallet or credentials included.');
