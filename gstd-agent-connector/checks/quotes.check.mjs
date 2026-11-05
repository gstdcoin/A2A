import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createPaidConnector} from '../paid-client.mjs';
import {createMcpServer} from '../server.mjs';
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {InMemoryTransport} from '@modelcontextprotocol/sdk/inMemory.js';
const token='gstd_agent_'+'a'.repeat(36)+'.'+'b'.repeat(64),credential={token,max_cost_gstd:'1'};
test('actual MCP validates decimal paid caps and quotes without payment; inference requires its own explicit call',async()=>{
 const calls=[],paid=createPaidConnector({credentialFile:'/fixture',loadCredential:async()=>credential,fetchImpl:async(url,init)=>{
  calls.push({url,body:JSON.parse(init.body)});
  return new Response(JSON.stringify({quote:{id:'a'.repeat(36),model:'fixture-model',nodeId:'fixture-node',price_gstd:'0.5',price_usd:'0.001',expiresAt:Date.now()+60000}}));
 }});
 const server=createMcpServer({policy:{inference_enabled:false},status:async()=>({}),models:async()=>({models:[]})},paid);
 const [a,b]=InMemoryTransport.createLinkedPair(),client=new Client({name:'paid-schema-check',version:'1'});
 try{
  await Promise.all([server.connect(a),client.connect(b)]);
  const r=await client.callTool({name:'gstd_paid_quote',arguments:{prompt:'fixture',model:'fixture-model',max_tokens:32,allow_network:true,max_cost_gstd:'0.5'}});
  assert.equal(r.isError,undefined);assert.equal(r.structuredContent.funds_reserved,false);
  assert.equal(r.structuredContent.within_cost_cap,true);assert.equal(calls.length,1);
  assert.ok(calls[0].url.endsWith('/economics/quotes'));assert.equal(calls[0].body.messages[0].content,'fixture');
  const denied=await client.callTool({name:'gstd_paid_quote',arguments:{prompt:'fixture',model:'fixture-model',allow_network:true,max_cost_gstd:'1e3'}});
  assert.equal(denied.isError,true);assert.equal(calls.length,1);
 }finally{await client.close();await server.close();}
});
