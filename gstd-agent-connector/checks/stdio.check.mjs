import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,copyFile,unlink,rmdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
test('bundled runtime starts outside node_modules and negotiates actual stdio MCP',async()=>{
 const folder=await mkdtemp(join(tmpdir(),'gstd-mcp-check-')),script=join(folder,'server.mjs');
 await copyFile(fileURLToPath(new URL('../dist/server.mjs',import.meta.url)),script);
 const client=new Client({name:'stdio-fixture',version:'1.0.0'});
 const transport=new StdioClientTransport({command:process.execPath,args:[script],env:{GSTD_AGENT_ALLOW_INFERENCE:'0'}});
 try{
  await client.connect(transport);
  assert.deepEqual((await client.listTools()).tools.map(t=>t.name),['gstd_status','gstd_models']);
 }finally{await client.close();await unlink(script);await rmdir(folder);}
});
