import {test} from 'node:test';
import assert from 'node:assert/strict';
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {InMemoryTransport} from '@modelcontextprotocol/sdk/inMemory.js';
import {createConnector,policyFromEnv} from '../client.mjs';
import {createMcpServer} from '../server.mjs';
const policy=extra=>policyFromEnv({GSTD_AGENT_ALLOW_INFERENCE:'1',...extra});
const args=extra=>({prompt:'fixture',allow_network:true,max_cost_gstd:0,...extra});
const reply=(model='local:small',text='fixture')=>({model,choices:[{message:{content:text}}],_gstd:{billing:{free:true}}});
test('default policy performs no inference and never reads a wallet secret',async()=>{
 const c=createConnector({policy:policyFromEnv({AGENT_PRIVATE_MNEMONIC:'do-not-use'}),fetchImpl:()=>{throw Error('no network');}});
 assert.equal(c.policy.inference_enabled,false);await assert.rejects(c.infer(args()),/inference_disabled/);
 assert.throws(()=>policyFromEnv({GSTD_AGENT_MAX_REQUESTS:'NaN'}),/invalid_request_limit/);
});
test('requires explicit consent, free ceiling, model policy and bounded attempts; sends no credentials',async()=>{
 const calls=[];const c=createConnector({policy:policy({GSTD_AGENT_MAX_REQUESTS:'1'}),fetchImpl:async(url,init)=>{calls.push({url,init});return Response.json(reply());}});
 for(const [patch,code] of [[{allow_network:false},'network_consent_required'],[{max_cost_gstd:1},'zero_cost_limit_required'],[{model:'qwen2.5:7b'},'model_not_allowed']])await assert.rejects(c.infer(args(patch)),new RegExp(code));
 assert.equal(calls.length,0);
 const r=await c.infer(args());assert.equal(r.result,'fixture');assert.equal(r.cost_gstd,0);
 assert.equal(calls[0].url,'https://app.gstdtoken.xyz/api/v1/agents/infer');
 assert.deepEqual(Object.keys(calls[0].init.headers).sort(),['Accept','Content-Type']);
 assert.equal(JSON.parse(calls[0].init.body).max_cost_gstd,0);
 await assert.rejects(c.infer(args()),/process_budget_exhausted/);assert.equal(calls.length,1);
});
test('refuses paid or mismatched named models without substituting auto',async()=>{
 let sends=0;const c=createConnector({policy:policy({GSTD_AGENT_ALLOWED_MODELS:'free:small,paid:large'}),fetchImpl:async(url)=>{
  if(url.endsWith('/available'))return Response.json({models:[{model_id:'free:small',nodes_count:1,is_free:true,price_gstd:0},{model_id:'paid:large',nodes_count:1,is_free:false,price_gstd:1}]});
  sends++;return Response.json(reply('other:model'));
 }});
 await assert.rejects(c.infer(args({model:'paid:large'})),/paid_model_requires_wallet/);assert.equal(sends,0);
 await assert.rejects(c.infer(args({model:'free:small'})),/model_mismatch/);assert.equal(sends,1);
});
test('coalesces discovery, respects 429 backoff and never automatically retries inference',async()=>{
 let calls=0,time=1000;const c=createConnector({policy:policy(),now:()=>time,fetchImpl:async(url)=>{calls++;return url.endsWith('/available')?Response.json({models:[]}):new Response('',{status:429,headers:{'Retry-After':'10'}});}});
 await Promise.all([c.models(),c.models()]);assert.equal(calls,1);
 await assert.rejects(c.infer(args()),/rate_limited/);assert.equal(calls,2);
 await assert.rejects(c.infer(args()),/rate_limited/);assert.equal(calls,2);
 time+=10001;await assert.rejects(c.infer(args()),/rate_limited/);assert.equal(calls,3);
});
test('official MCP client discovers only authorized tools and can call discovery without inference',async()=>{
 const connector=createConnector({policy:policyFromEnv({}),fetchImpl:async()=>Response.json({nodes_online:1})}),server=createMcpServer(connector);
 const [a,b]=InMemoryTransport.createLinkedPair(),client=new Client({name:'fixture-client',version:'1.0.0'});
 await Promise.all([server.connect(a),client.connect(b)]);
 try{assert.deepEqual((await client.listTools()).tools.map(t=>t.name),['gstd_status','gstd_models']);const r=await client.callTool({name:'gstd_status',arguments:{}});assert.equal(r.isError,undefined);assert.equal(JSON.parse(r.content[0].text).connector.spending_authority,false);}
 finally{await client.close();await server.close();}
});
test('official MCP client validates consent and can invoke an explicitly enabled free tool',async()=>{
 let sends=0;const server=createMcpServer(createConnector({policy:policy(),fetchImpl:async()=>{sends++;return Response.json(reply());}}));
 const [a,b]=InMemoryTransport.createLinkedPair(),client=new Client({name:'fixture-client',version:'1.0.0'});
 await Promise.all([server.connect(a),client.connect(b)]);
 try{assert.equal((await client.listTools()).tools.length,3);const bad=await client.callTool({name:'gstd_free_inference',arguments:{prompt:'fixture',allow_network:false,max_cost_gstd:0}});assert.equal(bad.isError,true);assert.equal(sends,0);const good=await client.callTool({name:'gstd_free_inference',arguments:args()});assert.equal(good.isError,undefined);assert.equal(sends,1);}
 finally{await client.close();await server.close();}
});
