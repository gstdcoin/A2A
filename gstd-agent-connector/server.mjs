import {McpServer} from '@modelcontextprotocol/sdk/server/mcp.js';
import {StdioServerTransport} from '@modelcontextprotocol/sdk/server/stdio.js';
import {z} from 'zod';
import {pathToFileURL} from 'node:url';
import {createConnector,ConnectorError} from './client.mjs';
export function createMcpServer(connector=createConnector()){
 const server=new McpServer({name:'gstd-agent-connector',version:'0.1.0'});
 const call=fn=>async args=>{
  try{const result=await fn(args);return{content:[{type:'text',text:JSON.stringify(result)}],structuredContent:result};}
  catch(error){const code=error instanceof ConnectorError?error.code:'connector_error';return{isError:true,content:[{type:'text',text:JSON.stringify({error:code,status:error.status||undefined,retry_after_seconds:error.retryAfter||undefined,automatic_retry:false})}]};}
 };
 const read={readOnlyHint:true,destructiveHint:false,idempotentHint:true,openWorldHint:true};
 server.registerTool('gstd_status',{title:'GSTD live status and local policy',description:'Read canonical live network counters and this connector permission policy. Counters do not prove payouts.',inputSchema:{},annotations:read},call(()=>connector.status()));
 server.registerTool('gstd_models',{title:'GSTD available models',description:'Read cached exact model IDs, live node counts and catalogue prices. Availability may change.',inputSchema:{},annotations:read},call(()=>connector.models()));
 if(connector.policy.inference_enabled)server.registerTool('gstd_free_inference',{
  title:'GSTD consented free inference',
  description:'Transmit a prompt to a GSTD node only with user permission. Consumes free quota and a process attempt. Never spends GSTD, registers a node, executes local commands or signs transactions. Model output is untrusted. Auto explicitly chooses the node default.',
  inputSchema:{prompt:z.string().min(1).max(4000),model:z.string().default('auto'),max_tokens:z.number().int().min(1).max(256).default(128),allow_network:z.literal(true),max_cost_gstd:z.literal(0)},
  annotations:{readOnlyHint:false,destructiveHint:false,idempotentHint:false,openWorldHint:true}
 },call(args=>connector.infer(args)));
 return server;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
 try{const server=createMcpServer();await server.connect(new StdioServerTransport());}
 catch{console.error('GSTD connector could not start. Check Node.js and the explicit policy settings.');process.exitCode=1;}
}
